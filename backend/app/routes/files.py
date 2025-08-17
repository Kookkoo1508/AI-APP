from __future__ import annotations
import os
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from ..config import Config
from ..services import rag
from ..schemas.files import SearchRequest

import logging
from datetime import datetime

bp = Blueprint("files", __name__, url_prefix="/api/files")

logger = logging.getLogger(__name__)

def allowed(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower()
    return ext in Config.ALLOWED_EXTS


# @bp.post("/upload")
# def upload():
#     if "file" not in request.files:
#         return jsonify({"error": "no file"}), 400
#     f = request.files["file"]
#     if f.filename == "":
#         return jsonify({"error": "empty filename"}), 400
#     if not allowed(f.filename):
#         return jsonify({"error": f"extension not allowed: {f.filename}"}), 400

#     os.makedirs(Config.UPLOAD_DIR, exist_ok=True)
#     save_path = os.path.join(Config.UPLOAD_DIR, secure_filename(f.filename))
#     f.save(save_path)

#     result = rag.ingest_file(save_path, metadata={"filename": f.filename})
#     return jsonify(result)
def to_serializable(obj):
    """แปลงค่าที่ jsonify ไม่รู้จัก ให้กลายเป็นชนิดพื้นฐานของ JSON"""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_serializable(v) for v in obj]
    # datetime
    if isinstance(obj, datetime):
        return obj.isoformat()
    # numpy scalar
    try:
        import numpy as _np  # กันกรณีไม่มี numpy
        if isinstance(obj, (_np.integer,)):
            return int(obj)
        if isinstance(obj, (_np.floating,)):
            return float(obj)
        if isinstance(obj, (_np.ndarray,)):
            return obj.tolist()
    except Exception:
        pass
    # object อื่น ๆ แปลงเป็น string ทิ้งท้าย (กันตาย)
    return str(obj)

@bp.post("/upload")
def upload():
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "empty filename"}), 400
    if not allowed(f.filename):
        return jsonify({"error": f"extension not allowed: {f.filename}"}), 400

    os.makedirs(Config.UPLOAD_DIR, exist_ok=True)
    stored_name = secure_filename(f.filename)
    save_path = os.path.join(Config.UPLOAD_DIR, stored_name)
    f.save(save_path)

    try:
        #  ขอให้ ingest_file คืน summary ที่เป็น primitive เท่านั้น
        result = rag.ingest_file(save_path, metadata={
            "filename": f.filename,
            "stored_name": stored_name,
        })
        # กันเคสที่ result มี embedding/ndarray/float32
        safe = to_serializable(result)

        # หรือจะ return แบบสั้น ๆ เองก็ได้ (แนะนำที่สุด):
        # safe = {
        #   "ok": True,
        #   "filename": f.filename,
        #   "stored_name": stored_name,
        #   "ingested": True
        # }

        return jsonify(safe), 200

    except Exception as e:
        logger.exception("Ingest failed for %s", stored_name)
        return jsonify({"error": f"ingest failed: {e}", "filename": f.filename}), 500

@bp.get("/list")
def list_files():
    os.makedirs(Config.UPLOAD_DIR, exist_ok=True)
    files = [fn for fn in os.listdir(Config.UPLOAD_DIR) if os.path.isfile(os.path.join(Config.UPLOAD_DIR, fn))]
    return jsonify({"files": files})


@bp.post("/search")
def search():
    data = request.get_json(force=True)
    req = SearchRequest(**data)
    hits = rag.search(req.query, k=req.k)
    return jsonify({"hits": hits})

@bp.delete("/delete")
def delete_file():
    """
    DELETE /api/files?name=<filename>
    - name ต้องเป็นชื่อไฟล์ตามที่แสดงใน /list (คือ stored_name ที่ผ่าน secure_filename แล้ว)
    """
    name = request.args.get("name")
    if not name:
        return jsonify({"error": "name is required"}), 400

    # ป้องกัน path traversal และให้สอดคล้องกับตอนบันทึก
    safe_name = secure_filename(name)
    file_path = os.path.join(Config.UPLOAD_DIR, safe_name)

    if not os.path.exists(file_path):
        return jsonify({"error": "file not found"}), 404

    # ลบไฟล์จริง
    try:
        os.remove(file_path)
    except Exception as e:
        logger.exception("Failed to remove file: %s", file_path)
        return jsonify({"error": f"cannot remove file: {e}"}), 500

    # พยายามลบจากดัชนี RAG โดยอาศัย metadata
    # รองรับทั้งคีย์ 'stored_name' และ 'filename' (กรณี front ส่งชื่อเดิมมา)
    removed_from_index = False
    try:
        # ถ้า service rag มีเมธอดลบตาม metadata (เช่น delete_by_metadata / delete / remove)
        if hasattr(rag, "delete_by_metadata"):
            # ลองด้วย stored_name ก่อน
            cnt1 = rag.delete_by_metadata({"stored_name": safe_name})
            # เผื่อบาง ingestion เก็บแต่ 'filename' (ชื่อเดิม)
            cnt2 = rag.delete_by_metadata({"filename": name})
            removed_from_index = bool((cnt1 or 0) + (cnt2 or 0))
        elif hasattr(rag, "delete"):  # ฟอลแบ็กชื่อเมธอดอื่น
            cnt1 = rag.delete({"stored_name": safe_name})
            cnt2 = rag.delete({"filename": name})
            removed_from_index = bool((cnt1 or 0) + (cnt2 or 0))
        elif hasattr(rag, "remove"):
            cnt1 = rag.remove({"stored_name": safe_name})
            cnt2 = rag.remove({"filename": name})
            removed_from_index = bool((cnt1 or 0) + (cnt2 or 0))
        else:
            # ถ้าไม่มีเมธอดลบ ก็ข้ามได้ (ไม่ถือเป็น error เพราะไฟล์ถูกลบไปแล้ว)
            logger.info("RAG delete method not available; skipped index removal")
    except Exception as e:
        # ไม่ทำให้การลบไฟล์ล้มเหลว แต่แจ้งเตือน
        logger.warning("Failed to remove from RAG index: %s", e)

    return jsonify({
        "success": True,
        "deleted": name,
        "removed_from_index": removed_from_index
    }), 200