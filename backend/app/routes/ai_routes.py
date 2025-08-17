from flask import Blueprint, request, jsonify, Response, stream_with_context
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.ollama_client import chat, embed
from ..services import rag
from app.models.conversation import Conversation, Message   # <<— import ตรงจากไฟล์โมดูล
from sqlalchemy import desc, asc
from app.extensions import db
from app.services.ollama_client import stream_chat as _ollama_stream
from flask import current_app
import base64, json, unicodedata, re
from ..services.ollama_client import model_available, list_models
from  ..utils.json import json_error

ai_bp = Blueprint("ai", __name__)

_ASCII_SAFE = re.compile(r"[^ -~]")  # printable ASCII 0x20-0x7E

def _sources_headers(sources: list[str]) -> tuple[str, str]:
    # header ASCII fallback เช่น "p.35 • file.pdf | p.249 • file.pdf"
    ascii_items = []
    for s in sources or []:
        t = _ASCII_SAFE.sub("?", s)  # แทนตัว non-ascii ด้วย ?
        ascii_items.append(t)
    ascii_join = " | ".join(ascii_items)

    # header B64: เก็บ JSON UTF‑8 เต็ม ๆ
    b64_json = base64.b64encode(json.dumps(sources, ensure_ascii=False).encode("utf-8")).decode("ascii")
    return ascii_join, b64_json


@ai_bp.post("/chat")
@jwt_required(optional=True)  # จะบังคับก็เปลี่ยนเป็น @jwt_required()
def ai_chat():
    data = request.get_json() or {}
    message = (data.get("message") or "").strip()
    model = data.get("model", "llama3.1")
    if not message:
        return jsonify({"message": "message is required"}), 400
    reply = chat(model=model, message=message)
    return jsonify({"reply": reply})

@ai_bp.post("/embeddings")
@jwt_required(optional=True)
def ai_embeddings():
    data = request.get_json() or {}
    text = (data.get("text") or "").strip()
    model = data.get("model", "nomic-embed-text")
    if not text:
        return jsonify({"message": "text is required"}), 400
    vec = embed(model=model, text=text)
    return jsonify({"embedding": vec})

def _ascii_safelists(items):
    out = []
    for s in items or []:
        if not isinstance(s, str):
            s = str(s)
        # Normalize แล้วกรองให้เหลือ ASCII printable เท่านั้น
        s_norm = unicodedata.normalize("NFKD", s)
        s_ascii = s_norm.encode("ascii", "ignore").decode("ascii")
        s_ascii = re.sub(r"[^ -~]", "", s_ascii)  # printable ASCII
        out.append(s_ascii)
    return out

