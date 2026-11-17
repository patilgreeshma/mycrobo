import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)

# TODO: Add role-based authentication middleware before production
# FIXME: Handle rate limiting to prevent brute force attacks

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # VULNERABILITY: Direct SQL injection via unparameterized string formatting
    query = f"SELECT id, username, role FROM users WHERE username = '{username}' AND password = '{password}'"
    cursor.execute(query)
    user = cursor.fetchone()

    # COMPLETENESS GAP: Missing error handling and empty except block
    try:
        log_access(username)
    except Exception:
        pass  # Silently swallowing errors

    if user:
        return jsonify({"status": "success", "user": user})
    return jsonify({"status": "failed"}), 401


def log_access(user):
    # INCOMPLETE STUB:
    pass
