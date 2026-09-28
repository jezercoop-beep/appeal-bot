"""Единый клиент ИИ. Автоматически выбирает провайдера:
1. ANTHROPIC_API_KEY -> Claude
2. GEMINI_API_KEY    -> Google Gemini (бесплатный тариф, vision)
3. OPENAI_API_KEY    -> любой OpenAI-совместимый API
"""
import base64
import json
import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()

PROVIDER = ("anthropic" if os.environ.get("ANTHROPIC_API_KEY")
            else "gemini" if os.environ.get("GEMINI_API_KEY")
            else "openai" if os.environ.get("OPENAI_API_KEY") else None)

MODEL = (os.environ.get("ANTHROPIC_MODEL") or os.environ.get("GEMINI_MODEL")
         or os.environ.get("OPENAI_MODEL") or "gemini-3.8-flash")

FOOD_PROMPT = (
    "Ты эксперт по питанию. По фото определи блюдо, оцени массу порции и КБЖУ. "
    'Ответь СТРОГО одним JSON-объектом без текста вокруг: '
    '{"dish":"название","grams":число,"kcal":число,"protein":число,"fat":число,"carbs":число}'
)


def _anthropic(messages, system=None, image=None, media_type="image/jpeg"):
    from anthropic import Anthropic
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], timeout=120)
    content = []
    if image:
        content.append({"type": "image",
                        "source": {"type": "base64", "media_type": media_type,
                                   "data": base64.b64encode(image).decode()}})
    content.append({"type": "text", "text": messages[-1]["content"]})
    resp = client.messages.create(model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
                                  max_tokens=1024,
                                  system=system or "",
                                  messages=[{"role": "user", "content": content}])
    return "".join(b.text for b in resp.content if b.type == "text")


def _gemini(messages, system=None, image=None, media_type="image/jpeg"):
    key = os.environ["GEMINI_API_KEY"]
    parts = []
    if image:
        parts.append({"inline_data": {"mime_type": media_type,
                                      "data": base64.b64encode(image).decode()}})
    parts.append({"text": messages[-1]["content"]})
    body = {"contents": [{"role": "user", "parts": parts}]}
    if system:
        body["system_instruction"] = {"parts": [{"text": system}]}
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{os.environ.get('GEMINI_MODEL', 'gemini-3.8-flash')}:generateContent?key={key}")
    r = requests.post(url, json=body, timeout=120)
    r.raise_for_status()
    data = r.json()
    return "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])


def _openai(messages, system=None, image=None, media_type="image/jpeg"):
    key = os.environ["OPENAI_API_KEY"]
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    msgs = ([{"role": "system", "content": system}] if system else []) + list(messages)
    if image:
        b64 = base64.b64encode(image).decode()
        msgs[-1]["content"] = [
            {"type": "text", "text": msgs[-1]["content"]},
            {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64}"}}]
    r = requests.post(f"{base}/chat/completions",
                      headers={"Authorization": f"Bearer {key}"},
                      json={"model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                            "messages": msgs, "temperature": 0.3}, timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


_CALL = {"anthropic": _anthropic, "gemini": _gemini, "openai": _openai}


def describe_food(image_bytes: bytes, media_type: str = "image/jpeg") -> str:
    return _CALL[PROVIDER](
        [{"role": "user", "content": "Определи КБЖУ этого блюда."}],
        system=FOOD_PROMPT, image=image_bytes, media_type=media_type)


def chat(system: str, history: list) -> str:
    return _CALL[PROVIDER](history, system=system)


def parse_food(text: str):
    s, e = text.find("{"), text.rfind("}")
    if s == -1:
        return None
    d = json.loads(text[s:e + 1])
    num = lambda k: float(d.get(k, 0) or 0)
    return d.get("dish", "Блюдо"), num("grams"), num("kcal"), num("protein"), num("fat"), num("carbs")


GOALS_RE = re.compile(r"СОХРАНИ_ЦЕЛИ.*?ккал=([\d.]+).*?белки=([\d.]+).*?жиры=([\d.]+).*?углеводы=([\d.]+)", re.S)


def parse_goals_command(text: str):
    m = GOALS_RE.search(text)
    if not m:
        return None
    return [float(x) for x in m.groups()]
