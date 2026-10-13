"""Servidor local: python3 app.py. No necesita cuenta ni API de Spotify."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from recommender import ContentRecommender, DEFAULT_DATASET


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, model, **kwargs):
        self.model = model
        super().__init__(*args, directory=str(Path(__file__).parent / "static"), **kwargs)

    def reply(self, payload, status=200):
        data = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        params = parse_qs(url.query)
        try:
            if url.path == "/api/stats":
                return self.reply(self.model.stats)
            if url.path == "/api/search":
                return self.reply(self.model.search(params.get("q", [""])[0][:200]))
            if url.path == "/api/recommend":
                return self.reply(self.model.recommend(
                    params.get("id", [""])[0], int(params.get("count", ["6"])[0]),
                    json.loads(params.get("weights", ["{}"])[0])))
            if url.path.startswith("/api/"):
                return self.reply({"error": "Ruta no encontrada."}, 404)
            return super().do_GET()
        except KeyError as error:
            self.reply({"error": str(error.args[0])}, 404)
        except (ValueError, TypeError, OverflowError) as error:
            self.reply({"error": str(error)}, 400)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    args = parser.parse_args()
    print("Preparando catálogo y vectores de audio…", flush=True)
    model = ContentRecommender(args.dataset)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), partial(Handler, model=model))
    print(f"{model.stats['tracks']:,} canciones listas · http://localhost:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
