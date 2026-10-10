import json
from http.server import BaseHTTPRequestHandler
from google import genai
import os

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body_data = self.rfile.read(content_length)
        event = json.loads(body_data.decode('utf-8')) if body_data else {}
        
        user_text = event.get('request', {}).get('original_utterance', '')
        is_new_session = event.get('session', {}).get('new', False)

        if is_new_session or not user_text:
            response_text = "Привет! Я Алиса на базе Gemini."
        else:
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
        return
