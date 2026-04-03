import telebot
import time
import os
from google import genai
from google.genai import types
from google.genai.errors import APIError

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-3-flash-preview"
CODEX = "Твой кодекс здесь..."

def ask_gemini(user_text, retries=3):
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_text)],
        ),
    ]

    # Уровень размышлений понижен на LOW для ускорения ответа
    config = types.GenerateContentConfig(
        system_instruction=CODEX,
        thinking_config=types.ThinkingConfig(thinking_level="LOW"),
    )

    for attempt in range(retries):
        try:
            response_text = ""
            for chunk in client.models.generate_content_stream(
                model=MODEL_NAME,
                contents=contents,
                config=config,
            ):
                if chunk.text:
                    response_text += chunk.text
            return response_text

        except APIError as e:
            if "503" in str(e):
                print(f"503: сервер перегружен, попытка {attempt + 1} из {retries}")
                time.sleep(2)  # уменьшили паузу перед повтором
                continue
            if "429" in str(e):
                return "⚠ Превышен лимит, подожди немного."
            if "400" in str(e):
                return "⚠ Слишком длинное сообщение."
            return f"❌ Ошибка API:\n{str(e)}"

        except Exception as e:
            return f"❌ Другая ошибка:\n{str(e)}"

    return "⚠ Сервис временно недоступен, попробуй позже."


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    bot.send_chat_action(message.chat.id, "typing")
    answer = ask_gemini(message.text)
    # уменьшили задержку между отправками, чтобы бот отвечал быстрее
    for i in range(0, len(answer), 4000):
        bot.send_message(message.chat.id, answer[i:i+4000])
        time.sleep(0.1)  # было 0.3, уменьшили

print("Бот запущен...")
while True:
    try:
        bot.polling(timeout=60)
    except Exception as e:
        print(f"Ошибка Telegram: {e}")
        time.sleep(2)
