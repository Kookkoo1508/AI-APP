import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from .config import Config
from .extensions import db, migrate, jwt
from .routes.auth_routes import auth_bp
from .routes.user_routes import user_bp
from .routes.ai_routes import ai_bp
from .routes.inbox_routes import inbox_bp
# from .routes.gemini_routes import gemini_bp  # เผื่ออนาคต

def create_app():
    # โหลด .env (ถ้ามี)
    load_dotenv()

    app = Flask(__name__)
    app.config.from_object(Config)

    # CORS สำหรับ dev (ใน prod ควรระบุ origin ที่อนุญาต)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # health check
    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    # register blueprints ใต้ /api
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(user_bp, url_prefix="/api/user")
    app.register_blueprint(ai_bp,    url_prefix='/api/ai')
    app.register_blueprint(inbox_bp, url_prefix='/api/inbox')

    return app
