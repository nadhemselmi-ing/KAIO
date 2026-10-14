"""KAIO ground segment: the mission-control server operators log into.

    python ground/manage.py add-user nadhem --role operator     # once
    python ground/server.py                                     # then open http://localhost:8000

Security model
* Login with username + password (scrypt hashes, rate-limited).
* Access token: signed JWT, 15 minutes, in an httpOnly cookie (JavaScript cannot read it).
* Refresh token: random, 7 days, httpOnly cookie sent only to /api/auth, rotated on every use;
  re-using an old refresh token revokes the whole session (token-theft detection).
* Cookies are SameSite=Strict and Secure; state-changing requests also need the X-KAIO header (CSRF).
* Roles: "viewer" can watch; "operator" can also send telecommands.
* Telecommands are signed with HMAC-SHA256 and a sequence number (kaio/telecommand.py);
  the satellite side verifies signature, freshness and safe limits before applying anything.
"""
from __future__ import annotations

import os
import sys
import time
from collections import defaultdict, deque

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import store  # noqa: E402
from kaio.engine import ELotusEngine  # noqa: E402
from kaio.telecommand import LIMITS, TCVerifier, sign  # noqa: E402

ACCESS_TTL = int(os.environ.get("KAIO_ACCESS_TTL", 15 * 60))
REFRESH_TTL = int(os.environ.get("KAIO_REFRESH_TTL", 7 * 24 * 3600))
SECURE = os.environ.get("KAIO_INSECURE_HTTP", "0") != "1"   # set to 1 only for plain-http tests on a LAN
DASHBOARD = os.path.join(ROOT, "web", "KAIO_Mission_Control.html")

con = store.db()
JWT_KEY = store.secret("jwt.key")
TC_KEY = store.secret("tc.key")

# the satellite, simulated in-process (on hardware this verifier runs on the onboard computer)
onboard_engine = ELotusEngine()
onboard = TCVerifier(TC_KEY, last_seq=(con.execute("SELECT MAX(seq) FROM tclog WHERE ok=1").fetchone()[0] or 0))
_last_packet: dict = {}

app = FastAPI(title="KAIO ground segment", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=os.path.join(HERE, "static")), name="static")
app.mount("/assets", StaticFiles(directory=os.path.join(ROOT, "web", "assets")), name="assets")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Cache-Control"] = "no-store"
    if SECURE:
        resp.headers["Strict-Transport-Security"] = "max-age=31536000"
    return resp


# ---- tokens and cookies -----------------------------------------------------------------------
def make_access(username: str, role: str) -> str:
    now = int(time.time())
    return jwt.encode({"sub": username, "role": role, "iat": now, "exp": now + ACCESS_TTL, "typ": "access"},
                      JWT_KEY, algorithm="HS256")


def set_session(resp: Response, username: str, role: str, refresh: str) -> None:
    resp.set_cookie("kaio_access", make_access(username, role), max_age=ACCESS_TTL, httponly=True,
                    secure=SECURE, samesite="strict", path="/")
    resp.set_cookie("kaio_refresh", refresh, max_age=REFRESH_TTL, httponly=True,
                    secure=SECURE, samesite="strict", path="/api/auth")


def clear_session(resp: Response) -> None:
    resp.delete_cookie("kaio_access", path="/", secure=SECURE, httponly=True, samesite="strict")
    resp.delete_cookie("kaio_refresh", path="/api/auth", secure=SECURE, httponly=True, samesite="strict")


def user_from(request: Request):
    tok = request.cookies.get("kaio_access")
    if not tok:
        return None
    try:
        claims = jwt.decode(tok, JWT_KEY, algorithms=["HS256"], options={"require": ["exp", "sub"]})
    except jwt.PyJWTError:
        return None
    if claims.get("typ") != "access" or store.role_of(con, claims["sub"]) is None:
        return None
    return {"username": claims["sub"], "role": store.role_of(con, claims["sub"]), "exp": claims["exp"]}


def need_user(request: Request):
    u = user_from(request)
    if u is None:
        raise HTTPException(401, "not authenticated")
    return u


def need_operator(u=Depends(need_user)):
    if u["role"] != "operator":
        raise HTTPException(403, "operator role required")
    return u


def csrf(request: Request):
    if request.headers.get("x-kaio") != "1":
        raise HTTPException(403, "missing X-KAIO header")


# ---- login rate limit: 5 failures per 15 min per (ip, user), 20 per ip ------------------------------
FAILS = defaultdict(deque)
WINDOW = 15 * 60


def _limited(key, limit) -> bool:
    q, now = FAILS[key], time.time()
    while q and q[0] < now - WINDOW:
        q.popleft()
    return len(q) >= limit


# ---- pages -----------------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    if user_from(request) is None:
        return RedirectResponse("/login", status_code=303)
    html = open(DASHBOARD, encoding="utf-8").read()
    tag = '<script src="/static/session.js"></script>'
    i = html.rfind("</body>")
    return HTMLResponse(html[:i] + tag + html[i:] if i >= 0 else html + tag)


