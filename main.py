
import os
import telebot
import json
import datetime
import openai

# Загрузка переменных окружения
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
openai.api_key = OPENAI_API_KEY

# Пути к файлам
SCHEDULE_PATH = "words_schedule.json"
PROGRESS_PATH = "storage/progress.csv"
REPETITION_PATH = "storage/repetition.json"
ESSAY_DIR = "storage/essays/"

# Загрузка расписания
with open(SCHEDULE_PATH, encoding="utf-8") as f:
    schedule = json.load(f)

# Получение слов на сегодня
def get_today_words():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    return schedule.get(today)

# Проверка использования слов
def check_word_usage(words, text):
    used = [w["word"] for w in words if w["word"].lower() in text.lower()]
    return used

# Команды
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, "Привет! Я VocabularBot. Нажми кнопку 📘 Слова дня.")

@bot.message_handler(func=lambda m: True)
def menu(message):
    if message.text == "📘 Слова дня":
        data = get_today_words()
        if not data:
            bot.send_message(message.chat.id, "На сегодня слов нет.")
            return
        theme = data["theme"]
        text = f"🎯 Тема: {theme}

"
        for w in data["words"]:
            text += f"🔹 *{w['word']}* ({w['pos']}) — {w['translation']}
_{w['example']}_

"
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
    elif message.text == "✍️ Прислать эссе":
        msg = bot.send_message(message.chat.id, "Пришли своё эссе одним сообщением.")
        bot.register_next_step_handler(msg, handle_essay)
    elif message.text == "🔁 Повторение":
        with open(REPETITION_PATH, encoding="utf-8") as f:
            rep = json.load(f)
        text = ""
        for word in rep.get(str(message.from_user.id), []):
            text += f"🔁 {word}
"
        bot.send_message(message.chat.id, text or "Нет слов для повторения.")
    elif message.text == "📊 Мой прогресс":
        with open(PROGRESS_PATH, encoding="utf-8") as f:
            lines = f.readlines()[1:]
        count = len([line for line in lines if str(message.from_user.id) in line])
        bot.send_message(message.chat.id, f"📈 Эссе сдано: {count}")
    elif message.text == "💰 Поддержать проект":
        bot.send_message(message.chat.id, "Если хочешь поддержать проект ❤️
📲 Kaspi Gold: +7 777 772 21 70
Спасибо тебе огромное!")

# Обработка эссе
def handle_essay(message):
    user_id = str(message.from_user.id)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    essay_path = f"{ESSAY_DIR}/{user_id}_{today}.txt"
    with open(essay_path, "w", encoding="utf-8") as f:
        f.write(message.text)

    data = get_today_words()
    used_words = check_word_usage(data["words"], message.text)

    # GPT анализ
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Check the following English essay for grammar, style, and structure."},
            {"role": "user", "content": message.text}
        ]
    )
    feedback = response["choices"][0]["message"]["content"]

    # Сохраняем в progress
    with open(PROGRESS_PATH, "a", encoding="utf-8") as f:
        f.write(f"{user_id},{today},{len(data['words'])},{len(used_words)},yes
")

    # Сохраняем в repetition
    missed = [w["word"] for w in data["words"] if w["word"] not in used_words]
    with open(REPETITION_PATH, encoding="utf-8") as f:
        rep = json.load(f)
    rep.setdefault(user_id, []).extend(missed)
    rep[user_id] = list(set(rep[user_id]))
    with open(REPETITION_PATH, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)

    bot.send_message(message.chat.id, f"📝 Эссе получено.
✅ Использовано слов: {len(used_words)} из {len(data['words'])}")
    bot.send_message(message.chat.id, f"📊 GPT анализ:
{feedback}")

# Кнопки
from telebot import types
@bot.message_handler(commands=["menu"])
def show_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📘 Слова дня", "✍️ Прислать эссе")
    markup.add("🔁 Повторение", "📊 Мой прогресс", "💰 Поддержать проект")
    bot.send_message(message.chat.id, "Выбери действие:", reply_markup=markup)

bot.polling()
