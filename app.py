# =======================================
# 🔥 ESCO SMART FLASK BACKEND (PRODUCTION READY)
# =======================================

from flask import Flask, jsonify, request
from flask_cors import CORS
from rapidfuzz import fuzz
from supabase import create_client
import re, random, time, os
from werkzeug.security import generate_password_hash, check_password_hash
# =========================
# ENV VARIABLES (RENDER)
# =========================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_JWT_SECRET = os.environ.get("JWT_SECRET")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("❌ Supabase ENV variables missing")
# Init Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Flask App
app = Flask(__name__)
CORS(app)

print("🔥 Backend Started")

# =========================
# USER AGENTS
# =========================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (X11; Linux x86_64)",
]

# =========================
# HELPERS
# =========================
def verify_token(token):
    if not token:
        return None

    user = supabase.table("users").select("*").eq("phone", token).execute().data

    return user[0] if user else None

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
# ROUTES
# =========================

@app.route("/")
def home():
    return jsonify({"status": "running"})

# =========================
# GET PRODUCT DETAILS
# =========================
@app.route("/product/<int:product_id>")
def get_product(product_id):
    try:
        data = supabase.table("product").select("*").eq("id", product_id).execute().data

        if not data:
            return jsonify({"error": "Product not found"}), 404

        product = data[0]

        product['links'] = {
            "amazon": product.get("amazon_link", ""),
            "flipkart": product.get("flipkart_link", "")
        }

        return jsonify(product)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================
# GET ALL PRODUCTS (PROTECTED)
# =========================
@app.route("/products")
def all_products():
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401

    token = auth_header.split("Bearer ")[1]
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
def add_product():
    payload = request.get_json()

    new_product = {
        "name": payload.get("name", "Unknown Product"),
        "category": payload.get("category", "electronics"),
        "image": payload.get("image", ""),
        "amazon_link": payload.get("amazon_link", ""),
        "flipkart_link": payload.get("flipkart_link", ""),
        "amazon": payload.get("amazon", 0),
        "flipkart": payload.get("flipkart", 0)
    }

    try:
        res = supabase.table("product").insert(new_product).execute()

        if res.data:
            return jsonify({"status": "added", "id": res.data[0]["id"]})
        else:
            return jsonify({"status": "failed"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route("/me", methods=["GET"])
def me():
    auth = request.headers.get("Authorization")

    if not auth:
        return jsonify({"error": "No token"}), 401

    token = auth.replace("Bearer ", "")

    user = verify_token(token)

    if not user:
        return jsonify({"error": "Invalid token"}), 401

    return jsonify({
        "status": "valid",
        "user": user
    })

@app.route("/signup-phone", methods=["POST"])
def signup_phone():
    data = request.get_json()

    name = data.get("name")
    phone = data.get("phone")
    password = data.get("password")

   if not name or not phone or not password:
        return jsonify({"error": "Missing fields"}), 400

    # check duplicate
    existing = supabase.table("users").select("*").eq("phone", phone).execute().data
    if existing:
        return jsonify({"error": "User already exists"}), 400

    # hash password
    hashed = generate_password_hash(password)

    try:
        supabase.table("users").insert({
            "name": name,
            "phone": phone,
            "password": hashed
        }).execute()

        return jsonify({"status": "created"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
        
@app.route("/login-phone", methods=["POST"])
def login_phone():
    data = request.get_json()

    phone = data.get("phone")
    password = data.get("password")

    if not phone or not password:
        return jsonify({"error": "Missing fields"}), 400

    res = supabase.table("users").select("*").eq("phone", phone).execute().data

    if not res:
        return jsonify({"error": "User not found"}), 404

    user = res[0]

if check_password_hash(user["password"], password):
   token = str(uuid.uuid4())

    return jsonify({
        "status": "success",
        "token": token,
        "name": user.get("name", "")
  })
    else:
        return jsonify({"error": "Invalid password"}), 401
# =========================
# UPDATE PRODUCT
# =========================
@app.route("/update", methods=["POST"])
def update_product():
    payload = request.get_json()
    product_id = payload.get("id")

    update_data = {}

    for field in ["image", "amazon", "flipkart", "amazon_link", "flipkart_link"]:
        if field in payload:
            update_data[field] = payload[field]

    try:
        supabase.table("product").update(update_data).eq("id", product_id).execute()
        return jsonify({"status": "updated"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================
# RUN SERVER (RENDER READY)
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
