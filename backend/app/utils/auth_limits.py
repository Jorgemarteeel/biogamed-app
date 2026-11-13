"""Process-local fixed windows, keyed by socket peer, never forwarded headers."""
import math
import os
import time
from collections import OrderedDict
from threading import Lock
from fastapi import HTTPException, Request


def positive(name, default):
    value = int(os.getenv(name, str(default)))
    if value < 1:
        raise RuntimeError(f"{name} must be positive")
    return value


class AuthLimits:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.rules = {
            "login": (positive("AUTH_LOGIN_LIMIT", 120), positive("AUTH_LOGIN_WINDOW_SECONDS", 600)),
            "register": (positive("AUTH_REGISTER_LIMIT", 60), positive("AUTH_REGISTER_WINDOW_SECONDS", 3600)),
        }
        self.entries = OrderedDict()
        self.lock = Lock()
        self.capacity = 10000

    def check(self, kind, peer):
        limit, window = self.rules[kind]
        now = self.clock()
        key = (kind, peer)
        with self.lock:
            # Bounded state: expired peers are removed; oldest entries evicted at capacity.
            for expired in [k for k, (_, end) in self.entries.items() if end <= now]:
                del self.entries[expired]
            count, end = self.entries.get(key, (0, now + window))
            if count >= limit:
                raise HTTPException(429, "Demasiados intentos. Inténtalo más tarde.",
                                    headers={"Retry-After": str(max(1, math.ceil(end - now)))})
            if key not in self.entries and len(self.entries) >= self.capacity:
                self.entries.popitem(last=False)
            self.entries[key] = (count + 1, end)


limits = AuthLimits()


def login_limit(request: Request):
    limits.check("login", request.client.host if request.client else "unknown")


def register_limit(request: Request):
    limits.check("register", request.client.host if request.client else "unknown")
