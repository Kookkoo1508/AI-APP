from __future__ import annotations
import os, re, uuid, unicodedata
from typing import Iterable, List, Dict, Any

from chromadb import PersistentClient
from pypdf import PdfReader
from docx import Document as Docx

from ..config import Config
from .ollama_client import embed as ollama_embed
from concurrent.futures import ThreadPoolExecutor, as_completed


# ---------- Sanitize ----------

_SURROGATE_RE = re.compile(r"[\uD800-\uDFFF]")  # ตัด surrogate ที่ผิดรูป
_NULL_RE = re.compile(r"\x00")                  # กัน null byte

def sanitize_text(s: str) -> str:
    if not s:
        return ""
    # ตัด null และ surrogate ออก
    s = _NULL_RE.sub("", s)
    s = _SURROGATE_RE.sub("", s)
    # จัดรูปแบบ unicode ให้ปกติ (เช่น สระ/วรรณยุกต์)
    try:
        s = unicodedata.normalize("NFC", s)
    except Exception:
        pass
    # เกลา white-space เล็กน้อย
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s+\n", "\n", s)
    return s.strip()

# ---------- Text loaders ----------

def load_text_from_file(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in [".txt", ".md"]:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return sanitize_text(f.read())
    if ext == ".docx":
        doc = Docx(path)
        paras = [sanitize_text(p.text or "") for p in doc.paragraphs]
        paras = [p for p in paras if p]
        return "\n\n".join(paras)
    raise ValueError(f"Unsupported extension: {ext}")

# ---------- Chunking (paragraph-aware) ----------

_parabreak = re.compile(r"\n{2,}")  # เว้นวรรค >=2 บรรทัด = ย่อหน้าใหม่
_whitespace = re.compile(r"\s+")

def _clean(s: str) -> str:
    return _whitespace.sub(" ", s).strip()

def _split_paragraphs(s: str) -> List[str]:
    parts = [p.strip() for p in _parabreak.split(s)]
    return [p for p in parts if p]

def chunk_text(s: str,
               max_chars: int | None = None,
               overlap: int | None = None) -> List[str]:
    """ตัดเป็นย่อหน้า แล้ว pack ให้ใกล้เคียง max_chars พร้อม overlap"""
    max_chars = max_chars or Config.RAG_CHUNK_CHARS
    overlap = overlap or Config.RAG_CHUNK_OVERLAP
    paras = [_clean(p) for p in _split_paragraphs(s)]
    chunks: List[str] = []
    buf = ""

    for p in paras:
        if not buf:
            buf = p
            continue
        if len(buf) + 2 + len(p) <= max_chars:
            buf = f"{buf}\n\n{p}"
        else:
            chunks.append(buf)
            # overlap ท้ายจาก buf มาเริ่มต้นชิ้นใหม่เพื่อคงความต่อเนื่อง
            if overlap > 0 and len(buf) > overlap:
                buf_tail = buf[-overlap:]
                buf = f"{buf_tail}\n\n{p}"
            else:
                buf = p
    if buf:
        chunks.append(buf)

    # กันชิ้นยักษ์: ตัดแบบ hard wrap ด้วยความยาว max_chars
    out: List[str] = []
    for c in chunks:
        if len(c) <= max_chars:
            out.append(c)
        else:
            i = 0
            step = max(max_chars - overlap, 1)
            while i < len(c):
                out.append(c[i:i+max_chars])
                i += step
    return [c for c in out if c.strip()]

# ---------- Chroma client ----------

def get_client():
    os.makedirs(Config.CHROMA_DIR, exist_ok=True)
    return PersistentClient(path=Config.CHROMA_DIR)

def get_collection(name: str = "kb_default"):
    client = get_client()
    return client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})

# ---- PDF loader (page-by-page) ----

def load_pdf_pages(path: str) -> list[tuple[int, str]]:
    reader = PdfReader(path)
    out = []
    for i, p in enumerate(reader.pages, start=1):  # 1-based
        txt = (p.extract_text() or "")
        txt = sanitize_text(txt)
        if txt:
            out.append((i, txt))
    return out

# ---- Embedding helper (safe for single-text embed API) ----

