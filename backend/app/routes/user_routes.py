from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user import User

user_bp = Blueprint("user", __name__)

@user_bp.get("/me")
@jwt_required()
def me():
    uid = int(get_jwt_identity())
    user = User.query.get(uid)
    if not user:
        return jsonify({"message": "ไม่พบผู้ใช้"}), 404
    return jsonify({"user": user.to_dict()})
