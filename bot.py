import os
import time
import telebot
from google import genai
from google.genai import types
from google.genai.errors import APIError
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise Exception("Проверьте, что TELEGRAM_TOKEN и GEMINI_API_KEY установлены!")

# Твой системный кодекс
CODEX = "Твой кодекс здесь..."

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-3-flash-preview"

def ask_gemini_streaming(user_text, retries=3):
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_text)],
        ),
    ]

    config = types.GenerateContentConfig(
        system_instruction=CODEX,
        thinking_config=types.ThinkingConfig(thinking_level="LOW")
    )

    for attempt in range(retries):
        try:
            # потоковая генерация
            partial_response = ""
            for chunk in client.models.generate_content_stream(
                model=MODEL_NAME,
                contents=contents,
                config=config
            ):
                if chunk.text:
                    partial_response += chunk.text
                    yield chunk.text  # отправка части текста сразу
            return
        except APIError as e:
            err = str(e)
            if "503" in err:
                print(f"⚠ 503: сервер перегружен, попытка {attempt + 1} из {retries}")
                time.sleep(2)
                continue
            if "429" in err:
                yield "⚠ Превышен лимит, подожди немного."
                return
            if "400" in err:
                yield "⚠ Слишком длинное сообщение."
                return
            yield f"❌ Ошибка API:\n{err}"
            return
        except Exception as e:
            yield f"❌ Другая ошибка:\n{str(e)}"
            return

    yield "⚠ Сервис временно недоступен, попробуй позже."


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    bot.send_chat_action(message.chat.id, "typing")

    # Отправка текста по мере генерации
    full_text = ""
    for chunk_text in ask_gemini_streaming(message.text):
        # Telegram ограничивает частые сообщения, поэтому делаем небольшую паузу
        if chunk_text:
            bot.send_message(message.chat.id, chunk_text)
            time.sleep(0.05)
        full_text += chunk_text

print("Бот запущен...")
while True:
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"Ошибка Telegram: {e}")
        time.sleep(2)
