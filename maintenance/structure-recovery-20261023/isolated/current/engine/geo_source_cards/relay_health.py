"""Separate loop activity from successful transport and delivery."""

import time


def observation(previous, result=None, *, error=None, now=None):
    now = time.time() if now is None else now
    previous = previous if isinstance(previous, dict) else {}
    old = previous.get("transport", {})
    old = old if isinstance(old, dict) else {}
    transport = {
        "status": "ERROR" if error else "OK",
        "last_attempt_epoch": now,
        "last_success_epoch": old.get("last_success_epoch") if error else now,
        "consecutive_failures": int(old.get("consecutive_failures", 0)) + 1
        if error
        else 0,
        "last_error": type(error).__name__ if error else None,
    }
    return {
        "status": "connection_or_delivery_error" if error else "ready",
        "checked_epoch": now,
        **({"error_type": type(error).__name__} if error else result or {}),
        "transport": transport,
    }
