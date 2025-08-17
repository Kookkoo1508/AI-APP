import os, requests, json
from typing import Iterator, List, Dict, Union, TypedDict
from flask import jsonify

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

def model_available(name: str) -> bool:
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        r.raise_for_status()
        data = r.json() or {}
        models = [m.get("name") for m in data.get("models", []) if isinstance(m, dict)]
        
        return any(m == name or m.startswith(f"{name}:") for m in models)
        # print(f"Available models: {names}")  # Debugging line
    except Exception:
        return False
    
def list_models():
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        r.raise_for_status()
        # print(f"Response from {OLLAMA_HOST}/api/tags: {r.text}")  # Debugging line
        data = r.json() or {}

        models = []
        for m in data.get("models", []):
            if isinstance(m, dict) and "name" in m:
                # เอาชื่อมาแล้ว split ที่ ":" เอาเฉพาะซ้ายสุด
                clean_name = m["name"].split(":")[0]
                models.append(clean_name)

        return jsonify({"models": models})
    except Exception:
        return jsonify({"models": []}), 500

def chat(model: str, message: str) -> str:
    r = requests.post(f"{OLLAMA_HOST}/api/chat", json={
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "stream": False
    }, timeout=120)
    r.raise_for_status()
    data = r.json()
    return data["message"]["content"]

def embed(model: str, texts: list[str]) -> list[list[float]]:
    """Batch embedding ด้วย Ollama /api/embeddings (ทีละชิ้นก็ได้)"""
    out: list[list[float]] = []
    for t in texts:
        r = requests.post(f"{OLLAMA_HOST}/api/embeddings", json={
            "model": model,
            "prompt": t,
        }, timeout=120)
        if r.status_code >= 400:
            # เติมข้อความแนะนำให้ชัด
            detail = r.text.strip()
            raise RuntimeError(
                f"Embeddings request failed ({r.status_code}) for model '{model}'. "
                f"Check OLLAMA_HOST={OLLAMA_HOST} and ensure model is pulled: `ollama pull {model}`. "
                f"Response: {detail[:300]}"
            )
        data = r.json()
        out.append(data.get("embedding", []))
    return out

class ChatMessage(TypedDict):
    role: str   # 'system' | 'user' | 'assistant'
    content: str

def _join_prompt(messages: list[dict]) -> str:
    parts = []
    for m in messages:
        role = m.get("role", "user").upper()
        content = m.get("content", "")
        parts.append(f"{role}:\n{content}\n")
    parts.append("ASSISTANT:\n")
    return "\n".join(parts)

def stream_chat(model: str, messages: Union[str, List[ChatMessage]]) -> Iterator[str]:
    """พยายามใช้ /api/chat; ถ้า 404 ให้ fallback ไป /api/generate"""
    if isinstance(messages, str):
        normalized: List[ChatMessage] = [{"role": "user", "content": messages}]
    else:
        normalized = messages

    # ---------- ทางหลัก: /api/chat ----------
    chat_url = f"{OLLAMA_HOST}/api/chat"
    payload = {"model": model, "messages": normalized, "stream": True}
    try:
        with requests.post(chat_url, json=payload, stream=True, timeout=None) as r:
            if r.status_code == 404:
                raise FileNotFoundError("ollama /api/chat not found")
            r.raise_for_status()
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                chunk = ""
                if isinstance(obj, dict):
                    # chat รูปแบบใหม่
                    if "message" in obj and isinstance(obj["message"], dict):
                        chunk = obj["message"].get("content", "")
                    # เผื่อบางเวอร์ชันส่ง field response มา
                    elif "response" in obj:
                        chunk = obj.get("response", "")

                if chunk:
                    yield chunk

                if isinstance(obj, dict) and obj.get("done"):
                    break
            return
    except FileNotFoundError:
        # ตกไปใช้ generate
        pass
    except requests.HTTPError as e:
        # ถ้าไม่ใช่ 404 ให้โยนต่อให้ route จัดการ
        if getattr(e.response, "status_code", None) != 404:
            raise

    # ---------- Fallback: /api/generate ----------
    gen_url = f"{OLLAMA_HOST}/api/generate"
    prompt = _join_prompt(normalized)
    with requests.post(gen_url, json={"model": model, "prompt": prompt, "stream": True}, stream=True, timeout=None) as r:
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            delta = ""
            # รูปแบบ generate เดิม
            if isinstance(obj, dict):
                delta = obj.get("response", "")
            if delta:
                yield delta

            if isinstance(obj, dict) and obj.get("done"):
                break