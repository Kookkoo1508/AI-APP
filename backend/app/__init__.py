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
from .routes.files import bp as files_bp

from werkzeug.exceptions import RequestEntityTooLarge
# from .routes.gemini_routes import gemini_bp  # เผื่ออนาคต

def create_app():
    # โหลด .env (ถ้ามี)
    load_dotenv()

    app = Flask(__name__)
    app.config.from_object(Config)

    # CORS สำหรับ dev (ใน prod ควรระบุ origin ที่อนุญาต)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # ensure data dirs
    os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)
    os.makedirs(app.config["CHROMA_DIR"], exist_ok=True)

    # init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(e):
        return jsonify({
            "error": "file too large",
            "max_mb": Config.MAX_UPLOAD_MB
        }), 413

    # health check
    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    # register blueprints ใต้ /api
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(user_bp, url_prefix="/api/user")
    app.register_blueprint(ai_bp,    url_prefix='/api/ai')
    app.register_blueprint(inbox_bp, url_prefix='/api/inbox')
    app.register_blueprint(files_bp, url_prefix='/api/files')

    return app
