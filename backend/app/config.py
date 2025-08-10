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