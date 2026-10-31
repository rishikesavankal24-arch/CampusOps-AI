"""Safe Google Gemini API connectivity test script.

SAFEGUARDS:
- Never prints, logs, or exposes the GEMINI_API_KEY value.
- Queries the models list endpoint to verify credential validity without making chargeable generations.
"""

import sys
import os
import requests

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings


def test_gemini_connectivity() -> bool:
    print("=" * 60)
    print("CampusOps AI — Google Gemini API Connectivity Check")
    print("=" * 60)

    if not settings.is_gemini_configured:
        print("[STATUS] GEMINI_API_KEY is NOT configured in backend/.env.")
        print("[ACTION] Please open backend/.env and add: GEMINI_API_KEY=<your-key>")
        return False

    print("[STATUS] GEMINI_API_KEY is detected in backend/.env (value hidden).")
    print("[STATUS] Performing lightweight read-only connectivity test...")

    # Query the available models endpoint
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={settings.gemini_api_key.strip()}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            models = [m.get("name", "").replace("models/", "") for m in data.get("models", [])]
            gemini_models = [m for m in models if "gemini" in m.lower()]
            print("[SUCCESS] Connected to Google Gemini API successfully!")
            print(f"[SUCCESS] HTTP Status: {response.status_code} OK")
            print(f"[INFO] Available Gemini Models ({len(gemini_models)} found):")
            for model_name in gemini_models[:8]:
                print(f"  - {model_name}")
            if len(gemini_models) > 8:
                print(f"  ... and {len(gemini_models) - 8} more models.")
            return True
        elif response.status_code == 400:
            data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            err_msg = data.get("error", {}).get("message", "API_KEY_INVALID")
            print(f"[ERROR] Authentication failed (HTTP 400): {err_msg}")
            return False
        elif response.status_code == 403:
            data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            err_msg = data.get("error", {}).get("message", "PERMISSION_DENIED")
            print(f"[ERROR] Permission denied (HTTP 403): {err_msg}")
            return False
        elif response.status_code == 429:
            print("[ERROR] Rate limit / quota exhausted (HTTP 429: RESOURCE_EXHAUSTED).")
            return False
        else:
            print(f"[ERROR] Unexpected response from Gemini API: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Network error connecting to Google Gemini API: {type(e).__name__}")
        return False


if __name__ == "__main__":
    success = test_gemini_connectivity()
    sys.exit(0 if success else 1)

