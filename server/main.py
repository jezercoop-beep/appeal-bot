"""Единый сервер: FastAPI (мини-апп + API) + Telegram-бот (webhook или polling)."""
import asyncio
import datetime
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import ai_client as ai
import auth
import db
from bot import make_dp
from fastapi import FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import BOT_TOKEN, PROMPT, PUBLIC_URL, USE_POLLING, WEBHOOK_SECRET, WEBAPP_URL

WEBAPP_DIR = Path(__file__).parent.parent / "webapp"
app = FastAPI()
db.init()
app.mount("/static", StaticFiles(directory=str(WEBAPP_DIR)), name="static")

dp = make_dp()
BOT = dp["bot"]
WEBHOOK_PATH = f"/telegram/{WEBHOOK_SECRET}"


def user_from(init_data: str):
    u = auth.check_init_data(init_data, BOT_TOKEN)
    if not u:
        raise HTTPException(status_code=401, detail="Bad initData")
    db.upsert_user(u["id"], u.get("username", ""), u.get("first_name", ""))
    return u


@app.get("/")
def index():
    return FileResponse(str(WEBAPP_DIR / "index.html"))


@app.post("/api/init")
def api_init(init_data: str = Form(...)):
    u = user_from(init_data)
    return {"user": db.get_user(u["id"]), "webapp_url": WEBAPP_URL}


class GoalsIn(BaseModel):
    init_data: str
    kcal: float
    protein: float
    fat: float
    carbs: float


@app.put("/api/goals")
def api_goals(g: GoalsIn):
    u = user_from(g.init_data)
    db.set_goals(u["id"], g.kcal, g.protein, g.fat, g.carbs)
    return {"ok": True, "user": db.get_user(u["id"])}


@app.get("/api/today")
def api_today(init_data: str):
    u = user_from(init_data)
    today = datetime.date.today().isoformat()
    return {"goals": db.get_user(u["id"]),
            "totals": db.totals_on(u["id"], today),
            "meals": db.meals_on(u["id"], today)}


@app.get("/api/week")
def api_week(init_data: str):
    u = user_from(init_data)
    return {"days": db.week(u["id"]), "goals": db.get_user(u["id"])}


@app.post("/api/food")
async def api_food(init_data: str = Form(...), photo: UploadFile = Form(...)):
    u = user_from(init_data)
    raw = await photo.read()
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Фото слишком большое")
    parsed = ai.parse_food(ai.describe_food(raw, photo.content_type or "image/jpeg"))
    if not parsed:
        raise HTTPException(status_code=502, detail="ИИ не распознал блюдо")
    dish, grams, kcal, p, f_, c = parsed
    mid = db.add_meal(u["id"], dish, kcal, p, f_, c)
    return {"ok": True, "meal": {"id": mid, "dish": dish, "grams": grams,
                                 "kcal": kcal, "protein": p, "fat": f_, "carbs": c}}


@app.delete("/api/meals/{meal_id}")
def api_del(meal_id: int, init_data: str):
    u = user_from(init_data)
    db.del_meal(u["id"], meal_id)
    return {"ok": True}


class ChatIn(BaseModel):
    init_data: str
    text: str


@app.post("/api/chat")
def api_chat(c: ChatIn):
    u = user_from(c.init_data)
    user = db.get_user(u["id"]) or {}
    sys_prompt = (PROMPT + f"\n\nЦели: ккал={user.get('kcal')}, Б={user.get('protein')}г, "
                  f"Ж={user.get('fat')}г, У={user.get('carbs')}г.")
    db.add_chat(u["id"], "user", c.text)
    history = [{"role": h["role"], "content": h["text"]} for h in db.chat_history(u["id"])]
    reply = ai.chat(sys_prompt, history)
    goals = ai.parse_goals_command(reply)
    saved = False
    if goals:
        db.set_goals(u["id"], *goals)
        saved = True
        reply = reply[:reply.find("СОХРАНИ_ЦЕЛИ")] + "✅ Цели сохранены!"
    db.add_chat(u["id"], "assistant", reply)
    return {"reply": reply, "goals_saved": saved, "user": db.get_user(u["id"])}


# ---------- Telegram webhook ----------
@app.post(WEBHOOK_PATH)
async def telegram_webhook(req: Request):
    from aiogram.types import Update
    update = Update(**await req.json())
    await dp.feed_raw_update(BOT, update.model_dump(exclude_unset=True))
    return {"ok": True}


@app.get("/health")
def health():
    return {"ok": True}


async def on_startup():
    if USE_POLLING:
        asyncio.create_task(dp.start_polling(BOT))
    elif PUBLIC_URL:
        await BOT.set_webhook(f"{PUBLIC_URL}{WEBHOOK_PATH}", drop_pending_updates=True)


app.add_event_handler("startup", on_startup)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
