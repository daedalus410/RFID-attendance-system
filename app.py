"""
RFID Attendance System - Backend (Flask)
Authors: [Your Names]
Date: [Date]

Supports:
- MySQL (local development)
- PostgreSQL (Heroku production)
- JWT authentication
- Environment variables for security
"""

# =============================================================================
# Imports and Configuration
# =============================================================================
from flask import Flask, jsonify, request, abort
from flask_cors import CORS
import os
import jwt
import datetime
from functools import wraps
from dotenv import load_dotenv

# Database connectors (both installed via requirements.txt)
try:
    import pymysql.cursors  # MySQL
except ImportError:
    pass  # Not needed on Heroku

try:
    import psycopg2  # PostgreSQL
except ImportError:
    pass  # Not needed locally

load_dotenv()

app = Flask(__name__)
CORS(app)

# =============================================================================
# Database Configuration
# =============================================================================

def get_db_connection():
    """
    Returns a database connection based on the environment.
    - Uses PostgreSQL on Heroku (DATABASE_URL auto-set by Heroku)
    - Uses MySQL locally (credentials from .env)
    """
    if 'DYNO' in os.environ:  # Detect Heroku environment
        # PostgreSQL connection for Heroku
        conn = psycopg2.connect(
            os.getenv("DATABASE_URL"),
            sslmode='require'
        )
    else:
        # MySQL connection for local development
        conn = pymysql.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "daedalus"),
            password=os.getenv("DB_PASSWORD", "4102001"),
            database=os.getenv("DB_NAME", "attendance_db"),
            cursorclass=pymysql.cursors.DictCursor
        )
    return conn

# =============================================================================
# JWT Authentication
# =============================================================================

JWT_SECRET = os.getenv("JWT_SECRET", "fallback-secret-for-dev")

def generate_token(user_id):
    """Generate JWT token for authenticated users"""
    payload = {
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
        "iat": datetime.datetime.utcnow(),
        "sub": user_id
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def token_required(f):
    """Decorator to validate JWT tokens"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            abort(401, "Token missing")
        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            current_user = data["sub"]
        except jwt.ExpiredSignatureError:
            abort(401, "Token expired")
        except Exception as e:
            abort(401, "Invalid token")
        return f(current_user, *args, **kwargs)
    return decorated

# =============================================================================
# API Endpoints
# =============================================================================

@app.route('/api/db-test', methods=['GET'])
def db_test():
    """Test database connectivity for both MySQL/PostgreSQL"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        return jsonify({"message": "Database connected!", "data": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Authenticate users (mock credentials - replace with real user table)"""
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    # Replace with actual user table query
    if username == "admin" and password == "admin123":
        token = generate_token(1)  # user_id=1 for admin
        return jsonify({"token": token})
    else:
        return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/attendance', methods=['POST'])
def record_attendance():
    """Record attendance from RFID scan (works with both DBs)"""
    data = request.get_json()
    rfid_tag = data.get("rfid_tag")

    if not rfid_tag:
        return jsonify({"error": "RFID required"}), 400

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Works for both MySQL and PostgreSQL
            cursor.execute(
                "SELECT user_id FROM users WHERE rfid_tag = %s",
                (rfid_tag,)
            )
            user = cursor.fetchone()
            
            if not user:
                return jsonify({"error": "User not found"}), 404

            # PostgreSQL uses SERIAL, MySQL uses AUTO_INCREMENT
            cursor.execute(
                "INSERT INTO attendance (user_id) VALUES (%s)",
                (user['user_id'],)
            )
            conn.commit()
            
        return jsonify({"message": "Attendance recorded!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =============================================================================
# Server Initialization
# =============================================================================

if __name__ == '__main__':
    # Heroku sets PORT environment variable
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=(os.getenv("FLASK_ENV") == "development")
    )
