"""Local-only UI. No model calls or shell execution exposed over HTTP."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import mimetypes
import secrets
import threading
import time
from urllib.parse import parse_qs, urlparse

from .documents import digest
from .store import Conflict


class ProjectionCache:
    def __init__(self, service):
        self.service = service
        self.good = None
        self.lock = threading.Lock()

    def get(self):
        with self.lock:
            fresh = self.service.state()
            if not fresh['errors']:
                self.good = fresh
            elif self.good:
                fresh = {**self.good, 'errors': fresh['errors'], 'stale': True}
            else:
                fresh = {**fresh, 'objects': [], 'mainline': [], 'library': [], 'project': None, 'stale': True}
            return fresh


def make_server(service, port=8765):
    token = secrets.token_urlsafe(24)
    cache = ProjectionCache(service)
    static = Path(__file__).parent / 'static'

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def allowed_host(self):
            return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')

        def respond(self, status, body, content_type='application/json; charset=utf-8'):
            if not isinstance(body, bytes):
                body = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self'; frame-src 'none'; object-src 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if not self.allowed_host():
                return self.respond(403, {'error': 'Invalid host'})
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            path = parsed.path
            try:
                if path in ('/', '/app.js', '/graph-layout.js', '/style.css', '/facets.svg'):
                    filename = 'index.html' if path == '/' else path[1:]
                    p = static / filename
                    return self.respond(200, p.read_bytes(), mimetypes.guess_type(filename)[0] + '; charset=utf-8')
                if path == '/api/state':
                    return self.respond(200, {**cache.get(), 'token': token})
                if path == '/api/file':
                    relative = query['path'][0]
                    if not service.store.editable(relative):
                        raise ValueError('File is not editable')
                    data = service.store.path(relative).read_bytes()
                    return self.respond(200, {'path': relative, 'raw': data.decode('utf-8-sig'), 'revision': digest(data)})
                if path == '/api/context':
                    return self.respond(200, {'text': service.context(query['id'][0], reviewer=query.get('reviewer') == ['1'])})
                if path == '/api/artifact':
                    relative = query['path'][0]
                    state = cache.get()
                    allowed = set()
                    for obj in state['objects']:
                        for field in ('evidence', 'before', 'after', 'artifacts_retained', 'artifacts_promoted'):
                            allowed.update(obj['meta'].get(field, []))
                    allowed.update('library/' + x['location'] for x in state['library'] if not x['location'].startswith(('http://', 'https://')))
                    if relative not in allowed:
                        raise ValueError('Artifact is not explicitly referenced')
                    p = service.store.path(relative)
                    # Text is always served as plain text, never executable HTML/SVG.
                    mime = mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
                    if mime not in ('image/png', 'image/jpeg', 'image/webp', 'image/gif', 'video/mp4', 'video/webm', 'application/pdf'):
                        mime = 'text/plain; charset=utf-8'
                    return self.respond(200, p.read_bytes(), mime)
                if path == '/api/events':
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/event-stream')
                    self.send_header('Cache-Control', 'no-store')
                    self.end_headers()
                    last = None
                    for _ in range(120):
                        payload = json.dumps(cache.get(), ensure_ascii=False, sort_keys=True)
                        current = digest(payload.encode())
                        if current != last:
                            self.wfile.write(('data: ' + current + '\n\n').encode())
                            last = current
                        else:
                            self.wfile.write(b': heartbeat\n\n')
                        self.wfile.flush()
                        time.sleep(1)
                    return
                self.respond(404, {'error': 'Not found'})
            except ConnectionError:
                pass
            except (ValueError, OSError, KeyError) as exc:
                self.respond(400, {'error': str(exc)})

        def do_POST(self):
            if not self.allowed_host() or self.headers.get('X-Infra-Token') != token:
                return self.respond(403, {'error': 'Invalid local session token'})
            origin = self.headers.get('Origin')
            if origin and origin not in (f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'):
                return self.respond(403, {'error': 'Invalid origin'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 2_000_000:
                    raise ValueError('Invalid request size')
                body = json.loads(self.rfile.read(length))
                if self.path == '/api/update':
                    service.update(body['path'], body['revision'], body.get('fields'), body.get('sections'), body.get('raw'))
                    result = {'ok': True}
                elif self.path == '/api/create':
                    result = {'id': service.create(body['kind'], body['title'], body.get('parent'), body.get('anchor'), body.get('predecessors'))}
                else:
                    return self.respond(404, {'error': 'Unknown command'})
                self.respond(200, result)
            except Conflict as exc:
                self.respond(409, {'error': str(exc)})
            except (ValueError, OSError, KeyError, TypeError) as exc:
                self.respond(400, {'error': str(exc)})

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    return server


def serve(service, port):
    server = make_server(service, port)
    print(f'Project Infra: http://127.0.0.1:{server.server_port}', flush=True)
    print('Local file editing enabled. Ctrl+C to stop.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
