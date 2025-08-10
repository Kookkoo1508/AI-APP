from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.task import Task

inbox_bp = Blueprint("inbox", __name__)

def _owner_filter(query):
    uid = int(get_jwt_identity())
    return query.filter(Task.owner_id == uid)

@inbox_bp.get("/tasks")
@jwt_required()
def list_tasks():
    q = _owner_filter(Task.query).filter_by(is_archived=False)
    items = [t.to_dict() for t in q.order_by(Task.created_at.desc()).all()]
    return jsonify({"items": items})

@inbox_bp.post("/tasks")
@jwt_required()
def create_task():
    uid = int(get_jwt_identity())
    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"message": "title is required"}), 400
    t = Task(owner_id=uid, title=title, notes=data.get("notes"))
    db.session.add(t)
    db.session.commit()
    return jsonify({"item": t.to_dict()}), 201

@inbox_bp.patch("/tasks/<int:task_id>")
@jwt_required()
def update_task(task_id: int):
    data = request.get_json() or {}
    t = _owner_filter(Task.query).filter_by(id=task_id).first_or_404()
    if "title" in data: t.title = data["title"]
    if "notes" in data: t.notes = data["notes"]
    if "is_done" in data: t.is_done = bool(data["is_done"])
    db.session.commit()
    return jsonify({"item": t.to_dict()})

@inbox_bp.post("/tasks/<int:task_id>/archive")
@jwt_required()
def archive_task(task_id: int):
    t = _owner_filter(Task.query).filter_by(id=task_id).first_or_404()
    t.is_archived = True
    db.session.commit()
    return jsonify({"item": t.to_dict()})

@inbox_bp.get("/archive")
@jwt_required()
def list_archive():
    q = _owner_filter(Task.query).filter_by(is_archived=True)
    items = [t.to_dict() for t in q.order_by(Task.updated_at.desc()).all()]
    return jsonify({"items": items})
