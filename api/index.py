from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# Этот роутер перехватывает вообще любые пути (будь то /api, корневой / или любые другие)
@app.route('/', defaults={'path': ''}, methods=['POST', 'GET'])
@app.route('/<path:path>', methods=['POST', 'GET'])
def webhook(path):
    if request.method == 'GET':
        return "Webhook is active.", 200

    try:
        # Безопасно парсим JSON-запрос от Яндекса
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
                response_text = "Ошибка: в настройках Vercel не задана переменная GEMINI_API_KEY."
            else:
                try:
                    from google import genai
                    client = genai.Client(api_key=api_key)
                    
                    response = client.models.generate_content(
                        model='gemini-1.5-flash',
                        contents=user_text,
                    )
                    response_text = response.text if response and response.text else "Модель вернула пустой ответ."
                except Exception as api_err:
                    response_text = f"Ошибка Gemini: {str(api_err)}"

        # Возвращаем строгий JSON для Яндекса со статусом 200
        return jsonify({
            "version": version,
            "session": session,
            "response": {
                "text": response_text,
                "end_session": False
            }
        }), 200

    except Exception as e:
        # Если произойдет сбой, вернем текст ошибки в чат Алисы
        return jsonify({
            "version": "1.0",
            "session": {"session_id": "error", "message_id": 0},
            "response": {
                "text": f"Критическая ошибка: {str(e)}",
                "end_session": False
            }
        }), 200