@app.get("/login")
def login_page():
    return FileResponse(os.path.join(HERE, "static", "login.html"))


# ---- auth API --------------------------------------------------------------------------------
class Login(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


@app.post("/api/auth/login", dependencies=[Depends(csrf)])
def login(body: Login, request: Request):
    ip = request.client.host if request.client else "?"
    if _limited((ip, body.username), 5) or _limited(ip, 20):
        raise HTTPException(429, "too many failed attempts, try again in 15 minutes")
    role = store.check_user(con, body.username, body.password)
    if role is None:
        FAILS[(ip, body.username)].append(time.time()); FAILS[ip].append(time.time())
        raise HTTPException(401, "wrong username or password")
    FAILS.pop((ip, body.username), None)
    resp = JSONResponse({"username": body.username, "role": role})
    set_session(resp, body.username, role, store.new_refresh(con, body.username, REFRESH_TTL))
    return resp


@app.post("/api/auth/refresh", dependencies=[Depends(csrf)])
def refresh(request: Request):
    tok = request.cookies.get("kaio_refresh")
    if not tok:
        raise HTTPException(401, "no refresh token")
    username, new = store.rotate_refresh(con, tok, REFRESH_TTL)
    role = store.role_of(con, username) if username else None
    if role is None:
        resp = JSONResponse({"detail": new if username is None else "user removed"}, status_code=401)
        clear_session(resp)
        return resp
    resp = JSONResponse({"username": username, "role": role})
    set_session(resp, username, role, new)
    return resp


@app.post("/api/auth/logout", dependencies=[Depends(csrf)])
def logout(request: Request):
    tok = request.cookies.get("kaio_refresh")
    if tok:
        store.revoke_refresh(con, tok)
    resp = JSONResponse({"ok": True})
    clear_session(resp)
    return resp


@app.get("/api/me")
def me(u=Depends(need_user)):
    return u


# ---- telecommands ------------------------------------------------------------------------------
def onboard_state():
    g = onboard_engine.guard
    return {"V": onboard_engine.V, "energy_margin_wh": g.energy_margin_wh, "thermal_margin_k": g.thermal_margin_k,
            "alert_override": float(g.alert_override), "use_isl": float(onboard_engine.use_isl)}


def tc_log(n=12):
    rows = con.execute("SELECT seq, ts, username, param, value, mac, ok, result FROM tclog ORDER BY id DESC LIMIT ?", (n,)).fetchall()
    return [dict(zip(("seq", "ts", "username", "param", "value", "mac", "ok", "result"), r)) for r in rows]


@app.get("/api/tc")
def tc_status(u=Depends(need_user)):
    return {"limits": {k: [lo, hi, d] for k, (lo, hi, d) in LIMITS.items()}, "state": onboard_state(),
            "last_seq": onboard.last_seq, "log": tc_log(), "can_send": u["role"] == "operator"}


class TC(BaseModel):
    param: str
    value: float


def _record(pkt, username, ok, why):
    con.execute("INSERT INTO tclog(seq, ts, username, param, value, mac, ok, result) VALUES(?,?,?,?,?,?,?,?)",
                (pkt.get("seq"), time.time(), username, pkt.get("param"), pkt.get("value"), pkt.get("mac"), int(ok), why))


@app.post("/api/tc", dependencies=[Depends(csrf)])
def send_tc(body: TC, u=Depends(need_operator)):
    global _last_packet
    pkt = sign(TC_KEY, onboard.last_seq + 1, body.param, body.value)
    ok, why = onboard.apply(pkt, onboard_engine)
    _record(pkt, u["username"], ok, why)
    if ok:
        _last_packet = pkt
    return {"packet": pkt, "ok": ok, "result": why, "state": onboard_state()}


class Attack(BaseModel):
    kind: str = Field(pattern="^(replay|tamper)$")


@app.post("/api/tc/attack", dependencies=[Depends(csrf)])
def attack(body: Attack, u=Depends(need_operator)):
    """Demonstration: what the satellite does with a replayed or modified packet."""
    if not _last_packet:
        raise HTTPException(400, "send one valid telecommand first")
    pkt = dict(_last_packet)
    if body.kind == "tamper":
        pkt["seq"] = onboard.last_seq + 1
        pkt["value"] = LIMITS[pkt["param"]][1]          # attacker changes the value but cannot re-sign
    ok, why = onboard.apply(pkt, onboard_engine)
    _record(pkt, u["username"] + f" ({body.kind} test)", ok, why)
    return {"packet": pkt, "ok": ok, "result": why, "state": onboard_state()}


if __name__ == "__main__":
    import argparse
    import uvicorn
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--cert", help="TLS certificate (PEM) for HTTPS")
    ap.add_argument("--key", help="TLS private key (PEM)")
    a = ap.parse_args()
    if con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        print("No users yet. Create one first:  python ground/manage.py add-user <name> --role operator")
        sys.exit(1)
    uvicorn.run(app, host=a.host, port=a.port, ssl_certfile=a.cert, ssl_keyfile=a.key)
