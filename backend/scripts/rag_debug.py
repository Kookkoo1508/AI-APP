# backend/scripts/rag_debug.py
import sys, json, os
# เติม backend ลง sys.path เผื่อรันตรง ๆ
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from app.services.rag import ingest_file

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python -m backend.scripts.rag_debug <path-to-file>")
        sys.exit(1)
    path = sys.argv[1]
    info = ingest_file(path, metadata={})
    print(json.dumps(info, ensure_ascii=False))
