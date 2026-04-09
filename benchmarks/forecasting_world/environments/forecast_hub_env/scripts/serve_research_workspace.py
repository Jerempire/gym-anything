#!/usr/bin/env python3
from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class ResearchWorkspaceHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:  # pragma: no cover - exercised indirectly in env
        self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8123)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    handler = partial(ResearchWorkspaceHandler, directory=str(root))
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Serving research workspace at http://{args.host}:{args.port}/ from {root}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