def embed_batch(texts: List[str]) -> List[List[float]]:
    """เรียก embed ทีละชิ้น, log ขนาดเวกเตอร์, กันเคสเวกเตอร์ว่าง"""
    vecs: List[List[float]] = []
    for idx, t in enumerate(texts, start=1):
        try:
            v = ollama_embed(Config.EMBEDDING_MODEL, t)
            if not isinstance(v, list) or not v:
                raise ValueError(f"empty/invalid embedding at chunk {idx}")
            vecs.append(v)
        except Exception as e:
            # log แล้วข้ามชิ้นนี้
            print(f"[RAG] embed error at chunk {idx}: {e}")
            # จะตัดชิ้นนี้ออกโดยไม่ push vecs/docs/ids ให้ขนาดตรงกัน
            vecs.append(None)  # ใส่ placeholder ไว้ก่อน เดี๋ยวกรองทิ้งตอน pack
    return vecs


# ---------- Ingest ----------

def _embed_batch_or_single(texts: List[str]) -> List[List[float] | None]:
    """
    เรียก ollama_embed แบบ batch (รายการข้อความ) ตามสัญญาเดิมของคุณ:
      embed(model, texts: List[str]) -> List[List[float]]
    ถ้าในระบบปัจจุบัน embed คืนเวกเตอร์เดี่ยว (list[float]) ก็ fallback ให้
    """
    if not texts:
        return []

    try:
        vecs = ollama_embed(Config.EMBEDDING_MODEL, texts)  # ✅ คาดหวังคืนรายการเวกเตอร์
        # ปกติควรเป็น list[list[float]] ขนาดเท่ากับ texts
        if isinstance(vecs, list) and len(vecs) == len(texts) and isinstance(vecs[0], list):
            return vecs
        # Fallback: embed อาจคืนเวกเตอร์เดี่ยวเมื่อส่งสตริง → ลองทีละชิ้น (ช้า แต่ไม่ค้าง)
        out: List[List[float] | None] = []
        for t in texts:
            try:
                v = ollama_embed(Config.EMBEDDING_MODEL, t)
                out.append(v if isinstance(v, list) and v else None)
            except Exception as e:
                print(f"[RAG] embed(single) error: {e}")
                out.append(None)
        return out
    except Exception as e:
        print(f"[RAG] embed(batch) error: {e} — falling back to single mode")
        out: List[List[float] | None] = []
        for t in texts:
            try:
                v = ollama_embed(Config.EMBEDDING_MODEL, t)
                out.append(v if isinstance(v, list) and v else None)
            except Exception as e2:
                print(f"[RAG] embed(single) error: {e2}")
                out.append(None)
        return out


def ingest_file(file_path: str, metadata: dict | None = None) -> dict:
    ext = os.path.splitext(file_path)[1].lower()
    base = os.path.basename(file_path)
    metabase = metadata or {}

    abs_dir = os.path.abspath(Config.CHROMA_DIR)
    os.makedirs(abs_dir, exist_ok=True)
    if not os.access(abs_dir, os.W_OK):
        raise RuntimeError(f"CHROMA_DIR not writable: {abs_dir}")

    col = get_collection()

    BATCH = int(getattr(Config, "RAG_EMBED_BATCH", 64))   # ✅ ก้อนใหญ่ขึ้นเล็กน้อย
    MIN_CHARS = int(getattr(Config, "RAG_MIN_CHARS", 1))

    # queue
    q_texts: List[str] = []
    q_metas: List[dict] = []

    def queue(text: str, meta: dict):
        text = sanitize_text(text)
        if not text or len(text) < MIN_CHARS:
            return
        q_texts.append(text)
        q_metas.append(meta)

    # เตรียมคิวจากไฟล์
    if ext == ".pdf":
        pages = load_pdf_pages(file_path)
        print(f"[RAG] ingest PDF: {base}, pages with text: {len(pages)}")
        for page_no, page_text in pages:
            chunks = [c for c in chunk_text(page_text) if c.strip()]
            try:
                page_offset = int(metabase.get("page_offset", 0) or 0)
            except Exception:
                page_offset = 0
            meta = {
                "source": base,
                "title": os.path.splitext(base)[0],
                "ext": "pdf",
                "page": page_no,
                "p": page_no,
                "page_display": page_no + page_offset,
                **{k: v for k, v in metabase.items() if k != "page_offset"},
            }
            for c in chunks:
                queue(c, meta)
    else:
        text = load_text_from_file(file_path)
        chunks = [c for c in chunk_text(text) if c.strip()]
        print(f"[RAG] ingest TEXT: {base}, chunks: {len(chunks)}")
        meta = {
            "source": base,
            "title": os.path.splitext(base)[0],
            "ext": ext.lstrip("."),
            **metabase
        }
        for c in chunks:
            queue(c, meta)

    total_added = 0
    total_queued = len(q_texts)

    # ทำงานเป็นก้อน
    for i in range(0, total_queued, BATCH):
        texts = q_texts[i:i+BATCH]
        metas = q_metas[i:i+BATCH]
        print(f"[RAG] embedding batch {i//BATCH + 1} — size {len(texts)}")

        vecs = _embed_batch_or_single(texts)

        ids, docs, embs, out_metas = [], [], [], []
        for t, m, v in zip(texts, metas, vecs):
            if v is None:
                continue
            ids.append(str(uuid.uuid4()))
            docs.append(t)
            embs.append(v)
            out_metas.append(m)

        if not ids:
            print("[RAG] skip empty batch (all embeds failed)")
            continue

        try:
            col.add(ids=ids, documents=docs, embeddings=embs, metadatas=out_metas)
        except UnicodeEncodeError:
            docs2 = [_SURROGATE_RE.sub("", d).replace("\x00", "") for d in docs]
            col.add(ids=ids, documents=docs2, embeddings=embs, metadatas=out_metas)

        total_added += len(ids)
        print(f"[RAG] added {len(ids)} chunks (total {total_added}/{total_queued})")

    print(f"[RAG] DONE -> added {total_added} chunks to {abs_dir}")
    return {"file": base, "chunks": total_added}


