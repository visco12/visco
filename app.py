# =======================================
# 🔥 ESCO SMART FLASK BACKEND (CORRECTED)
# =======================================
from flask import Flask, jsonify, request
from flask_cors import CORS
from rapidfuzz import fuzz
from supabase import create_client
from playwright.sync_api import sync_playwright
import re, random, time
import os
from dotenv import load_dotenv
from jose import jwt

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_JWT_SECRET = os.getenv("JWT_SECRET")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
CORS(app)  # ✅ Apply CORS to all routes automatically

print("🔥 Backend Started")

# =========================
# USER AGENTS
# =========================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.1 Safari/605.1.15",
]

# =========================
# HELPERS
# =========================
def verify_token(token):
    try:
        user = supabase.auth.get_user(token)
        return user
    except Exception as e:
        print("Auth error:", e)
        return None
def clean_text(text):
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def random_delay(min_sec=1, max_sec=3):
    time.sleep(random.uniform(min_sec, max_sec))

# =========================
# SAVE / UPDATE PRODUCT
# =========================
def save_product(item):
    try:
        name = item.get("name", "")
        if not name:
            return

        cleaned = clean_text(name)
        products = supabase.table("product").select("*").execute().data or []

        for p in products:
            if fuzz.token_set_ratio(cleaned, clean_text(p.get("name", ""))) > 60:
                update_data = {"image": item.get("image", p.get("image", ""))}
                if item["source"] == "amazon":
                    update_data["amazon"] = item.get("price", 0)
                    update_data["amazon_link"] = item.get("link", "")
                elif item["source"] == "flipkart":
                    update_data["flipkart"] = item.get("price", 0)
                    update_data["flipkart_link"] = item.get("link", "")
                supabase.table("product").update(update_data).eq("id", p["id"]).execute()
                print(f"✅ Updated: {name[:50]}...")
                return

        # Insert new product
        new_product = {
            "name": name,
            "category": item.get("category", "electronics"),
            "image": item.get("image", ""),
            "amazon": item.get("price", 0) if item["source"] == "amazon" else 0,
            "flipkart": item.get("price", 0) if item["source"] == "flipkart" else 0,
            "amazon_link": item.get("link", "") if item["source"] == "amazon" else "",
            "flipkart_link": item.get("link", "") if item["source"] == "flipkart" else ""
        }
        res = supabase.table("product").insert(new_product).execute()
        if res.data:
            print(f"✅ Inserted: {name[:50]}...")
        else:
            print(f"⚠️ Insert returned no data for {name[:50]}...")

    except Exception as e:
        print(f"❌ Save Error: {e}")

# =========================
# ROUTES
# =========================# =========================
# ROUTES
# =========================

@app.route("/")
def home():
    return jsonify({"status": "running"})


# =========================
# DETAIL PAGE
# =========================
@app.route("/product/<int:product_id>")
def get_product(product_id):
    try:
        data = supabase.table("product").select("*").eq("id", product_id).execute().data

        if not data:
            return jsonify({"error": "Product not found"}), 404

        data[0]['links'] = {
            "amazon": data[0].get("amazon_link", ""),
            "flipkart": data[0].get("flipkart_link", "")
        }

        return jsonify(data[0])

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# PRODUCTS (PROTECTED 🔐)
# =========================
@app.route("/products")
def all_products():
    auth_header = request.headers.get("Authorization")

    # Check header exists and correct format
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401

    # Extract token
    token = auth_header.split("Bearer ")[1]

    # Verify token with Supabase
    user = verify_token(token)

    if not user:
        return jsonify({"error": "Invalid token"}), 401

    try:
        data = supabase.table("product").select("*").execute().data or []

        for p in data:
            p['amazon'] = p.get('amazon', 0)
            p['flipkart'] = p.get('flipkart', 0)
            p['amazon_link'] = p.get('amazon_link', "#")
            p['flipkart_link'] = p.get('flipkart_link', "#")

        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================
# MATCH PRODUCT
# =========================
@app.route("/match", methods=["POST"])
def match_product():
    payload = request.get_json()
    title = clean_text(payload.get("title", ""))

    products = supabase.table("product").select("*").execute().data or []

    for p in products:
        if fuzz.token_set_ratio(clean_text(p.get("name", "")), title) > 60:
            return jsonify({"status": "found", "id": p["id"]})

    return jsonify({"status": "not_found"})


# =========================
# ADD PRODUCT
# =========================
@app.route("/add", methods=["POST"])
def add_product_route():
    payload = request.get_json()
    print("📥 Payload received for /add:", payload)

    new_product = {
        "name": payload.get("name") or "Unknown Product",
        "category": payload.get("category") or "electronics",
        "image": payload.get("image") or "",
        "amazon_link": payload.get("amazon_link") or "",
        "flipkart_link": payload.get("flipkart_link") or "",
        "amazon": payload.get("amazon") or 0,
        "flipkart": payload.get("flipkart") or 0
    }

    try:
        res = supabase.table("product").insert(new_product).execute()

        print("💾 Supabase insert result:", res.data)

        if res.data and len(res.data) > 0:
            product_id = res.data[0].get("id")
            return jsonify({"status": "added", "id": product_id})
        else:
            return jsonify({"status": "added_but_no_id", "data": new_product})

    except Exception as e:
        print("❌ /add ERROR:", e)
        return jsonify({"error": str(e)}), 500


# =========================
# UPDATE PRODUCT
# =========================
@app.route("/update", methods=["POST"])
def update_product():
    payload = request.get_json()
    product_id = payload.get("id")

    update_data = {}

    for field in ["image", "amazon", "flipkart", "amazon_link", "flipkart_link"]:
        if field in payload and payload[field] is not None:
            update_data[field] = payload[field]

    try:
        supabase.table("product").update(update_data).eq("id", product_id).execute()
        return jsonify({"status": "updated"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# RUN SERVER
# =========================
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)