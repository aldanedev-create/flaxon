import asyncio
import builtins
import io
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest

from flaxon import Flaxon
from flaxon.admin import AdminDashboard
from flaxon.admin.cms import CMS
from flaxon.admin.microservices import RemoteServiceClient, RemoteServiceError
from flaxon.admin.services import AdminAuth
from flaxon.exceptions import BadRequest, Forbidden, PayloadTooLarge, Unauthorized
from flaxon.files import UploadedFile
from flaxon.http import Request, Response
from flaxon.middleware.body_limit import BodyLimitMiddleware
from flaxon.middleware.proxy_headers import ProxyHeadersMiddleware
from flaxon.security import CSRF
from flaxon.security.sessions import Session, SessionManager
from flaxon.testing import TestClient


def request(headers=(), method="POST"):
    return Request({"type": "http", "method": method, "path": "/", "headers": list(headers)}, None)


def test_cookie_alone_cannot_authorize_csrf_request():
    csrf = CSRF("secret")
    token = csrf.generate_token()
    with pytest.raises(Forbidden):
        csrf.validate_request(request([(b"cookie", f"_csrf={token}".encode())]))
    csrf.validate_request(request([(b"x-csrf-token", token.encode())]))


def test_future_csrf_token_is_rejected():
    csrf = CSRF("secret")
    stamp = str(int(time.time()) + 7200)
    assert not csrf.verify_token(f"nonce.{stamp}.{csrf._sign(f'nonce.{stamp}')}")


@pytest.mark.parametrize("length", [b"0", b"1", b"8"])
def test_body_limit_counts_actual_chunks_with_content_length(length):
    async def run():
        chunks = iter([
            {"type": "http.request", "body": b"12345", "more_body": True},
            {"type": "http.request", "body": b"67890", "more_body": False},
        ])

        async def receive():
            return next(chunks)

        async def app(scope, receive, send):
            while (await receive()).get("more_body"):
                pass

        async def send(message):
            pass

        middleware = BodyLimitMiddleware(app, max_size=8)
        with pytest.raises(PayloadTooLarge):
            await middleware({"type": "http", "headers": [(b"content-length", length)]}, receive, send)

    asyncio.run(run())


def test_admin_mfa_failures_trigger_login_throttle(monkeypatch):
    auth = AdminAuth(users=[{"username": "admin", "password": "Admin123!"}])
    auth.users["admin"]["mfa_secret"] = auth.generate_mfa_secret()
    monkeypatch.setattr(auth, "verify_otp", lambda *args: False)
    for _ in range(10):
        assert asyncio.run(auth.login("admin", "Admin123!", otp="bad", client_key="client")) is None
    monkeypatch.setattr(auth, "verify_otp", lambda *args: True)
    assert asyncio.run(auth.login("admin", "Admin123!", otp="correct", client_key="client")) is None


def test_admin_session_uses_current_permissions_and_account_status():
    auth = AdminAuth(users=[{"username": "admin", "password": "Admin123!", "permissions": ["admin:write"]}])
    token = asyncio.run(auth.login("admin", "Admin123!"))
    auth.users["admin"]["permissions"] = ["admin:read"]
    req = SimpleNamespace(user=None, cookies={"session_id": token})
    assert asyncio.run(auth.current_user(req)).permissions == ["admin:read"]
    auth.users["admin"]["active"] = False
    with pytest.raises(Unauthorized):
        asyncio.run(auth.current_user(req))


def test_deleted_admin_session_cannot_authenticate():
    auth = AdminAuth(users=[{"username": "admin", "password": "Admin123!"}])
    token = asyncio.run(auth.login("admin", "Admin123!"))
    del auth.users["admin"]
    with pytest.raises(Unauthorized):
        asyncio.run(auth.current_user(SimpleNamespace(user=None, cookies={"session_id": token})))


def test_expired_signed_session_is_not_restored():
    manager = SessionManager("secret")
    session = Session("old-session", {"authenticated": True}, ttl=60)
    session._created = int(time.time()) - 120
    cookie = manager._encode(session)
    restored = manager.get_session(SimpleNamespace(cookies={"session": cookie}))
    assert restored.session_id != "old-session"
    assert restored.get("authenticated") is None


def test_signed_session_with_fractional_timestamp_round_trips():
    manager = SessionManager("secret")
    session = Session("active-session", {"authenticated": True})
    restored = manager.get_session(SimpleNamespace(cookies={"session": manager._encode(session)}))
    assert restored.session_id == "active-session"
    assert restored.get("authenticated") is True


def test_password_reset_invalidates_existing_admin_session():
    auth = AdminAuth(users=[{"username": "admin", "password": "Admin123!"}])
    token = asyncio.run(auth.login("admin", "Admin123!"))
    reset = auth.request_password_reset("admin")
    assert auth.reset_password(reset, "Changed123!")
    with pytest.raises(Unauthorized):
        asyncio.run(auth.current_user(SimpleNamespace(cookies={"session_id": token})))
    fresh = asyncio.run(auth.login("admin", "Changed123!"))
    assert asyncio.run(auth.current_user(SimpleNamespace(cookies={"session_id": fresh}))).username == "admin"