# ---------- Search (with threshold + context control) ----------

# ---- helper: normalize embedding vector ----
def _normalize_vec(v):
    # v = [f1, f2, ...] -> ok
    if isinstance(v, list) and v and isinstance(v[0], (float, int)):
        return v
    # v = [[f1, f2, ...]] -> เอาอันแรก
    if isinstance(v, list) and v and isinstance(v[0], list):
        return v[0]
    # numpy array / อื่นๆ
    try:
        import numpy as np
        if isinstance(v, np.ndarray):
            if v.ndim == 1:
                return v.tolist()
            if v.ndim == 2:
                return v[0].tolist()
    except Exception:
        pass
    raise ValueError(f"[RAG] cannot normalize embedding shape: {type(v)}")


def search(query: str, k: int | None = None) -> List[Dict[str, Any]]:
    """คืนผลลัพธ์ที่ใกล้พอด้วย adaptive threshold; ถ้าเคร่งเกินจนว่าง ให้ fallback เป็น top-k"""
    query = sanitize_text(query)
    k = k or Config.RAG_TOPK_DEFAULT

    qvec_raw = ollama_embed(Config.EMBEDDING_MODEL, query)
    qvec = _normalize_vec(qvec_raw)

    col = get_collection()
    # ดึงเยอะกว่าที่ต้องใช้ เพื่อประเมิน distribution ได้
    n_pull = max(k * 4, 40)
    res = col.query(
        query_embeddings=[qvec],
        n_results=n_pull,
        include=["documents", "metadatas", "distances"],
    )

    distances = res.get("distances", [[]])[0] or []
    documents = res.get("documents", [[]])[0] or []
    metadatas = res.get("metadatas", [[]])[0] or []

    # แพ็ก + กรอง none
    items = []
    for d, doc, md in zip(distances, documents, metadatas):
        if d is None or not doc:
            continue
        items.append((float(d), doc, dict(md or {})))

    if not items:
        return []

    # เรียงจากใกล้สุด → ไกลสุด (สำหรับ cosine/L2 ใช้ระยะน้อยดีกว่า)
    items.sort(key=lambda x: x[0])

    # -------- Adaptive cutoff ----------
    ds = [d for d, _, _ in items]
    # เพอร์เซ็นไทล์ 85 สำหรับตัดหาง และคุมเพดานเบา ๆ เผื่อคอลเลกชันใช้ space ต่างกัน
    import math
    def pct(arr, p):
        i = max(0, min(len(arr)-1, int(math.ceil(p * len(arr)) - 1)))
        return sorted(arr)[i]

    p85 = pct(ds, 0.85)

    # ถ้าเคยตั้ง Config.RAG_MAX_DISTANCE ให้ใช้ min ระหว่าง p85 กับค่านั้น; ถ้าไม่ได้ตั้งให้ใช้ p85 ไปเลย
    hard = getattr(Config, "RAG_MAX_DISTANCE", None)
    cutoff = min(p85, hard) if isinstance(hard, (int, float)) and hard > 0 else p85

    # กรองตาม cutoff
    filtered = [(d, doc, md) for (d, doc, md) in items if d <= cutoff]

    # ถ้ากรองแล้วน้อย/ว่าง → fallback: ใช้ top-k ตรง ๆ
    chosen = filtered if len(filtered) >= max(1, k) else items[:max(1, k)]

    # -------- Trim per-doc & whole-context ----------
    max_per = getattr(Config, "RAG_MAX_DOC_CHARS", 1200)
    max_all = getattr(Config, "RAG_MAX_CONTEXT_CHARS", 4000)

    hits: List[Dict[str, Any]] = []
    total = 0
    for d, doc, md in chosen:
        snippet = (doc or "")[:max_per]
        if total + len(snippet) > max_all:
            break
        hits.append({
            "document": snippet,
            "metadata": md,
            "distance": d,
        })
        total += len(snippet)

    # ตัดเหลือ k ชิ้น
    return hits[:k]


