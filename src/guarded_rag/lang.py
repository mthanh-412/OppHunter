from __future__ import annotations

import re
import unicodedata

_VI_MARKS = {"\u0302", "\u0309", "\u0323", "\u031b", "\u0306"}

_VI_PLAIN = re.compile(r"\b(hoc bong|han nop|khi nao|bao nhieu|nhu the nao|cho toi|toi muon|ho so)\b")


def fold(text: str) -> str:
    """Hạ chữ thường và bỏ dấu tiếng Việt (đ thành d)."""
    text = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def is_vietnamese(text: str, hint: str | None = None) -> bool:
    """True nếu câu có ký tự đặc trưng tiếng Việt, hoặc là tiếng Việt không dấu với cụm quen thuộc."""
    if "đ" in text.lower():
        return True
    decomposed = unicodedata.normalize("NFD", text)
    if any(ch in _VI_MARKS for ch in decomposed):
        return True
    if _VI_PLAIN.search(fold(text)):
        return True
    return hint == "vi" and any(unicodedata.category(ch) == "Mn" for ch in decomposed)