from flask import Flask, request, jsonify
import os
from google import genai

app = Flask(__name__)

@app.route('/api', methods=['POST'])
def webhook():
    try:
        # Flask сам корректно парсит JSON от Яндекса
        event = request.get_json(silent=True) or {}
        
        user_text = event.get('request', {}).get('original_utterance', '')
        is_new_session = event.get('session', {}).get('new', False)

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

        # Возвращаем ответ в строгом формате Яндекс Диалогов
        return jsonify({
            "version": event.get('version', '1.0'),
            "session": event.get('session'),
            "response": {
                "text": response_text,
                "end_session": False
            }
        })

    except Exception as e:
        # Если произошла любая ошибка, возвращаем текст ошибки Алисе, чтобы не было пустого ответа
        return jsonify({
            "version": "1.0",
            "session": event.get('session', {}),
            "response": {
                "text": f"Произошла ошибка обработки: {str(e)}",
                "end_session": False
            }
        })

# Дополнительный маршрут на случай запроса без слеша или с ним
@app.route('/api/', methods=['POST'])
def webhook_slash():
    return webhook()
