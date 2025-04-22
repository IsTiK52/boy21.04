import os
import telebot
import json
import datetime
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

SCHEDULE_PATH = "words_schedule.json"
PROGRESS_PATH = "storage/progress.csv"
REPETITION_PATH = "storage/repetition.json"
ESSAY_DIR = "storage/essays/"

def get_today_words():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    with open(SCHEDULE_PATH, encoding="utf-8") as f:
        schedule = json.load(f)
    return schedule.get(today)

def check_word_usage(words, text):
    return [w["word"] for w in words if w["word"].lower() in text.lower()]

@bot.message_handler(commands=["start", "menu"])
def show_menu(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📘 Слова дня", "✍️ Прислать эссе")
    markup.add("🔁 Повторение", "📊 Мой прогресс", "💰 Поддержать проект")
    bot.send_message(message.chat.id, "Выбери действие:", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def menu(message):
    if message.text == "📘 Слова дня":
        data = get_today_words()
        if not data:
            bot.send_message(message.chat.id, "На сегодня слов нет.")
            return
        theme = data["theme"]
        text = f"🎯 Тема: {theme}\n\n"
        for w in data["words"]:
            text += f"🔹 *{w['word']}* ({w['pos']}) — {w['translation']}\n_{w['example']}_\n\n"
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
    elif message.text == "✍️ Прислать эссе":
        msg = bot.send_message(message.chat.id, "Пришли своё эссе одним сообщением.")
        bot.register_next_step_handler(msg, handle_essay)
    elif message.text == "🔁 Повторение":
        with open(REPETITION_PATH, encoding="utf-8") as f:
            rep = json.load(f)
        words = rep.get(str(message.from_user.id), [])
        text = "\n".join(f"🔁 {w}" for w in words) or "Нет слов для повторения."
        bot.send_message(message.chat.id, text)
    elif message.text == "📊 Мой прогресс":
        with open(PROGRESS_PATH, encoding="utf-8") as f:
            lines = f.readlines()[1:]
        count = len([line for line in lines if str(message.from_user.id) in line])
        bot.send_message(message.chat.id, f"📈 Эссе сдано: {count}")
    elif message.text == "💰 Поддержать проект":
        bot.send_message(message.chat.id, "Если хочешь поддержать проект ❤️\n📲 Kaspi Gold: +7 777 772 21 70\nСпасибо тебе огромное!")

def handle_essay(message):
    user_id = str(message.from_user.id)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    os.makedirs(ESSAY_DIR, exist_ok=True)
    essay_path = f"{ESSAY_DIR}/{user_id}_{today}.txt"
    with open(essay_path, "w", encoding="utf-8") as f:
        f.write(message.text)

    data = get_today_words()
    used_words = check_word_usage(data["words"], message.text)

    # 🔁 GPT через локальный Ollama
    response = requests.post("http://localhost:11434/api/generate", json={
        "model": "llama3",
        "prompt": f"Check this English essay for grammar, style, and structure:\n\n{message.text}",
        "stream": False
    })
    feedback = response.json().get("response", "").strip()

    # Save progress
    with open(PROGRESS_PATH, "a", encoding="utf-8") as f:
        f.write(f"{user_id},{today},{len(data['words'])},{len(used_words)},yes\n")

    # Update repetition
    missed = [w["word"] for w in data["words"] if w["word"] not in used_words]
    with open(REPETITION_PATH, encoding="utf-8") as f:
        rep = json.load(f)
    rep.setdefault(user_id, []).extend(missed)
    rep[user_id] = list(set(rep[user_id]))
    with open(REPETITION_PATH, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)

    bot.send_message(message.chat.id, f"📝 Эссе получено.\n✅ Использовано слов: {len(used_words)} из {len(data['words'])}")
    bot.send_message(message.chat.id, f"📊 GPT анализ:\n{feedback}")

bot.polling()
