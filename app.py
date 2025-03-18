"""
RFID Attendance System - Backend (Flask)
Version: 2.1
"""

# =================================================================================
# Section 1: Import Dependencies
# =================================================================================
# Core Flask components
from flask import Flask, jsonify, request, abort
from flask_cors import CORS

# Security and authentication
from functools import wraps
import jwt
import datetime
import bcrypt  # Added for password hashing

# Database connectivity
import psycopg2
from psycopg2 import pool

# Environment management
import os
from dotenv import load_dotenv

# Logging
import logging

# =================================================================================
# Section 2: Application Configuration
# =================================================================================
# Load environment variables from .env file
load_dotenv()

# Initialize Flask application
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configure CORS for API endpoints
CORS(app, resources={
    r"/api/*": {
        "origins": os.getenv("ALLOWED_ORIGINS", "*"),
        "methods": ["GET", "POST"],
        "allow_headers": ["Authorization", "Content-Type"]
    }
})

# =================================================================================
# Section 3: Security Configuration
# =================================================================================
# JWT Configuration
app.config['JWT_SECRET'] = os.getenv("JWT_SECRET", "fallback-secret-for-dev")
app.config['JWT_EXPIRATION_HOURS'] = int(os.getenv("JWT_EXPIRATION_HOURS", 1))

# =================================================================================
# Section 4: Database Configuration
# =================================================================================
# Database connection pool parameters
DB_CONFIG = {
    'minconn': 1,
    'maxconn': 20,
    'dbname': os.getenv("DB_NAME", "rfid_db"),
    'user': os.getenv("DB_USER", "postgres_user"),
    'password': os.getenv("DB_PASSWORD", "4102001Oli@"),
    'host': os.getenv("DB_HOST", "localhost"),
    'port': os.getenv("DB_PORT", "5432")
}

# Connection pool initialization
try:
    postgres_pool = psycopg2.pool.ThreadedConnectionPool(**DB_CONFIG)
    logger.info(f"Database connection pool created successfully with params: {DB_CONFIG}")
    logger.info(f"Pool status: {postgres_pool}")
except psycopg2.OperationalError as e:
    postgres_pool = None
    logger.error(f"Database connection failed: {str(e)}")
    # Consider adding automatic retry logic here in production

# =================================================================================
# Section 5: Helper Functions and Decorators
# =================================================================================
def get_db_connection():
    """Acquire a database connection from the pool"""
    if not postgres_pool:
        abort(500, "Database connection unavailable")
    conn = postgres_pool.getconn()

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
    except psycopg2.InterfaceError:
        postgres_pool.putconn(conn, close=True)
        conn = postgres_pool.getconn()
    
    return conn


def release_db_connection(conn):
    """Release a database connection back to the pool"""
    postgres_pool.putconn(conn)


def validate_json(schema):
    """Decorator to validate incoming JSON payload structure"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Check content type
            if not request.is_json:
                return jsonify({"error": "Request must be JSON"}), 400
                
            # Validate payload structure
            try:
                data = request.get_json()
                missing = [field for field in schema if field not in data]
                if missing:
                    return jsonify({
                        "error": "Missing required fields",
                        "missing": missing
                    }), 400
                return f(*args, **kwargs)
            except Exception as e:
                logger.error(f"JSON validation error: {str(e)}")
                return jsonify({"error": "Invalid JSON format"}), 400
        return wrapper
    return decorator

# =================================================================================
# Section 6: Authentication Middleware
# =================================================================================
def token_required(f):
    """JWT Authentication decorator for protected endpoints"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Extract JWT from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid authorization header"}), 401
        
        try:
            # Decode and verify JWT
            token = auth_header.split(" ")[1]
            payload = jwt.decode(
                token, 
                app.config['JWT_SECRET'], 
                algorithms=["HS256"]
            )
            current_user = payload["sub"]
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
            
        # Pass user context to the route
        return f(current_user, *args, **kwargs)
    return decorated


@app.route("/api/auth/validate", methods=["POST"])
@token_required
def validate_token(current_user):
    """Validate JWT token and return expiration info"""
    try:
        auth_header = request.headers.get("Authorization")
        token = auth_header.split()[1]
        
        logger.info(f"Validating token: {token}")
        logger.info(f"Using JWT_SECRET: {app.config['JWT_SECRET']}")

        payload = jwt.decode(token, app.config['JWT_SECRET'], algorithms=["HS256"])
        
        return jsonify({
            "valid": True,
            "user_id": current_user,
            "expires_at": datetime.datetime.utcfromtimestamp(payload["exp"]).isoformat()
        })
    except Exception as e:
        logger.error(f"Token validation failed: {str(e)}")
        return jsonify({"valid": False, "error": str(e)}), 401

# =================================================================================
# Section 7: API Endpoints
# =================================================================================
# -------------------------------
# Subsection 7.1: Health Checks
# -------------------------------
@app.route("/api/health", methods=["GET"])
def health_check():
    """Basic service health check"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "version": "2.1"
    })


@app.route("/api/health/db", methods=["GET"])
def db_health_check():
    """Database connection health check"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT version()")
            db_version = cursor.fetchone()[0]
        return jsonify({
            "database": "connected",
            "status": "ok",
            "version": db_version
        })
    except Exception as e:
        return jsonify({
            "database": "disconnected",
            "error": str(e)
        }), 500
    finally:
        if conn:
            release_db_connection(conn)

