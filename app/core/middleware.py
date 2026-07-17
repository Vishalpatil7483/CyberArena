"""Custom middleware."""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import get_settings


class SecurityHeadersMiddleware:
    """Attach basic security headers to every response.

    Implemented as pure ASGI middleware (no BaseHTTPMiddleware overhead).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        settings = get_settings()
        headers = {
            b"x-content-type-options": b"nosniff",
            b"x-frame-options": b"DENY",
            b"referrer-policy": b"strict-origin-when-cross-origin",
            b"permissions-policy": b"camera=(), microphone=(), geolocation=()",
            b"content-security-policy": (
                b"default-src 'self'; "
                b"style-src 'self' https://cdn.jsdelivr.net; "
                b"script-src 'self' https://cdn.jsdelivr.net; "
                b"font-src 'self' https://cdn.jsdelivr.net; "
                b"img-src 'self' data:; "
                b"form-action 'self'; "
                b"base-uri 'self'; "
                b"frame-ancestors 'none'"
            ),
        }
        if settings.is_production:
            headers[b"strict-transport-security"] = (
                b"max-age=31536000; includeSubDomains"
            )
        self._headers = list(headers.items())

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                message.setdefault("headers", [])
                message["headers"].extend(self._headers)
            await send(message)

        await self.app(scope, receive, send_with_headers)
