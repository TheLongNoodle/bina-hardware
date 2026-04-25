from gpiozero import LED
from time import sleep   
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8071
led = LED(21)

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        print("Request Receved!")
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Signal received!\n")
        for _ in range(5):
            led.on()
            sleep(1)  # LED ON for 1 second
            led.off()
            sleep(1)  # LED OFF for 1 second

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), SimpleHandler)
    print(f"Listening on port {PORT}...")
    server.serve_forever()

