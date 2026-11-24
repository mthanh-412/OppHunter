from __future__ import annotations

import re

from ..lang import fold

_PATTERNS_VI = [
    ("vi_override",
     r"\b(bo qua|lo di|huy bo)\b[^.\n]{0,40}\b(huong dan|chi dan|quy tac|chi thi|cau lenh)\b"
     r"[^.\n]{0,40}\b(truoc do|truoc day|o tren|ban dau|cua ban|da duoc cho|he thong)\b"),
    ("vi_forget_rules",
     r"\bquen\b[^.\n]{0,20}\b(huong dan|chi dan|quy tac|chi thi)\b"
     r"[^.\n]{0,30}\b(truoc do|truoc day|cua ban|da duoc cho)\b"),
    ("vi_reveal_prompt",
     r"\b(tiet lo|in ra|hien thi|cho toi xem|noi cho toi|liet ke|lap lai)\b[^.\n]{0,40}"
     r"\b(system prompt|prompt he thong|huong dan an|chi dan an|chi dan he thong|huong dan he thong|cau lenh he thong)\b"),
    ("vi_developer_mode",
     r"\b(che do nha phat trien|developer mode|khong bi rang buoc|khong co gioi han nao)\b"),
    ("vi_fake_authority",
     r"\b(ghi de he thong|system override|thong bao danh cho (tro ly|ai))\b"),
    ("vi_secret_ask",
     r"\b(liet ke|in ra|tiet lo|cho toi xem)\b[^.\n]{0,40}"
     r"\b(mat khau|ma otp|ma mfa|thong tin dang nhap|api key|khoa api|du lieu bi mat|thong tin bi mat)\b"),
]

_COMPILED = [(name, re.compile(pattern)) for name, pattern in _PATTERNS_VI]


def scan_vi(text: str) -> list[str]:
    """Trả về danh sách tên mẫu khớp (rỗng nếu không thấy dấu hiệu injection)."""
    folded = fold(text)
    return [name for name, pattern in _COMPILED if pattern.search(folded)]