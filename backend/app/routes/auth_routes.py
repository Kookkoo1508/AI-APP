from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.user import User
from flask_jwt_extended import create_access_token, create_refresh_token
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended import jwt_required, get_jwt_identity

auth_bp = Blueprint("auth", __name__)

@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"message": "อีเมลหรือรหัสผ่านไม่ถูกต้อง"}), 401

    access_token = create_access_token(identity=str(user.id), additional_claims={
        "email": user.email, "name": user.name
    })

    refresh = create_refresh_token(identity=str(user.id))
    #  ส่ง key ชื่อ 'token' ให้ตรงกับ FE
    return jsonify(token=access_token, refresh_token=refresh, user=user.to_dict())

@auth_bp.post("/register")
def register():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"message": "ต้องมี email และ password"}), 400

    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"message": "อีเมลนี้มีผู้ใช้แล้ว"}), 409

    token = create_access_token(identity=user.id)
    return jsonify({"access_token": token, "user": user.to_dict()}), 201

@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    uid = get_jwt_identity()  # string
    new_access = create_access_token(identity=uid)
    return jsonify(token=new_access)