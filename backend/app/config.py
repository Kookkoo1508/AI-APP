import os
from datetime import timedelta

class Config:
    # Core
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"

    # Database (เริ่มด้วย SQLite ก่อน ง่ายสุด)
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret")
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_TYPE = "Bearer"

    # ตั้งอายุโทเค็นเริ่มต้น
    JWT_ACCESS_TOKEN_EXPIRES  = timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MIN", "60"))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES_DAYS", "30"))
    )

    UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "data", "uploads"))
    CHROMA_DIR = os.getenv("CHROMA_DIR", os.path.join(os.path.dirname(__file__), "data", "chroma"))
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    # MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 50 * 1024 * 1024))  # 50MB
    ALLOWED_EXTS = {"txt", "md", "pdf", "docx"}

    RAG_TOPK_DEFAULT = int(os.getenv("RAG_TOPK_DEFAULT", 6))
    RAG_MAX_DISTANCE = float(os.getenv("RAG_MAX_DISTANCE", 0.35))  # ยิ่งต่ำยิ่งใกล้ (cosine distance)
    RAG_CHUNK_CHARS = int(os.getenv("RAG_CHUNK_CHARS", 1100))
    RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", 200))
    RAG_MAX_DOC_CHARS = int(os.getenv("RAG_MAX_DOC_CHARS", 900))   # จำกัดต่อชิ้น
    RAG_MAX_CONTEXT_CHARS = int(os.getenv("RAG_MAX_CONTEXT_CHARS", 3500)) 

    MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", 50))  # ปรับได้ตามต้องการ
    MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024