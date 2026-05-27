"""
Shield Suite — content filters.
Pure functions — no side effects, easy to unit-test.
"""
from __future__ import annotations
import re

# Common URL pattern (t.me invite links, http/https, etc.)
_URL_RE = re.compile(
    r"(https?://\S+|t\.me/\S+|@\w{4,})",
    re.IGNORECASE,
)

# Patterns commonly used in spam
_SPAM_PATTERNS = re.compile(
    r"(earn|كسب|ربح|اشتراك|مجاني|اربح|win|prize|click here|اضغط هنا)",
    re.IGNORECASE,
)


def contains_link(text: str) -> bool:
    return bool(_URL_RE.search(text))


def looks_like_spam(text: str) -> bool:
    return bool(_SPAM_PATTERNS.search(text))


def is_forwarded(message) -> bool:
    return message.forward_origin is not None


def is_bot_account(user) -> bool:
    return user.is_bot


def suspicious_account(user) -> bool:
    """
    Heuristic: very new accounts with no username tend to be spam bots.
    aiogram doesn't expose account age, so we check proxy signals.
    """
    return not user.username and not user.last_name
