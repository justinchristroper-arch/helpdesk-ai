"""Trust Vercel's overwritten header only inside the Vercel runtime."""
import os
from ipaddress import ip_address

from fastapi import Request


def client_ip(request: Request) -> str:
    if os.getenv("VERCEL") == "1":
        value = request.headers.get("x-vercel-forwarded-for", "").strip()
        try:
            return str(ip_address(value))
        except ValueError:
            # Missing/ambiguous metadata shares a conservative quota bucket.
            return "unknown-vercel-client"
    return request.client.host if request.client else "unknown"