@pytest.mark.parametrize("peer", [None, ("203.0.113.8", 1234)])
def test_forwarded_headers_are_untrusted_by_default(peer):
    scope = {
        "type": "http",
        "client": peer,
        "scheme": "http",
        "headers": [
            (b"host", b"original.test"),
            (b"x-forwarded-for", b"127.0.0.1"),
            (b"x-forwarded-proto", b"https"),
            (b"x-forwarded-host", b"evil.test"),
        ],
    }

    async def app(scope, receive, send):
        assert scope["client"] == peer
        assert scope["scheme"] == "http"
        assert dict(scope["headers"])[b"host"] == b"original.test"

    asyncio.run(ProxyHeadersMiddleware(app)(scope, None, None))


def test_application_user_cannot_replace_admin_authentication():
    auth = AdminAuth(users=[{"username": "admin", "password": "Admin123!"}])
    with pytest.raises(Unauthorized):
        asyncio.run(auth.current_user(SimpleNamespace(user=auth.user("admin"), cookies={})))


def test_old_session_cannot_authenticate_recreated_account():
    auth = AdminAuth(users=[{"username": "admin", "password": "Admin123!"}])
    token = asyncio.run(auth.login("admin", "Admin123!"))
    auth.add_user({"username": "admin", "password": "Replacement123!"})
    with pytest.raises(Unauthorized):
        asyncio.run(auth.current_user(SimpleNamespace(cookies={"session_id": token})))


def test_trusted_proxy_can_forward_headers():
    scope = {
        "type": "http",
        "client": ("127.0.0.1", 1234),
        "scheme": "http",
        "headers": [(b"x-forwarded-for", b"203.0.113.7"), (b"x-forwarded-proto", b"https")],
    }

    async def app(scope, receive, send):
        assert scope["client"] == ("203.0.113.7", 0)
        assert scope["scheme"] == "https"

    asyncio.run(ProxyHeadersMiddleware(app, trusted_proxies=["127.0.0.1"])(scope, None, None))


def test_rejected_local_upload_does_not_leave_a_public_file(tmp_path):
    app = Flaxon("upload-regression")
    dashboard = AdminDashboard(
        app,
        upload_dir=str(tmp_path / "media"),
        storage_path=str(tmp_path / "admin.sqlite3"),
        users=[{"username": "admin", "password": "Admin123!", "roles": ["administrator"]}],
    )
    token = asyncio.run(dashboard.auth.login("admin", "Admin123!"))
    body = (
        '--security-test\r\nContent-Disposition: form-data; name="_csrf"\r\n\r\n'
        + dashboard.csrf_token()
        + '\r\n--security-test\r\nContent-Disposition: form-data; name="file"; filename="payload.html"'
        + "\r\nContent-Type: image/png\r\n\r\n<script>alert(1)</script>\r\n--security-test--\r\n"
    ).encode()
    response = TestClient(app).post(
        "/admin/media",
        content=body,
        headers={
            "cookie": f"session_id={token}",
            "content-type": "multipart/form-data; boundary=security-test",
        },
    )
    assert response.status_code == 400
    assert not list((tmp_path / "media").rglob("*.*"))


def test_cms_upload_cannot_store_html_extension(tmp_path):
    app = Flaxon("cms-upload-regression")
    AdminDashboard(app, upload_dir=str(tmp_path / "media"), storage_path=str(tmp_path / "admin.sqlite3"))
    cms = CMS(app)
    upload = UploadedFile("payload.html", "text/plain", 5, io.BytesIO(b"hello"))
    url = asyncio.run(cms._save_admin_upload(upload, SimpleNamespace(user=None, client=None)))
    assert url.endswith(".txt")
    assert not list((tmp_path / "media").glob("*.html"))


def test_image_validation_fails_closed_without_pillow(tmp_path, monkeypatch):
    dashboard = AdminDashboard(Flaxon("image-validation"), storage_path=str(tmp_path / "admin.sqlite3"))
    original_import = builtins.__import__

    def without_pillow(name, *args, **kwargs):
        if name == "PIL":
            raise ImportError("Pillow unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_pillow)
    with pytest.raises(BadRequest):
        asyncio.run(dashboard._validate_media_bytes(b"not an image", "image/png"))


def test_remote_service_redirect_does_not_forward_credentials():
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "/capture")
                self.end_headers()
            else:
                received.append(self.headers.get("Authorization"))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"{}")

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        client = RemoteServiceClient(
            f"http://127.0.0.1:{server.server_port}", token="service-secret", retries=0
        )
        with pytest.raises(RemoteServiceError):
            asyncio.run(client.request("GET", "/redirect"))
        assert received == []
        assert asyncio.run(client.request("GET", "/capture")) == {}
        assert received == ["Bearer service-secret"]
    finally:
        server.shutdown()
        server.server_close()
        worker.join()


@pytest.mark.parametrize("debug,secure", [(False, True), (True, False)])
def test_admin_cookie_security_follows_environment(tmp_path, debug, secure):
    dashboard = AdminDashboard(Flaxon("cookies", debug=debug), storage_path=str(tmp_path / "admin.sqlite3"))
    response = Response()
    dashboard.auth.attach_cookie(response, "test-token")
    header = dict(response.headers.to_asgi())[b"set-cookie"].decode()
    assert ("; Secure" in header) is secure
    assert "HttpOnly" in header
    assert "SameSite=Lax" in header
