"""Serve the standalone board placement form using only Python's standard library."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import webbrowser

WEB_ROOT = Path(__file__).with_name("web")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8769)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    handler = partial(SimpleHTTPRequestHandler, directory=str(WEB_ROOT))
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    except OSError as exc:
        parser.error(str(exc))
    url = f"http://localhost:{server.server_port}/placement_planner.html"
    print(f"Placement planner: {url}\nPress Ctrl+C to stop.", flush=True)
    if not args.no_browser:
        threading.Timer(.2, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
