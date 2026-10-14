# KAIO ground segment — mission-control server

The dashboard also works as an offline file (`web/KAIO_Mission_Control.html`). This server is the
**deployable version**: operators sign in, and only operators can send commands to the satellite.

## Run it (5 minutes)

```bash
pip install -r ground/requirements.txt
python ground/manage.py add-user nadhem --role operator     # asks for a password (10+ characters)
python ground/manage.py add-user jury --role viewer
python ground/server.py                                     # open http://localhost:8000
```

On another computer of the network (or in production) run it behind HTTPS:

```bash
python ground/server.py --host 0.0.0.0 --port 8443 --cert cert.pem --key key.pem
```

(`KAIO_INSECURE_HTTP=1` allows plain http on a test LAN only; cookies are then not marked Secure.)

## Security model

| Layer | What it does |
|---|---|
| Passwords | scrypt hash + random salt (never stored in clear); same work for unknown users, so timing does not reveal valid names |
| Login rate limit | 5 failures per user and IP in 15 min, 20 per IP |
| Access token | signed JWT (HS256), **15 min**, cookie `kaio_access`: **httpOnly, Secure, SameSite=Strict** |
| Refresh token | random 256-bit, **7 days**, cookie `kaio_refresh` (httpOnly, Secure, SameSite=Strict, only sent to `/api/auth`); stored as a SHA-256 hash; **rotated on every use**; re-using an old one revokes the whole session (theft detection) |
| CSRF | SameSite=Strict cookies + every POST needs the `X-KAIO: 1` header |
| Roles | `viewer` watches; `operator` can also send telecommands |
| Headers | X-Frame-Options DENY, nosniff, no-referrer, no-store, HSTS |
| Telecommands | signed with HMAC-SHA256 + sequence number (`kaio/telecommand.py`); the satellite checks signature, freshness (anti-replay) and safe limits before applying anything |

Secrets (`jwt.key`, `tc.key`) are created on first start in `ground/data/` with owner-only permissions,
or read from the environment (`KAIO_JWT_KEY`, `KAIO_TC_KEY`). The same `tc.key` is loaded on the satellite.

## Files

- `server.py` — FastAPI app: login/refresh/logout, pages, telecommand API
- `store.py` — SQLite: users, refresh tokens, telecommand log
- `manage.py` — add / list / remove users
- `static/login.html` — sign-in page (EN/FR)
- `static/session.js` — added to the dashboard: user badge, sign out, silent refresh, Telecommands panel
- `../kaio/telecommand.py` — signing (ground) and verification (onboard), standard library only

Tests: `python -m pytest tests/test_ground.py tests/test_telecommand.py` (10 tests).
