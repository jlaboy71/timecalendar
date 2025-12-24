"""
Security headers middleware for the TJM Time Calendar application.

Adds security-related HTTP headers to all responses to protect against
common web vulnerabilities like XSS, clickjacking, and content sniffing.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all HTTP responses.

    Headers added:
    - X-Content-Type-Options: Prevents MIME type sniffing
    - X-Frame-Options: Prevents clickjacking by disabling iframe embedding
    - X-XSS-Protection: Legacy XSS protection for older browsers
    - Referrer-Policy: Controls referrer information sent with requests
    - Content-Security-Policy: Controls resource loading sources
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and add security headers to response."""
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking - deny all iframe embedding
        response.headers["X-Frame-Options"] = "DENY"

        # Legacy XSS protection for older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy
        # NiceGUI requires 'unsafe-inline' and 'unsafe-eval' for its reactive UI
        # blob: and data: needed for file downloads, embedded images, and voice features
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:",  # blob: for Web Speech API
            "script-src-elem 'self' 'unsafe-inline' blob:",
            "worker-src 'self' blob:",  # For web workers
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: blob:",
            "font-src 'self' data:",
            "connect-src 'self' ws: wss: https:",  # WebSocket for NiceGUI reactivity
            "media-src 'self' blob: data:",  # For audio playback (TTS)
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        return response


def add_security_headers(app):
    """
    Add security headers middleware to a FastAPI/Starlette application.

    Args:
        app: FastAPI or Starlette application instance

    Usage:
        from src.middleware.security import add_security_headers
        add_security_headers(app)
    """
    app.add_middleware(SecurityHeadersMiddleware)
