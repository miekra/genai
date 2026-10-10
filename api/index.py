from flask import Flask, request, jsonify
import os
from google import genai

app = Flask(__name__)

@app.route('/', methods=['POST'])
def webhook():
    # Безопасно извлекаем данные запроса с force=True
    event = request.get_json(silent=True, force=True) or {}
    session = event.get('session', {})
    version = event.get('version', '1.0')

    try:
        user_text = event.get('request', {}).get('original_utterance', '')
        is_new_session = session.get('new', False)

        if is_new_session or not user_text:
            response_text = "Привет! Я Алиса на базе Gemini. Задайте мне вопрос!"
        else:
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                response_text = "Ошибка: не задан GEMINI_API_KEY в переменных Vercel."
            else:
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=user_text,
                )
                response_text = response.text

        # Обязательно возвращаем session, чтобы Яндекс не выдавал ошибку 400
        return jsonify({
            "version": version,
            "session": session,
            "response": {
                "text": response_text,
                "end_session": False
            }
        })

    except Exception as e:
        # Даже при ошибке возвращаем правильный JSON с сессией
        return jsonify({
            "version": version,
            "session": session,
            "response": {
                "text": f"Произошла ошибка: {str(e)}",
                "end_session": False
            }
        })

@app.route('/', methods=['GET'])
def health_check():
    return "Gemini Alice Webhook is running!"
