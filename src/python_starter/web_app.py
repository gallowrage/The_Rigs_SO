from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8000
WEB_ROOT = Path(__file__).with_name("web")


class PianoAppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), PianoAppHandler)
    print(f"Piano Chord Studio is running at http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Piano Chord Studio.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
