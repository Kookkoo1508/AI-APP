# app/utils/json.py
import json
from flask import Response

def json_error(message: str, status: int = 400, **extra):
    payload = {"error": message, **extra}
    body = json.dumps(payload, ensure_ascii=False)  # << สำคัญ
    return Response(body, status=status, mimetype="application/json")
