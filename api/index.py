from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/', methods=['POST', 'GET'])
@app.route('/api', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return "Echo bot is active!", 200

    try:
        event = request.get_json(silent=True, force=True) or {}
        session = event.get('session', {})
        version = event.get('version', '1.0')
        user_text = event.get('request', {}).get('original_utterance', '')

        # Просто повторяем то, что сказала Алиса
        response_text = f"Эхо: {user_text}" if user_text else "Привет!"

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
                "text": f"Ошибка: {str(e)}",
                "end_session": False
            }
        }), 200