@ai_bp.post("/chat/stream")
@jwt_required(optional=True)
def chat_stream():
    data = request.get_json(force=True) or {}
    model = data.get("model", "llama3.1")
    user_message = (data.get("message") or "").strip()
    conversation_id = data.get("conversation_id")
    use_knowledge = bool(data.get("use_knowledge", False))
    topk = int(data.get("topk", 5))

    # เช็คว่ามีโมเดลจริงหรือไม่
    if not model_available(model):
        return json_error(
            f"ไม่พบโมเดล '{model}' บน Ollama — โปรดเลือกโมเดลที่ใช้งานได้ (ดูรายการที่ /api/ai/models)",
            400,
            code="MODEL_NOT_FOUND"
        )

    if not user_message:
        return jsonify({"error": "message is required"}), 400

    # --- auth (คงพฤติกรรมเดิมของคุณ) ---
    identity = get_jwt_identity()
    try:
        uid = int(identity)
    except (TypeError, ValueError):
        current_app.logger.error("Invalid JWT identity: %r", identity)
        return jsonify({"error": "invalid identity"}), 401

    # --- หา/สร้างบทสนทนาของผู้ใช้นี้ ---
    conv = None
    if conversation_id:
        conv = (
            Conversation.query
            .filter_by(id=conversation_id, user_id=uid)
            .first()
        )
        if not conv:
            return jsonify({"error": "conversation not found"}), 404

    if not conv:
        conv = Conversation(
            user_id=uid,
            title=(user_message[:80] + "…") if len(user_message) > 80 else user_message
        )
        db.session.add(conv)
        db.session.commit()

    # --- ประวัติ N ข้อความล่าสุด (ไม่เก็บ/ไม่ใส่ system ใน DB) ---
    N = 20
    history = (
        Message.query
        .filter_by(conversation_id=conv.id)
        .order_by(asc(Message.created_at))
        .limit(N)
        .all()
    )
    history_msgs = [{"role": m.role, "content": m.content} for m in history]

    # --- บันทึก user message ลง DB ก่อนเรียกโมเดล ---
    db.session.add(Message(conversation_id=conv.id, role="user", content=user_message))
    db.session.commit()

    # --- เตรียม messages สำหรับโมเดล (RAG-aware) ---
    sources: list[str] = []
    rag_error: str | None = None
    msgs: list[dict]

    if use_knowledge:
        try:
            # ใช้ตัว build รุ่นใหม่ (มี threshold/trim)
            from ..services.rag import build_augmented_messages
            msgs_rag, sources = build_augmented_messages(user_message, topk=topk)
            # รวม history เข้าระหว่าง system กับ user ของ msgs_rag
            # msgs_rag = [system_msg, augmented_user]
            if history_msgs:
                msgs = [msgs_rag[0], *history_msgs, msgs_rag[1]]
            else:
                msgs = msgs_rag
        except Exception as e:
            current_app.logger.exception("RAG build/search failed")
            rag_error = str(e)
            # fallback → โหมดปกติ
            use_knowledge = False
            msgs = history_msgs + [{"role": "user", "content": user_message}]
    else:
        msgs = history_msgs + [{"role": "user", "content": user_message}]

    # --- สตรีมผลลัพธ์จากโมเดล ---
    def generate():
        had_output = False
        buffer = []
        try:
            for chunk in _ollama_stream(model, msgs):
                buffer.append(chunk)
                had_output = True
                yield chunk
        except Exception as e:
            current_app.logger.exception("Ollama stream failed")
            yield "\n(เกิดข้อขัดข้องระหว่างเชื่อมต่อโมเดล — โปรดลองอีกครั้ง)\n"
            return

        # เซฟ assistant หลังสตรีมจบ
        if had_output:
            text = "".join(buffer).strip()
            if text:
                db.session.add(Message(conversation_id=conv.id, role="assistant", content=text))
                db.session.commit()
        else:
            yield "\n"

    # --- headers สำหรับ FE ---
    headers = {
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
        "X-Conversation-Id": str(conv.id),
        "Access-Control-Expose-Headers": "X-Conversation-Id, X-Knowledge-Sources, X-Knowledge-Sources-B64, X-RAG-Error",
    }
    if use_knowledge and sources:
        ascii_join, b64_json = _sources_headers(sources)
        headers["X-Knowledge-Sources"] = ascii_join                    # ASCII-only (fallback)
        headers["X-Knowledge-Sources-B64"] = b64_json                  # UTF-8 JSON (แนะนำให้ FE ใช้)

    if rag_error:
        headers["X-RAG-Error"] = (rag_error[:200]).replace("\n", " ")

    return Response(
        stream_with_context(generate()),
        mimetype="text/plain; charset=utf-8",
        headers=headers,
    )


@ai_bp.get("/conversations")
@jwt_required()  #  ต้องล็อกอิน
def list_conversations():

    uid = int(get_jwt_identity())
    rows = (
        Conversation.query
        .filter_by(user_id=uid)             # ✅ เฉพาะของผู้ใช้นี้
        .order_by(desc(Conversation.created_at))
        .all()
    )
    out = []
    for c in rows:
        last = (
            Message.query
            .filter_by(conversation_id=c.id)
            .order_by(desc(Message.created_at))
            .first()
        )
        out.append({
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at.isoformat(),
            "last_preview": (last.content[:120] + "…") if last else "",
        })
    return jsonify({"items": out})

@ai_bp.get("/messages")
@jwt_required() 
def list_messages():
    conv_id = request.args.get("conversation_id", type=int)
    if not conv_id:
        return jsonify({"error": "conversation_id is required"}), 400
    
    uid = int(get_jwt_identity())
    conv = Conversation.query.filter_by(id=conv_id, user_id=uid).first()
    
    if not conv:
        return jsonify({"error": "conversation not found"}), 404
    msgs = (
        Message.query
        .filter_by(conversation_id=conv_id)
        .order_by(asc(Message.created_at))
        .all()
    )
    return jsonify({
        "items": [
            {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
            for m in msgs
        ]
    })

@ai_bp.route("/conversations/<int:conv_id>", methods=["PUT", "PATCH"])
@jwt_required()
def rename_conversation(conv_id: int):
    uid = int(get_jwt_identity())
    title = (request.get_json() or {}).get("title", "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    conv = Conversation.query.filter_by(id=conv_id, user_id=uid).first()
    if not conv:
        return jsonify({"error": "conversation not found"}), 404

    conv.title = title
    db.session.commit()
    return jsonify({"ok": True})

@ai_bp.delete("/conversations/<int:conv_id>")
@jwt_required()
def delete_conversation(conv_id: int):
    uid = int(get_jwt_identity())
    conv = Conversation.query.filter_by(id=conv_id, user_id=uid).first()
    if not conv:
        return jsonify({"error": "conversation not found"}), 404

    db.session.delete(conv)
    db.session.commit()
    return jsonify({"ok": True})

@ai_bp.get("/models")
def models():
    resp = list_models()
    if resp is False:
        return jsonify({"error": "ไม่สามารถดึงรายการโมเดลได้"}), 500
    return resp
