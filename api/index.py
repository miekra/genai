from flask import Flask, request, jsonify
import os
from google import genai

app = Flask(__name__)

# Глобальный клиент для минимизации задержек инициализации
_client = None

def get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            _client = genai.Client(api_key=api_key)
    return _client

@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return "Webhook is active.", 200

    try:
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
                response_text = "Ошибка: не задан GEMINI_API_KEY в Vercel."
            else:
                try:
                    client = get_client()
                    if not client:
                        response_text = "Ошибка инициализации клиента."
                    else:
                        # Ограничиваем максимальную длину ответа токенами, 
                        # чтобы модель отвечала мгновенно и не превышала тайм-аут Яндекса
                        config = {
                            "max_output_tokens": 150,
                            "temperature": 0.7
                        }
                        
                        response = client.models.generate_content(
                            model='gemini-1.5-flash',
                            contents=user_text,
                            config=config
                        )
                        response_text = response.text if response and response.text else "Модель вернула пустой ответ."
                except Exception as api_err:
                    response_text = f"Ошибка Gemini: {str(api_err)}"

        return jsonify({
            "version": version,
            "session": session,
            "response": {
                "text": response_text,
                "end_session": False
            }
        }), 200

    except Exception as e:
        return jsonify({
            "version": "1.0",
            "session": {"session_id": "error", "message_id": 0},
            "response": {
                "text": f"Критическая ошибка: {str(e)}",
                "end_session": False
            }
        }), 200
