"""
Chạy thử:  uvicorn api:app --reload --port 8000
Triển khai: uvicorn api:app --host 0.0.0.0 --port $PORT
"""
from __future__ import annotations

import os
import re
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from guarded_rag.config import Settings
from guarded_rag.graph import answer
from guarded_rag.guards.pii import mask
from guarded_rag.kb import load_kb
from guarded_rag.llm import OpenAICompatLLM, ScriptedLLM

settings = Settings()
kb = load_kb(settings.kb_dir)  # nạp 1 lần lúc khởi động

OFFLINE = os.getenv("GRAG_OFFLINE") == "1"                 # =1 để test không cần model
ORIGINS = [
    o.strip().rstrip("/")
    for o in os.getenv(
        "ALLOWED_ORIGINS",
        "https://opphunter.netlify.app"
    ).split(",")
    if o.strip()
]
PER_MIN = int(os.getenv("RATE_PER_MIN", "6"))              # số câu hỏi / phút / người dùng
DAILY_CAP = int(os.getenv("DAILY_CAP", "300"))             # tổng số câu hỏi / ngày (bảo vệ quota API key)
MAX_LEN = 500                                              # độ dài tối đa của câu hỏi

LINK: dict[str, str] = {}
for c in kb.chunks:
    doc = c.id.split("#")[0]
    m = re.search(r"Official page:\s*(https?://\S+?)\.?(?:\s|$)", c.text)
    if m and doc not in LINK:
        LINK[doc] = m.group(1)

app = FastAPI(title="OppHunter API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_hits: dict[str, deque] = defaultdict(deque)
_day = {"d": "", "n": 0}


def _check_rate(ip: str) -> None:
    now = time.time()
    q = _hits[ip]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= PER_MIN:
        raise HTTPException(429, "rate limit")
    today = time.strftime("%Y-%m-%d")
    if _day["d"] != today:
        _day["d"], _day["n"] = today, 0
    if _day["n"] >= DAILY_CAP:
        raise HTTPException(429, "daily cap")
    q.append(now)
    _day["n"] += 1


class Req(BaseModel):
    message: str
    lang: str = "vi"
    history: list = []


@app.get("/")
def health():
    return {"ok": True, "chunks": len(kb.chunks), "offline": OFFLINE}


@app.post("/chat")
def chat(r: Req, request: Request):
    msg = r.message.strip()
    if not msg:
        raise HTTPException(400, "empty message")
    if len(msg) > MAX_LEN:
        raise HTTPException(400, "message too long")
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "?")
    _check_rate(ip)

    llm = ScriptedLLM() if OFFLINE else OpenAICompatLLM(settings.llm_base_url, settings.llm_model, settings.llm_api_key)
    try:
        res = answer(msg, llm, kb, settings, use_llm_judge=not OFFLINE, lang=r.lang)
    except Exception as e:  # lỗi gọi model, hết quota...
        raise HTTPException(502, f"model error: {type(e).__name__}")

    sources, seen = [], set()
    for cid in res.citations:
        doc = cid.split("#")[0]
        if doc in seen:
            continue
        seen.add(doc)
        sources.append({"id": doc, "title": doc.replace("-", " ").title(), "link": LINK.get(doc)})
    masked_q, _ = mask(msg)
    return {"answer": res.answer, "status": res.status, "sources": sources, "masked_question": masked_q}