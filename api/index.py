from flask import Flask, request, jsonify, make_response
import os
from google import genai

app = Flask(__name__)

@app.route('/', methods=['POST'])
@app.route('/api', methods=['POST'])
def webhook():
    event = request.get_json(silent=True, force=True) or {}
    session = event.get('session', {})
    version = event.get('version', '1.0')
    
    user_text = event.get('request', {}).get('original_utterance', '')
    is_new_session = session.get('new', False)

    if is_new_session or not user_text:
        response_text = "Привет! Я Алиса на базе Gemini. Задайте мне вопрос!"
    else:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            response_text = "Ошибка: не задана переменная GEMINI_API_KEY в Vercel."
        else:
            try:
                # Инициализация официального клиента Google GenAI
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=user_text,
                )
                response_text = response.text if response and response.text else "Модель вернула пустой ответ."
            except Exception as e:
                response_text = f"Ошибка Gemini API: {str(e)}"

    # Формируем ответ со строгим HTTP статусом 200
    res_body = {
        "version": version,
        "session": session,
        "response": {
            "text": response_text,
            "end_session": False
        }
    }
    
    return make_response(jsonify(res_body), 200)

@app.route('/', methods=['GET'])
@app.route('/api', methods=['GET'])
def health_check():
    return "Webhook is active.", 200
