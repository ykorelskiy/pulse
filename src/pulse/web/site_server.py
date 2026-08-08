"""Site server for Pulse showcase website (Vite React SPA)."""

import os
from http.server import HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from pulse.logging import configure_logging, get_logger

logger = get_logger("pulse.web.site_server")

SITE_DIST_DIR = Path(__file__).resolve().parent.parent.parent.parent / "site" / "dist"


class SPARequestHandler(SimpleHTTPRequestHandler):
    """Simple HTTP Request Handler with SPA fallback to index.html for date routes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE_DIST_DIR), **kwargs)

    def do_GET(self):
        # Serve existing static files (js, css, webp, png, svg) directly
        target_file = SITE_DIST_DIR / self.path.lstrip("/")
        if not target_file.exists() and not self.path.startswith("/assets"):
            # Fallback to index.html for SPA client-side routing (/2026/08/08)
            self.path = "/index.html"
        return super().do_GET()


def run_site_server(port: int = 8081, host: str = "0.0.0.0") -> None:
    configure_logging()
    if not SITE_DIST_DIR.exists():
        logger.error("site_dist_not_found", dir=str(SITE_DIST_DIR))
        return

    server = ThreadingHTTPServer((host, port), SPARequestHandler)
    logger.info("pulse_site_server_started", host=host, port=port, dist=str(SITE_DIST_DIR))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("pulse_site_server_stopping")
        server.server_close()


if __name__ == "__main__":
    run_site_server()