# -------------------------------
# Subsection 7.2: Authentication
# -------------------------------
@app.route("/api/auth/test_bcrypt", methods=["POST"])
def test_bcrypt():
    """Test bcrypt password verification"""
    stored_hash = "$2b$12$gBvG.afg96NK.pnVpqHc2.hAMx4V3cB0Ebhg3wyFTy40PwBhfoPD6"
    password = "testpass123"
    return jsonify({
        "match": bcrypt.checkpw(password.encode(), stored_hash.encode())
    })


@app.route("/api/auth/login", methods=["POST"])
@validate_json(["username", "password"])
def login():
    """User authentication endpoint"""
    data = request.get_json()
    logger.debug(f"\n--- Login Attempt ---")
    logger.debug(f"Username Received: {data['username']}")
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            username = data["username"].strip()
            password = data["password"].strip()

            cursor.execute("""
                SELECT id, name, password_hash 
                FROM users 
                WHERE LOWER(name) = LOWER(%s)
                """, 
                (username,)
            )
            user = cursor.fetchone()
            logger.debug(f"Database User: {user}")
            
            if not user:
                return jsonify({"error": "Invalid credentials"}), 401

            logger.debug(f"Stored Hash: {user[2]}")
            logger.debug(f"Input Password: {password}")
            
            # Password verification
            password_bytes = password.encode('utf-8')
            stored_hash_bytes = user[2].encode('utf-8')
            is_valid = bcrypt.checkpw(password_bytes, stored_hash_bytes)
            logger.debug(f"Password Valid: {is_valid}")
            
            if not is_valid:
                return jsonify({"error": "Invalid credentials"}), 401

            # Generate JWT
            token = jwt.encode({
                "sub": user[0],
                "name": user[1],
                "exp": datetime.datetime.utcnow() + datetime.timedelta(
                    hours=app.config['JWT_EXPIRATION_HOURS']
                )
            }, app.config['JWT_SECRET'], algorithm="HS256")

            logger.info(f"Successful login for user: {user[1]}")
            return jsonify({
                "token": token,
                "user_id": user[0],
                "user_name": user[1]
            })
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({"error": "Authentication failed"}), 500
    finally:
        if conn:
            release_db_connection(conn)

# -------------------------------
# Subsection 7.3: Attendance Management
# -------------------------------
@app.route("/api/attendance", methods=["POST"])
@token_required
@validate_json(["rfid_uid"])
def record_attendance(current_user):
    """Record RFID-based attendance entry"""
    data = request.get_json()
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Check RFID registration
            cursor.execute(
                "SELECT id, name FROM users WHERE rfid_uid = %s",
                (data["rfid_uid"],)
            )
            user = cursor.fetchone()
            
            if not user:
                return jsonify({
                    "error": "RFID not registered",
                    "rfid_uid": data["rfid_uid"]
                }), 404
            
            # Create attendance record
            cursor.execute("""
                INSERT INTO attendance (user_id) 
                VALUES (%s) 
                RETURNING id, timestamp
                """, 
                (user[0],)
            )
            record = cursor.fetchone()
            conn.commit()
            
            return jsonify({
                "message": "Attendance recorded",
                "user_id": user[0],
                "user_name": user[1],
                "attendance_id": record[0],
                "timestamp": record[1].isoformat()
            })
    except psycopg2.DatabaseError as e:
        conn.rollback()
        logger.error(f"Database error: {str(e)}")
        return jsonify({"error": "Database operation failed"}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        if conn:
            release_db_connection(conn)


@app.route("/api/attendance", methods=["GET"])
@token_required
def get_attendance(current_user):
    """Retrieve recent attendance records"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT a.id, u.name, a.timestamp 
                FROM attendance a
                JOIN users u ON a.user_id = u.id
                ORDER BY a.timestamp DESC
                LIMIT 100
            """)
            return jsonify({
                "count": cursor.rowcount,
                "records": [{
                    "id": row[0],
                    "name": row[1],
                    "timestamp": row[2].isoformat()
                } for row in cursor.fetchall()]
            })
    except Exception as e:
        logger.error(f"Attendance fetch error: {str(e)}")
        return jsonify({"error": "Failed to retrieve records"}), 500
    finally:
        if conn:
            release_db_connection(conn)

# =================================================================================
# Section 8: Error Handlers
# =================================================================================
@app.errorhandler(400)
def bad_request_error(e):
    return jsonify({
        "error": "Bad request",
        "message": "Invalid or malformed request"
    }), 400


@app.errorhandler(401)
def unauthorized_error(e):
    return jsonify({
        "error": "Unauthorized",
        "message": "Authentication credentials invalid/missing"
    }), 401


@app.errorhandler(403)
def forbidden_error(e):
    return jsonify({
        "error": "Forbidden",
        "message": "You don't have permission to access this resource"
    }), 403


@app.errorhandler(404)
def not_found_error(e):
    return jsonify({
        "error": "Resource not found",
        "message": "The requested resource was not found"
    }), 404


@app.errorhandler(405)
def method_not_allowed_error(e):
    return jsonify({
        "error": "Method not allowed",
        "message": "The requested method is not supported for this endpoint"
    }), 405


@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500

# =================================================================================
# Section 9: Application Entry Point
# =================================================================================
if __name__ == "__main__":
    # Configure port from environment variable or default
    port = int(os.environ.get("PORT", 5000))
    
    # Start application server
    app.run(
        host="0.0.0.0",
        port=port,
        # Disable debug in production
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    )
