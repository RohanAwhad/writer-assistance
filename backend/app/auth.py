"""INT-006 auth gate (R-075, SD-22/SD-23): AUTH_API_KEY login surface + stateless session cookie.

State lives entirely in the signed ``wa_session`` cookie (SD-23): the signing key
derives deterministically from AUTH_API_KEY (no new secret), and verification is
per-request constant-time HMAC + expiry check. ``install_gate`` wires the
middleware and login/logout routes into an app instance and is called only when
the gate is active (SD-24), so a gate-off instance exposes no login surface.
"""

import base64
import hashlib
import hmac
import json
import time
from collections.abc import Awaitable, Callable
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

SESSION_COOKIE = "wa_session"
SESSION_TTL_SECONDS = 30 * 24 * 60 * 60
_SIGNING_CONTEXT = b"writer-assistance-session-v1"
UNAUTHENTICATED_DETAIL = "authentication required"
_OPEN_PATHS = ("/login", "/logout")


def _signing_key(api_key: str) -> bytes:
    return hmac.new(api_key.encode("utf-8"), _SIGNING_CONTEXT, hashlib.sha256).digest()


def make_session_value(api_key: str, now: int | None = None) -> str:
    """Cookie value ``<base64url json {"exp": unix}>.`` + ``<hex hmac>`` (SD-23).

    ``now`` lets tests mint expired cookies; it defaults to the current time.
    """
    issued = int(time.time()) if now is None else now
    payload = (
        base64.urlsafe_b64encode(
            json.dumps({"exp": issued + SESSION_TTL_SECONDS}, separators=(",", ":")).encode("utf-8")
        )
        .rstrip(b"=")
        .decode("ascii")
    )
    digest = hmac.new(_signing_key(api_key), payload.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{payload}.{digest}"


def session_is_valid(api_key: str, cookie_value: str | None, now: int | None = None) -> bool:
    """True iff the cookie re-verifies against the key and its exp is in the future."""
    if not cookie_value:
        return False
    payload, separator, digest = cookie_value.partition(".")
    if not separator or not digest:
        return False
    expected = hmac.new(_signing_key(api_key), payload.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, digest):
        return False
    try:
        padded = payload + "=" * (-len(payload) % 4)
        exp = json.loads(base64.urlsafe_b64decode(padded))["exp"]
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        # A malformed cookie is an unauthenticated request, never a 500 (SD-27).
        return False
    current = int(time.time()) if now is None else now
    return isinstance(exp, int) and exp > current


def request_is_https(request: Request) -> bool:
    """Secure-cookie decision (SD-23): https scheme or X-Forwarded-Proto: https."""
    if request.url.scheme == "https":
        return True
    forwarded = request.headers.get("x-forwarded-proto")
    return forwarded is not None and forwarded.lower() == "https"


def login_page(error: bool = False) -> str:
    """Minimal self-contained login page (SD-22): no SPA assets, posts to /login."""
    marker = '<p id="login-error">Incorrect key — try again.</p>' if error else ""
    return _LOGIN_PAGE_HTML.replace("__ERROR_MARKER__", marker)


_LOGIN_PAGE_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sign in · Writer Assistance</title>
<style>
  body { font-family: system-ui, sans-serif; background: #f4f4f5; display: flex;
         align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
  main { background: #fff; border: 1px solid #e4e4e7; border-radius: 12px; padding: 2rem;
         width: min(22rem, 90vw); box-shadow: 0 4px 12px rgb(0 0 0 / .06); }
  h1 { font-size: 1.1rem; margin: 0 0 .25rem; }
  .sub { color: #71717a; font-size: .85rem; margin: 0 0 1.25rem; }
  label { font-size: .85rem; color: #3f3f46; }
  input { width: 100%; box-sizing: border-box; padding: .55rem .6rem; margin-top: .25rem;
          border: 1px solid #d4d4d8; border-radius: 8px; font-size: 1rem; }
  button { margin-top: 1rem; width: 100%; padding: .55rem; border: 0; border-radius: 8px;
           background: #18181b; color: #fff; font-size: .95rem; cursor: pointer; }
  #login-error { color: #b91c1c; font-size: .85rem; margin: 0 0 .75rem; }
</style>
</head>
<body>
  <main>
    <h1>Writer Assistance</h1>
    <p class="sub">Sign in to continue.</p>
    __ERROR_MARKER__
    <form method="post" action="/login">
      <label for="key">API key</label>
      <input id="key" name="key" type="password" autocomplete="current-password" autofocus required>
      <button type="submit">Sign in</button>
    </form>
  </main>
</body>
</html>
"""


def _keys_match(submitted: str, api_key: str) -> bool:
    return hmac.compare_digest(
        submitted.encode("utf-8", "surrogatepass"), api_key.encode("utf-8")
    )


async def _session_gate(
    request: Request, call_next: Callable[[Request], Awaitable[Response]], api_key: str
) -> Response:
    """Per-request gate (R-075): 401 JSON for /api/*, 302 /login for everything else.

    /login and /logout are open; a valid session passes through. Registered only
    when the gate is active (SD-24).
    """
    path = request.url.path
    if path in _OPEN_PATHS or session_is_valid(api_key, request.cookies.get(SESSION_COOKIE)):
        return await call_next(request)
    if path.startswith("/api"):
        return JSONResponse(status_code=401, content={"detail": UNAUTHENTICATED_DETAIL})
    return RedirectResponse("/login", status_code=302)


def install_gate(app: FastAPI, api_key: str) -> None:
    """Wire the gate into an app instance: middleware + login/logout routes."""

    @app.middleware("http")
    async def gate(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        return await _session_gate(request, call_next, api_key)

    @app.get("/login", include_in_schema=False)
    def get_login(request: Request) -> Response:
        if session_is_valid(api_key, request.cookies.get(SESSION_COOKIE)):
            return RedirectResponse("/", status_code=302)
        return HTMLResponse(login_page())

    @app.post("/login", include_in_schema=False)
    async def post_login(request: Request) -> Response:
        raw = (await request.body()).decode("utf-8", errors="replace")
        submitted = parse_qs(raw, keep_blank_values=True).get("key")
        candidate = submitted[0] if submitted else ""
        if candidate and _keys_match(candidate, api_key):
            response = RedirectResponse("/", status_code=302)
            response.set_cookie(
                SESSION_COOKIE,
                make_session_value(api_key),
                max_age=SESSION_TTL_SECONDS,
                path="/",
                httponly=True,
                samesite="lax",
                secure=request_is_https(request),
            )
            return response
        return HTMLResponse(login_page(error=True), status_code=401)

    @app.post("/logout", include_in_schema=False)
    def post_logout(request: Request) -> Response:
        response = RedirectResponse("/login", status_code=302)
        response.delete_cookie(
            SESSION_COOKIE,
            path="/",
            httponly=True,
            samesite="lax",
            secure=request_is_https(request),
        )
        return response
