from http.server import BaseHTTPRequestHandler
import json
import os
from google import genai

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body_data = self.rfile.read(content_length)
            event = json.loads(body_data.decode('utf-8')) if body_data else {}

            user_text = event.get('request', {}).get('original_utterance', '')
            is_new_session = event.get('session', {}).get('new', False)

            # При старте сессии сразу возвращаем приветствие без вызова Gemini
            if is_new_session or not user_text:
                response_text = "Привет! Я Алиса на базе Gemini. Напишите мне любой вопрос!"
            else:
                api_key = os.environ.get("GEMINI_API_KEY")
                if not api_key:
                    response_text = "Ошибка: не задан API ключ GEMINI_API_KEY в Vercel."
                else:
                    client = genai.Client(api_key=api_key)
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=user_text,
                    )
                    response_text = response.text

            response_body = json.dumps({
                "version": event.get('version', '1.0'),
                "session": event.get('session'),
                "response": {
                    "text": response_text,
                    "end_session": False
                }
            }, ensure_ascii=False)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(response_body.encode('utf-8'))

        except Exception as e:
            # Безопасный перехват любых ошибок, чтобы Яндекс Диалоги не получали empty response
            error_response = json.dumps({
                "version": "1.0",
                "session": event.get('session') if 'event' in locals() else {},
                "response": {
                    "text": f"Произошла внутренняя ошибка: {str(e)}",
                    "end_session": False
                }
            }, ensure_ascii=False)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))

    def do_GET(self):
        # Чтобы при клике в браузере не выдавало 501 ошибку
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write("Webhook handler is running!".encode('utf-8'))
