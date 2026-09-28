# 🌿 Appeal — трекер калорий (Telegram Mini App + Claude)

## Что умеет
- 📸 Фото еды → Claude (vision) → КБЖУ → дневник
- 💬 Текстовый чат: Claude пошагово считает целевые КБЖУ и сохраняет их по команде
- 📊 Мини-апп: прогресс-кольца за день, график за 7 дней, редактирование целей, чат
- 🎨 Минимализм в стиле логотипа (чёрный + салатовый), светлая/тёмная тема Telegram

## Деплой на Render (бесплатно) — 10 минут
1. Залей эту папку на GitHub (кнопка Add file → Upload files)
2. render.com → Sign up (GitHub) → **New + → Blueprint** → выбери репозиторий
3. Render сам увидит `render.yaml`. Введи переменные:
   - `BOT_TOKEN` — токен от @BotFather
   - `GEMINI_API_KEY` — бесплатный ключ на aistudio.google.com (кнопка Get API key, карта не нужна)
   - `PUBLIC_URL` — появится после деплоя, вида `https://appeal-bot.onrender.com`
     (сначала оставь пустым/любым, после деплоя впиши и нажми **Save Changes** — сервер перезапустится и сам установит webhook)
4. Готово! Открой бота в Telegram → /start → кнопка «Открыть Appeal»
5. В @BotFather: Bot Settings → Menu Button → укажи тот же URL

## Локальный тест (без деплоя)
```bash
pip install -r requirements.txt
cp .env.example .env   # заполни токены, поставь USE_POLLING=1
python server/main.py
# и в @BotFather → Bot Settings → Menu Button → http://localhost:8000
# (мини-апп локально откроется, фото работает, webhook не нужен)
```

## Свой промпт
Замени текст в `prompt.txt` на свой промпт от Claude и перезапусти сервер (Render: Manual Deploy → Clear build cache & deploy).
