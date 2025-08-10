from flask import Blueprint, request, jsonify, Response, stream_with_context
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.ollama_client import chat, embed, stream_chat
from app.models.conversation import Conversation, Message   # <<— import ตรงจากไฟล์โมดูล
from sqlalchemy import desc, asc
from app.extensions import db
from app.services.ollama_client import stream_chat as _ollama_stream
from flask import current_app

ai_bp = Blueprint("ai", __name__)

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

@ai_bp.post("/chat/stream")
@jwt_required(optional=True) 
def chat_stream():
    data = request.get_json(force=True) or {}
    model = data.get("model", "llama3.1")
    user_message = (data.get("message") or "").strip()
    conversation_id = data.get("conversation_id")

    if not user_message:
        return jsonify({"error": "message is required"}), 400

    identity = get_jwt_identity()
    
    try:
        uid = int(identity)
    except (TypeError, ValueError):
        current_app.logger.error("Invalid JWT identity: %r", identity)
        return jsonify({"error": "invalid identity"}), 401

    # หา/สร้างบทสนทนาของ "ผู้ใช้นี้เท่านั้น"
    conv = None
    if conversation_id:
        conv = (
            Conversation.query
            .filter_by(id=conversation_id, user_id=uid)
            .first()
        )
        if not conv:
            # ไม่ให้รู้ว่ามีของคนอื่น -> ตอบเหมือนไม่มี
            return jsonify({"error": "conversation not found"}), 404

    if not conv:
        conv = Conversation(
            user_id=uid,
            title=(user_message[:80] + "…") if len(user_message) > 80 else user_message
        )
        db.session.add(conv)
        db.session.commit()

    # ดึงประวัติ N ข้อความล่าสุด
    N = 20
    history = (
        Message.query
        .filter_by(conversation_id=conv.id)
        .order_by(asc(Message.created_at))
        .limit(N)
        .all()
    )

    # บันทึก user message ก่อนเรียกโมเดล
    db.session.add(Message(conversation_id=conv.id, role="user", content=user_message))
    db.session.commit()

    # เตรียม messages สำหรับโมเดล
    msgs = [{"role": m.role, "content": m.content} for m in history]
    msgs.append({"role": "user", "content": user_message})

    def generate():
        had_output = False
        buffer = []
        try:
            for chunk in _ollama_stream(model, msgs):
                buffer.append(chunk)
                had_output = True
                yield chunk
        except Exception as e:
            yield f"\n[ERROR] {type(e).__name__}: {e}\n"
            return

        # เซฟ assistant หลังสตรีมจบ
        if had_output:
            text = "".join(buffer).strip()
            if text:
                db.session.add(Message(conversation_id=conv.id, role="assistant", content=text))
                db.session.commit()
        else:
            yield "\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "X-Conversation-Id": str(conv.id),
        },
    )

@ai_bp.get("/conversations")
@jwt_required()  # ✅ ต้องล็อกอิน
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

@ai_bp.patch("/conversations/<int:conv_id>")
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