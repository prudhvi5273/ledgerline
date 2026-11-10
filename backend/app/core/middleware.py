import time
import uuid
from collections import defaultdict
from typing import Dict, List, Tuple
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Applies OWASP-recommended security headers and request-id tracing to all HTTP responses.
    """
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.perf_counter()
        response: Response = await call_next(request)
        process_time = time.perf_counter() - start_time

        # Financial platform security headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{process_time * 1000:.2f}ms"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"

        return response


class LoginRateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter protecting authentication endpoints against brute force attacks.
    Limits each client IP to at most 10 login attempts per 60 seconds.
    """
    def __init__(self, app, max_attempts: int = 10, window_seconds: int = 60):
        super().__init__(app)
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts: Dict[str, List[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Only rate limit POST requests to auth login/register
        if request.method == "POST" and (
            request.url.path.endswith("/auth/login") or request.url.path.endswith("/auth/register")
        ):
            client_ip = request.client.host if request.client else "unknown"
            now = time.time()
            cutoff = now - self.window_seconds

            # Prune attempts outside sliding window
            self.attempts[client_ip] = [t for t in self.attempts[client_ip] if t > cutoff]

            if len(self.attempts[client_ip]) >= self.max_attempts:
                retry_after = int(self.window_seconds - (now - self.attempts[client_ip][0]))
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Too many authentication requests. Please try again later.",
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "retry_after_seconds": max(1, retry_after)
                    },
                    headers={"Retry-After": str(max(1, retry_after))}
                )

            # Record attempt
            self.attempts[client_ip].append(now)

        return await call_next(request)
