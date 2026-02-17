"""In-memory sliding-window rate limiter middleware.

Limits requests per IP address with separate budgets for read (GET) and
write (POST) operations. Uses a simple token-bucket approach stored in
a dict — no external dependencies. Suitable for single-instance MVP;
swap for Redis-backed limiter when horizontally scaling.
"""

import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        read_limit: int = 60,       # GET requests per window
        write_limit: int = 10,       # POST requests per window
        window_seconds: int = 60,    # Sliding window size
    ):
        super().__init__(app)
        self.read_limit = read_limit
        self.write_limit = write_limit
        self.window = window_seconds
        # {bucket_key: [timestamp, ...]}
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def reset(self):
        """Clear all rate limit state. Used in tests."""
        self._buckets.clear()

    def _client_ip(self, request: Request) -> str:
        """Extract client IP, respecting X-Forwarded-For behind a proxy."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _prune(self, key: str, now: float) -> list[float]:
        """Remove timestamps outside the current window."""
        cutoff = now - self.window
        self._buckets[key] = [t for t in self._buckets[key] if t > cutoff]
        return self._buckets[key]

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)

        ip = self._client_ip(request)
        now = time.monotonic()
        is_write = request.method in ("POST", "PUT", "PATCH", "DELETE")

        # Use separate buckets for read vs write
        bucket_key = f"{ip}:{'w' if is_write else 'r'}"
        timestamps = self._prune(bucket_key, now)
        limit = self.write_limit if is_write else self.read_limit

        if len(timestamps) >= limit:
            retry_after = int(self.window - (now - timestamps[0])) + 1
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        self._buckets[bucket_key].append(now)

        response = await call_next(request)
        # Add rate limit headers for transparency
        remaining = limit - len(self._buckets[bucket_key])
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        return response
