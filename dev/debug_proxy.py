import tornado.ioloop
import tornado.web
import tornado.httpclient
import json
import time
import os
import datetime

# Configuration
OLLAMA_URL = "http://localhost:11434"
LISTEN_PORT = 11435

def get_daily_log_file():
    """Returns a filename based on the current date."""
    today = datetime.date.today().strftime("%Y-%m-%d")
    os.makedirs("logs", exist_ok=True)
    return f"logs/debug_{today}.log"

def clean_response_for_logging(response_text):
    """Parses response JSON and removes bulky fields like 'context'."""
    try:
        # Handle streaming JSON (multiple objects)
        if "}\n{" in response_text:
            return response_text # Keep raw streams as is, hard to filter on the fly
        
        data = json.loads(response_text)
        
        # Filter out the massive context array
        if 'context' in data:
            count = len(data['context'])
            data['context'] = f"<... {count} integers hidden ...>"
            
        # Filter out embedding vectors (if you use embeddings endpoint)
        if 'embedding' in data:
             data['embedding'] = "<... vector hidden ...>"
             
        return json.dumps(data, indent=2)
    except:
        return response_text

def log_transaction(endpoint, req_payload, response_text, duration):
    """Appends the clean request/response pair to the daily log file."""
    filename = get_daily_log_file()
    
    try:
        with open(filename, "a", encoding="utf-8") as f:
            timestamp = time.strftime("%H:%M:%S")
            
            # --- HEADER: Massive visual separation for new requests ---
            f.write("\n\n\n")
            f.write("################################################################################\n")
            f.write(f"###   REQUEST START  |  {endpoint}  |  {timestamp}  |  {duration:.2f}s   ###\n")
            f.write("################################################################################\n")

            # --- 1. REQUEST SECTION ---
            if req_payload:
                # Make a copy so we don't modify the original
                log_view = req_payload.copy()
                
                # Extract prompt to print separately
                prompt_text = log_view.pop('prompt', None)
                
                f.write("\n--- [METADATA] ---\n")
                f.write(json.dumps(log_view, indent=2))
                
                # Print the Prompt as a distinct block
                if prompt_text:
                    f.write("\n\n")
                    f.write("┌──────────────────────────────────────────────────────────────────────────────┐\n")
                    f.write("│  📝 PROMPT TEXT                                                              │\n")
                    f.write("└──────────────────────────────────────────────────────────────────────────────┘\n")
                    f.write(str(prompt_text))
                    f.write("\n\n")
            else:
                f.write("\n(No Request Body)\n")

            # --- 2. RESPONSE SECTION ---
            f.write("=" * 80 + "\n")
            f.write("  ⬅️   RESPONSE\n")
            f.write("=" * 80 + "\n")

            clean_res = clean_response_for_logging(response_text)
            f.write(clean_res)
            
            # --- FOOTER: Clear end marker ---
            f.write("\n")
            f.write("-------------------------------- END OF TRANSACTION --------------------------------\n")
                
        print(f"🟢 Logged {endpoint} to {filename}")

    except Exception as e:
        print(f"🔴 Failed to write log: {e}")

class ProxyHandler(tornado.web.RequestHandler):
    async def prepare(self):
        # Capture body for logging
        self.request_payload = {}
        if self.request.body:
            try:
                self.request_payload = json.loads(self.request.body)
            except:
                self.request_payload = {"raw": self.request.body.decode('utf-8', errors='ignore')}

    async def forward(self, path):
        url = f"{OLLAMA_URL}/{path}"
        start_time = time.time()
        
        # Clean headers
        headers = self.request.headers.copy()
        for header in ['Host', 'Content-Length']:
            if header in headers:
                del headers[header]

        http_client = tornado.httpclient.AsyncHTTPClient()
        
        try:
            request = tornado.httpclient.HTTPRequest(
                url=url,
                method=self.request.method,
                headers=headers,
                body=self.request.body if self.request.body else None,
                request_timeout=300.0
            )
            
            response = await http_client.fetch(request)
            
            self.set_status(response.code)
            for key, value in response.headers.get_all():
                if key not in ['Content-Length', 'Transfer-Encoding', 'Connection']:
                    self.set_header(key, value)
            
            self.write(response.body)
            
            # Log logic
            duration = time.time() - start_time
            response_text = response.body.decode('utf-8', errors='ignore')
            log_transaction(path, self.request_payload, response_text, duration)
            
        except tornado.httpclient.HTTPClientError as e:
            if e.response:
                self.set_status(e.response.code)
                self.write(e.response.body)
                duration = time.time() - start_time
                log_transaction(path, self.request_payload, e.response.body.decode('utf-8', errors='ignore'), duration)
            else:
                self.set_status(500)
                self.write(f"Proxy Error: {str(e)}")
        except Exception as e:
            self.set_status(500)
            self.write(f"Internal Error: {str(e)}")

    async def get(self, path): await self.forward(path)
    async def post(self, path): await self.forward(path)
    async def put(self, path): await self.forward(path)
    async def delete(self, path): await self.forward(path)

def make_app():
    return tornado.web.Application([(r"/(.*)", ProxyHandler)])

if __name__ == "__main__":
    print(f"🕵️  Clean Debug Proxy running on port {LISTEN_PORT}")
    print(f"📂 Logs will be saved to: {get_daily_log_file()}")
    app = make_app()
    app.listen(LISTEN_PORT)
    tornado.ioloop.IOLoop.current().start()