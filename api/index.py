from http.server import BaseHTTPRequestHandler
import json
import os

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write("Native Webhook is active.".encode('utf-8'))

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b'{}'
            data = json.loads(body.decode('utf-8'))
        except Exception:
            data = {}

        session = data.get('session', {})
        version = data.get('version', '1.0')
        user_text = data.get('request', {}).get('original_utterance', '')
        is_new_session = session.get('new', False)

        if is_new_session or not user_text:
            response_text = "Привет! Я Алиса на базе Gemini. Задайте мне вопрос!"
        else:
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                response_text = "Ошибка: не задан GEMINI_API_KEY в переменных Vercel."
            else:
                try:
                    from google import genai
                    client = genai.Client(api_key=api_key)
                    response = client.models.generate_content(
                        model='gemini-1.5-flash',
                        contents=user_text,
                    )
                    response_text = response.text if response and response.text else "Модель вернула пустой ответ."
                except Exception as e:
                    response_text = f"Ошибка Gemini: {str(e)}"

        response_data = {
            "version": version,
            "session": session,
            "response": {
                "text": response_text,
                "end_session": False
            }
        }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
