"""
RFID Attendance System - Backend Server (Flask + MySQL)
Authors: [Your Names]
Date: [Date]

This server handles:
- RFID attendance logging via POST requests
- Database connectivity checks
- API key authentication for secure access
"""

# =============================================================================
# Import Required Libraries
# =============================================================================
from flask import Flask, jsonify, request, abort
from flask_cors import CORS
import pymysql.cursors

# =============================================================================
# Initialize Flask Application
# =============================================================================
app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing

# =============================================================================
# Configuration Settings (Move to environment variables in production!)
# =============================================================================
API_KEY = "4102001"  # Secret key for API authentication

# MySQL Database Configuration
db_config = {
    'host': 'localhost',
    'user': 'daedalus',
    'password': '4102001',
    'database': 'attendance_db',
    'cursorclass': pymysql.cursors.DictCursor
}

# =============================================================================
# Authentication Middleware
# =============================================================================
def require_api_key(func):
    """
    Decorator function to validate API key in request headers
    """
    def wrapper(*args, **kwargs):
        provided_key = request.headers.get('X-API-Key')
        if provided_key != API_KEY:
            abort(401, "Invalid API key")
        return func(*args, **kwargs)
    return wrapper

# =============================================================================
# API Endpoints
# =============================================================================

@app.route('/api/db-test', methods=['GET'])
def db_test():
    """
    Test database connectivity
    Returns: JSON response with connection status
    """
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        return jsonify({
            "message": "Database connected! ✅", 
            "data": result
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/attendance', methods=['POST'])
@require_api_key  # Requires valid API key in headers
def record_attendance():
    """
    Record attendance from RFID scan
    Expected JSON payload: {"rfid_tag": "ABC123"}
    Returns: JSON confirmation or error message
    """
    # Get and validate request data
    data = request.get_json()
    rfid_tag = data.get('rfid_tag')
    
    if not rfid_tag:
        return jsonify({"error": "RFID tag is required"}), 400

    try:
        # Connect to database
        connection = pymysql.connect(**db_config)
        
        with connection.cursor() as cursor:
            # Step 1: Verify RFID exists in users table
            cursor.execute(
                "SELECT user_id FROM users WHERE rfid_tag = %s",
                (rfid_tag,)
            )
            user = cursor.fetchone()
            
            if not user:
                return jsonify({"error": "User not registered"}), 404

            # Step 2: Record attendance entry
            cursor.execute(
                "INSERT INTO attendance (user_id) VALUES (%s)",
                (user['user_id'],)
            )
            connection.commit()
            
        return jsonify({"message": "Attendance recorded! ✅"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =============================================================================
# Server Initialization
# =============================================================================
if __name__ == '__main__':
    app.run(
        debug=True,    # Debug mode (disable in production)
        port=5000      # Local development port
    )

"""
Security Improvements Needed for Production:
1. Replace hardcoded credentials with environment variables
2. Use HTTPS with SSL/TLS encryption
3. Implement rate limiting
4. Add input validation/sanitization
5. Disable debug mode
"""
