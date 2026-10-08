
"""Small dependency-free REST utility service."""
from __future__ import annotations
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def response(status: int, payload, content_type: str = "application/json"):
    if content_type == "application/json":
        data = json.dumps(payload, ensure_ascii=False).encode()
    elif isinstance(payload, str):
        data = payload.encode()
    else:
        data = payload
    return status, {"Content-Type": content_type, "Content-Length": str(len(data))}, data


def error(message: str, status: int = 400):
    return response(status, {"error": message})


class Handler(BaseHTTPRequestHandler):
    def _serve(self, method: str):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            payload = None
        status, headers, body = handle(method, self.path.split("?", 1)[0], payload)
        self.send_response(status)
        for key, value in headers.items(): self.send_header(key, value)
        self.end_headers(); self.wfile.write(body)
    do_GET = lambda self: self._serve("GET")
    do_POST = lambda self: self._serve("POST")
    do_PUT = lambda self: self._serve("PUT")
    do_DELETE = lambda self: self._serve("DELETE")
    def log_message(self, *_): pass


import base64, html, os, subprocess, tempfile, zipfile
from xml.etree import ElementTree

def _docx(data):
    with zipfile.ZipFile(__import__("io").BytesIO(data)) as z: return " ".join(ElementTree.fromstring(z.read("word/document.xml")).itertext())

def handle(method, path, payload):
    if method == "GET" and path == "/health": return response(200, {"ok": True, "service": "document-converter-api"})
    if method != "POST" or path != "/convert": return error("route not found", 404)
    if not isinstance(payload, dict) or not payload.get("data") or payload.get("target") not in {"txt", "html", "pdf"}: return error("data and target (txt, html, pdf) are required")
    try:
        raw = base64.b64decode(payload["data"], validate=True); source = payload.get("source", "txt")
        text = _docx(raw) if source == "docx" else raw.decode("utf-8")
    except Exception as exc: return error(f"invalid source: {exc}")
    if payload["target"] == "html": out = f"<pre>{html.escape(text)}</pre>".encode()
    elif payload["target"] == "txt": out = text.encode()
    else:
        return error("PDF conversion requires an external adapter; use html-to-pdf-api", 501)
    return response(200, {"data": base64.b64encode(out).decode(), "target": payload["target"]})


def serve(host="0.0.0.0", port=8080):
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    serve()