# ---------- Compose augmented messages ----------

def _short_name(name: str, max_chars: int = 40) -> str:
    """ย่อชื่อไฟล์ให้ไม่ยาวเกินไป โดยคงส่วนท้าย (นามสกุล) ไว้"""
    base = os.path.basename(name or "document")
    if len(base) <= max_chars:
        return base
    head = max_chars - 1 - 15  # เว้นที่สำหรับ … และท้าย 15 ตัว
    if head < 10:
        head = max(10, max_chars // 2 - 1)
    return f"{base[:head]}…{base[-15:]}"

def _display_page(md: dict) -> int | None:
    """คำนวณเลขหน้าที่จะแสดง (รองรับ page, p, page_offset)"""
    page = md.get("page")
    if page is None:
        page = md.get("p")
    if page is None:
        return None
    try:
        page = int(page)
    except Exception:
        return None
    offset = 0
    try:
        offset = int(md.get("page_offset", 0) or 0)
    except Exception:
        offset = 0
    return page + offset

def build_augmented_messages(user_message: str, topk: int | None = None) -> tuple[list[dict], list[str]]:
    """สร้าง messages + คืน sources เพื่อเอาไปแสดง citation ได้"""
    topk = topk or Config.RAG_TOPK_DEFAULT
    hits = search(user_message, k=topk)

    # ถ้าไม่มีชิ้นไหน 'ใกล้พอ' ให้บอกผู้ใช้ตรงๆ
    if not hits:
        system_prompt = (
            "คุณคือผู้ช่วยที่ตอบจากคลังความรู้เท่านั้น แต่ตอนนี้ไม่พบชิ้นข้อมูลที่เกี่ยวข้องมากพอ "
            "ตอบว่า 'ไม่พบข้อมูลในคลังความรู้ — โปรดลองอัปโหลดเอกสารเพิ่มเติม' โดยไม่เดา"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"คำถาม:\n{user_message}"},
        ]
        return messages, []

    context_blocks: List[str] = []
    sources: list[str] = []
    for i, h in enumerate(hits):
        md = h["metadata"] or {}
        src = md.get("source") or md.get("file") or "document"
        page_disp = _display_page(md)
        section = md.get("section")

        # ทำให้เลขหน้าอยู่ด้านหน้าเพื่อไม่ถูกชื่อไฟล์ยาวบัง
        short_src = _short_name(src)
        if page_disp is not None:
            tag = f"p.{page_disp} • {short_src}"
        elif section:
            tag = f"§{section} • {short_src}"
        else:
            tag = short_src

        sources.append(tag)
        context_blocks.append(f"[DOC {i+1} • {tag}]\n{h['document']}")

    context = "\n\n".join(context_blocks)

    system_prompt = (
        "คุณคือผู้ช่วยที่ตอบจาก 'บริบทความรู้' ที่ให้เท่านั้น "
        "ห้ามเดาคำตอบนอกเหนือจากบริบท หากไม่พอ ให้บอกว่าไม่พบข้อมูลในคลังความรู้ "
        "ให้ตอบไทย กระชับ และอ้างอิงชื่อไฟล์ที่ใช้ประกอบคำตอบ"
    )
    user_prompt = f"บริบทความรู้:\n{context}\n\nคำถาม:\n{user_message}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # ลบซ้ำ: รักษาลำดับไว้
    dedup_sources = list(dict.fromkeys(sources))
    return messages, dedup_sources
