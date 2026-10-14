"""Ground segment: login, httpOnly cookies, refresh-token rotation, roles and CSRF header."""
import importlib
import os
import sys

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

H = {"X-KAIO": "1"}


@pytest.fixture()
def srv(tmp_path, monkeypatch):
    monkeypatch.setenv("KAIO_GROUND_DATA", str(tmp_path))
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "ground"))
    import store
    import server
    importlib.reload(store); importlib.reload(server)
    store.add_user(server.con, "op", "operator-pass-1", "operator")
    store.add_user(server.con, "jury", "viewer-pass-12", "viewer")
    return server


def client(srv):
    return TestClient(srv.app, base_url="https://testserver")


def login(c, u, p):
    return c.post("/api/auth/login", json={"username": u, "password": p}, headers=H)


def test_dashboard_needs_login_and_cookies_are_httponly(srv):
    c = client(srv)
    assert c.get("/", follow_redirects=False).status_code == 303
    r = login(c, "op", "operator-pass-1")
    assert r.status_code == 200
    sc = r.headers.get_list("set-cookie")
    assert all("httponly" in s.lower() and "secure" in s.lower() and "samesite=strict" in s.lower() for s in sc)
    assert any(s.startswith("kaio_refresh=") and "Path=/api/auth" in s for s in sc)
    assert c.get("/").status_code == 200 and "session.js" in c.get("/").text


def test_wrong_password_and_rate_limit(srv):
    c = client(srv)
    for _ in range(5):
        assert login(c, "op", "nope-nope-nope").status_code == 401
    assert login(c, "op", "operator-pass-1").status_code == 429


def test_csrf_header_required(srv):
    c = client(srv)
    assert c.post("/api/auth/login", json={"username": "op", "password": "operator-pass-1"}).status_code == 403


def test_refresh_rotates_and_reuse_revokes_session(srv):
    c = client(srv)
    login(c, "op", "operator-pass-1")
    old = c.cookies.get("kaio_refresh", path="/api/auth")
    assert c.post("/api/auth/refresh", headers=H).status_code == 200
    new = c.cookies.get("kaio_refresh", path="/api/auth")
    assert new and new != old
    thief = client(srv); thief.cookies.set("kaio_refresh", old, domain="testserver.local", path="/api/auth")
    r = thief.post("/api/auth/refresh", headers=H)
    assert r.status_code == 401 and "re-used" in r.json()["detail"]
    assert c.post("/api/auth/refresh", headers=H).status_code == 401      # whole family revoked


def test_roles_and_signed_telecommands(srv):
    v = client(srv); login(v, "jury", "viewer-pass-12")
    assert v.post("/api/tc", json={"param": "V", "value": 0.5}, headers=H).status_code == 403
    o = client(srv); login(o, "op", "operator-pass-1")
    r = o.post("/api/tc", json={"param": "V", "value": 0.5}, headers=H).json()
    assert r["ok"] and r["state"]["V"] == 0.5
    assert not o.post("/api/tc", json={"param": "V", "value": 50}, headers=H).json()["ok"]
    assert not o.post("/api/tc/attack", json={"kind": "replay"}, headers=H).json()["ok"]
    assert o.post("/api/tc/attack", json={"kind": "tamper"}, headers=H).json()["result"] == "bad signature"


def test_logout_revokes(srv):
    c = client(srv); login(c, "op", "operator-pass-1")
    assert c.post("/api/auth/logout", headers=H).status_code == 200
    assert c.get("/api/me").status_code == 401
    assert c.post("/api/auth/refresh", headers=H).status_code == 401
