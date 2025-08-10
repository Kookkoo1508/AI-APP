import os, requests, json
from typing import Iterator, List, Dict, Union, TypedDict

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

def chat(model: str, message: str) -> str:
    r = requests.post(f"{OLLAMA_HOST}/api/chat", json={
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "stream": False
    }, timeout=120)
    r.raise_for_status()
    data = r.json()
    return data["message"]["content"]

def embed(model: str, text: str) -> list[float]:
    r = requests.post(f"{OLLAMA_HOST}/api/embeddings", json={
        "model": model, "prompt": text
    }, timeout=120)
    r.raise_for_status()
    return r.json().get("embedding", [])


# def stream_chat(model: str, message: str):
#     """
#     เรียก Ollama /api/chat แบบสตรีม แล้ว yield เฉพาะข้อความ (token/chunk) ทีละส่วน
#     ใช้ต่อกับ frontend เพื่อโชว์ผลแบบ real-time ได้ทันที

#     Usage:
#         # ตัวอย่างการใช้งาน
#         # for chunk in stream_chat("llama2", "สวัสดี"):
#         #     print(chunk, end="", flush=True)

#     Args:
#         model (str): ชื่อโมเดลของ Ollama ที่ต้องการใช้ (เช่น "llama2")
#         message (str): ข้อความที่ต้องการส่งไปให้โมเดล

#     Yields:
#         str: ส่วนของข้อความ (token/chunk) ที่ได้รับจาก Ollama API
#     """
    
#     url = f"{OLLAMA_HOST}/api/chat"
#     payload = {
#         "model": model,
#         "messages": [{"role": "user", "content": message}],
#         "stream": True,
#     }

#     try:
#         # ใช้ requests.post เพื่อส่งคำขอแบบสตรีม
#         with requests.post(url, json=payload, stream=True, timeout=None) as r:
#             r.raise_for_status() # ตรวจสอบสถานะการตอบกลับว่าสำเร็จหรือไม่ (2xx)

#             # อ่านข้อมูลที่ส่งกลับมาทีละบรรทัด
#             for line in r.iter_lines(decode_unicode=True):
#                 if not line:  # ข้ามบรรทัดว่าง
#                     continue

#                 try:
#                     obj = json.loads(line)

#                     chunk = ""
#                     # รูปแบบการตอบกลับมาตรฐานของ /api/chat (สตรีม)
#                     if isinstance(obj, dict):
#                         if "message" in obj and isinstance(obj["message"], dict):
#                             chunk = obj["message"].get("content", "")
#                         elif "response" in obj: # fallback สำหรับรูปแบบเก่า
#                             chunk = obj.get("response", "")

#                         if chunk:
#                             yield chunk

#                         # ตรวจสอบว่าสตรีมสิ้นสุดแล้ว
#                         if obj.get("done"):
#                             break

#                 except json.JSONDecodeError:
#                     # ถ้าบรรทัดไหนไม่ใช่ JSON ที่สมบูรณ์ ให้ข้ามไป
#                     continue

#     except requests.RequestException as e:
#         # จัดการข้อผิดพลาดที่เกี่ยวกับ network
#         yield f"[ERROR] {type(e).__name__}: {e}"


class ChatMessage(TypedDict):
    role: str   # 'system' | 'user' | 'assistant'
    content: str

def stream_chat(model: str, messages: Union[str, List[ChatMessage]]) -> Iterator[str]:
    """
    เรียก Ollama /api/chat แบบสตรีม
    - ถ้าให้เป็น str -> จะถูกแปลงเป็น [{"role":"user","content": str}]
    - ถ้าให้เป็น list[ChatMessage] -> ส่งเป็นบริบทหลาย turn ได้ทันที
    """
    if isinstance(messages, str):
        normalized: List[ChatMessage] = [{"role": "user", "content": messages}]
    else:
        normalized = messages

    url = f"{OLLAMA_HOST}/api/chat"
    payload = {"model": model, "messages": normalized, "stream": True}

    try:
        with requests.post(url, json=payload, stream=True, timeout=None) as r:
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
                    if "message" in obj and isinstance(obj["message"], dict):
                        chunk = obj["message"].get("content", "")
                    elif "response" in obj:  # fallback /api/generate style
                        chunk = obj.get("response", "")

                    if chunk:
                        yield chunk

                    if obj.get("done"):
                        break
    except requests.RequestException as e:
        yield f"[ERROR] {type(e).__name__}: {e}"