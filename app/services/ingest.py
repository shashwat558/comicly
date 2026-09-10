import io
import re

import tiktoken
from bs4 import BeautifulSoup
from ebooklib import epub
from pypdf import PdfReader

enc = tiktoken.get_encoding("cl100k_base")

TARGET_TOKENS = 900
MAX_TOKENS = 1200


def _clean(text: str) -> str:
    text = re.sub(r"\r", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def extract_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue
    return _clean("\n\n".join(parts))


def extract_epub(data: bytes) -> str:
    book = epub.read_epub(io.BytesIO(data))
    parts: list[str] = []
    for item in book.get_items():
        if item.get_type() == 9:
            soup = BeautifulSoup(item.get_content(), "lxml")
            for tag in soup(["script", "style"]):
                tag.decompose()
            parts.append(soup.get_text(separator="\n"))
    return _clean("\n\n".join(parts))


def chunk_text(text: str, target: int = TARGET_TOKENS, hard_max: int = MAX_TOKENS) -> list[str]:
    # split on blank lines so chunks never cut mid-paragraph
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    cur: list[str] = []
    cur_tokens = 0
    for p in paras:
        toks = len(enc.encode(p))
        if toks > hard_max:

            sents = re.split(r"(?<=[.!?])\s+", p)
            for s in sents:
                st = len(enc.encode(s))
                if cur_tokens + st > hard_max and cur:
                    chunks.append("\n\n".join(cur))
                    cur, cur_tokens = [], 0
                cur.append(s)
                cur_tokens += st
            continue
        if cur_tokens + toks > target and cur:
            chunks.append("\n\n".join(cur))
            cur, cur_tokens = [], 0
        cur.append(p)
        cur_tokens += toks
    if cur:
        chunks.append("\n\n".join(cur))
    return [c for c in chunks if c.strip()]


def parse_book(filename: str, content_type: str, data: bytes) -> tuple[str, list[str]]:
    name = (filename or "").lower()
    ctype = (content_type or "").lower()
    if name.endswith(".pdf") or "pdf" in ctype:
        text = extract_pdf(data)
        kind = "pdf"
    elif name.endswith(".epub") or "epub" in ctype or "oebps" in ctype:
        text = extract_epub(data)
        kind = "epub"
    elif name.endswith(".txt") or "text/plain" in ctype:
        text = _clean(data.decode("utf-8", errors="ignore"))
        kind = "txt"
    else:
        raise ValueError(f"Unsupported file type: {filename} ({content_type})")
    if not text or len(text.strip()) < 50:
        raise ValueError("No readable text extracted - empty or scanned PDF?")
    return kind, chunk_text(text)
