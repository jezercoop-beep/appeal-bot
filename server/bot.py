"""Логика Telegram-бота. Работает и через webhook (прод), и через polling (локально)."""
import asyncio
import datetime

import ai_client as ai
import db
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton, Message,
                           WebAppInfo)

from config import BOT_TOKEN, PROMPT, WEBAPP_URL

WELCOME = (
    "Привет! Я Appeal — твой трекер питания \U0001F33F\n\n"
    "\U0001F4F8 Пришли фото еды — посчитаю КБЖУ\n"
    "\U0001F4AC Напиши «посчитай мне калории» — рассчитаю цель\n"
    "\U0001F4CA Кнопка ниже — мини-приложение с прогрессом и статистикой"
)


def make_dp() -> Dispatcher:
    db.init()
    dp = Dispatcher()
    bot = Bot(BOT_TOKEN)
    dp["bot"] = bot

    @dp.message(CommandStart())
    async def start(m: Message):
        db.upsert_user(m.from_user.id, m.from_user.username or "", m.from_user.first_name or "")
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="📊 Открыть Appeal", web_app=WebAppInfo(url=WEBAPP_URL))
        ]])
        await m.answer(WELCOME, reply_markup=kb)

    @dp.message(Command("goal"))
    async def goal(m: Message):
        await m.answer("Напиши мне в чат: «посчитай мои калории» — я спрошу вес, рост, возраст и рассчитаю целевые КБЖУ 💬")

    @dp.message(F.photo)
    async def on_photo(m: Message):
        msg = await m.answer("🔍 Смотрю на фото...")
        try:
            f = await bot.download(m.photo[-1])
            parsed = ai.parse_food(ai.describe_food(f.read()))
            if not parsed:
                await msg.edit_text("Не смог распознать блюдо 😔 Попробуй другое фото.")
                return
            dish, grams, kcal, p, f_, c = parsed
            db.upsert_user(m.from_user.id, m.from_user.username or "", m.from_user.first_name or "")
            db.add_meal(m.from_user.id, dish, kcal, p, f_, c)
            tot = db.totals_on(m.from_user.id, datetime.date.today().isoformat())
            await msg.edit_text(
                f"🍽 <b>{dish}</b> (~{grams:.0f} г)\n"
                f"⚡️ {kcal:.0f} ккал · Б {p:.0f} · Ж {f_:.0f} · У {c:.0f}\n\n"
                f"За день: <b>{tot['kcal']:.0f}</b> ккал",
                parse_mode="HTML")
        except Exception as e:
            await msg.edit_text(f"Ошибка 😔 Попробуй ещё раз. ({e})")

    @dp.message(F.text)
    async def on_text(m: Message):
        db.upsert_user(m.from_user.id, m.from_user.username or "", m.from_user.first_name or "")
        wait = await m.answer("...")
        try:
            user = db.get_user(m.from_user.id) or {}
            sys_prompt = (PROMPT + f"\n\nТекущие цели пользователя: ккал={user.get('kcal')}, "
                          f"белки={user.get('protein')}г, жиры={user.get('fat')}г, углеводы={user.get('carbs')}г. "
                          "Если он соглашается с рассчитанными целями — выведи команду СОХРАНИ_ЦЕЛИ.")
            db.add_chat(m.from_user.id, "user", m.text)
            history = [{"role": h["role"], "content": h["text"]} for h in db.chat_history(m.from_user.id)]
            reply = ai.chat(sys_prompt, history)
            goals = ai.parse_goals_command(reply)
            if goals:
                db.set_goals(m.from_user.id, *goals)
                reply = reply[:reply.find("СОХРАНИ_ЦЕЛИ")] + "✅ Цели сохранены!"
            db.add_chat(m.from_user.id, "assistant", reply)
            await wait.edit_text(reply, parse_mode="HTML")
        except Exception as e:
            await wait.edit_text(f"Ошибка 😔 ({e})")

    return dp
