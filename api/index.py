from flask import Flask, request, jsonify
import os
from google import genai

app = Flask(__name__)

@app.route('/', methods=['POST'])
@app.route('/api', methods=['POST'])
def webhook():
    # 1. Безопасно извлекаем JSON-запрос
    try:
        event = request.get_json(silent=True, force=True) or {}
    except Exception as e:
        event = {}
    
    session = event.get('session', {})
    version = event.get('version', '1.0')
    user_text = event.get('request', {}).get('original_utterance', '')
    is_new_session = session.get('new', False)

    response_text = ""

    # 2. Обрабатываем логику ответа
    if is_new_session or not user_text:
        response_text = "Привет! Я Алиса на базе Gemini. Связь установлена, задайте вопрос."
    else:
        try:
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                response_text = "Ошибка: в настройках Vercel не задана переменная GEMINI_API_KEY."
            else:
                # Инициализация и вызов Gemini (используем стабильную gemini-1.5-flash)
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model='gemini-1.5-flash',
                    contents=user_text,
                )
                response_text = response.text if response and response.text else "Модель вернула пустой ответ."
        except Exception as gemini_error:
            # Если Gemini выдал ошибку или тайм-аут, мы перехватываем её и выводим в чат
            response_text = f"Ошибка Gemini: {str(gemini_error)}"

    # 3. Гарантированно возвращаем правильный JSON для Яндекса
    return jsonify({
        "version": version,
        "session": session,
        "response": {
            "text": response_text,
            "end_session": False
        }
    })

@app.route('/', methods=['GET'])
@app.route('/api', methods=['GET'])
def health_check():
    return "Webhook is active."
