from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/', methods=['POST', 'GET'])
@app.route('/api', methods=['POST', 'GET'])
def webhook():
    try:
        # Если это простой GET-запрос (проверка работоспособности)
        if request.method == 'GET':
            return "Webhook is active.", 200

        # Безопасно парсим JSON от Яндекса
        event = request.get_json(silent=True, force=True) or {}
        session = event.get('session', {})
        version = event.get('version', '1.0')
        user_text = event.get('request', {}).get('original_utterance', '')
        is_new_session = session.get('new', False)

        if is_new_session or not user_text:
            response_text = "Привет! Я Алиса на базе Gemini. Задайте мне вопрос!"
        else:
            import os
            api_key = os.environ.get("GEMINI_API_KEY")
            
            if not api_key:
                response_text = "Ошибка: в настройках Vercel не задана переменная GEMINI_API_KEY."
            else:
                try:
                    # Безопасный импорт и вызов Gemini прямо внутри запроса
                    from google import genai
                    client = genai.Client(api_key=api_key)
                    
                    response = client.models.generate_content(
                        model='gemini-1.5-flash',
                        contents=user_text,
                    )
                    response_text = response.text if response and response.text else "Модель вернула пустой ответ."
                
                except ImportError:
                    response_text = "Ошибка: библиотека google-genai не найдена в requirements.txt"
                except Exception as api_err:
                    response_text = f"Ошибка Gemini: {str(api_err)}"

        # Возвращаем корректный ответ Яндексу
        return jsonify({
            "version": version,
            "session": session,
            "response": {
                "text": response_text,
                "end_session": False
            }
        })

    except Exception as e:
        # Если произошел сбой вообще на любом этапе, вернем текст ошибки в чат Алисы
        return jsonify({
            "version": "1.0",
            "session": {"session_id": "error", "message_id": 0},
            "response": {
                "text": f"Критическая ошибка кода: {str(e)}",
                "end_session": False
            }
        })
