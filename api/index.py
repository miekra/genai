from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# Кэшируем клиент глобально, чтобы избежать повторных долгих инициализаций
_client = None

def get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            from google import genai
            _client = genai.Client(api_key=api_key)
    return _client

@app.route('/', methods=['POST', 'GET'])
@app.route('/api', methods=['POST', 'GET'])
def webhook():
    # Если зашли из браузера (GET)
    if request.method == 'GET':
        return "Webhook is active.", 200

    try:
        # Безопасно парсим запрос от Яндекса
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
                        response_text = "Ошибка: не удалось инициализировать клиент Gemini."
                    else:
                        # Запрос к модели
                        response = client.models.generate_content(
                            model='gemini-1.5-flash',
                            contents=user_text,
                        )
                        response_text = response.text if response and response.text else "Модель вернула пустой ответ."
                except Exception as api_err:
                    response_text = f"Ошибка обращения к Gemini: {str(api_err)}"

        # Отправляем ответ Яндексу со статусом 200
        return jsonify({
            "version": version,
            "session": session,
            "response": {
                "text": response_text,
                "end_session": False
            }
        }), 200

    except Exception as e:
        # Даже если упадет всё остальное, вернем ошибку текстом в чат, а не пустой ответ
        return jsonify({
            "version": "1.0",
            "session": {"session_id": "error", "message_id": 0},
            "response": {
                "text": f"Критическая ошибка: {str(e)}",
                "end_session": False
            }
        }), 200
