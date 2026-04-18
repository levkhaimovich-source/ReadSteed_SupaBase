from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
import os
import secrets
from database import (init_db, create_user, login, get_readings, 
                      get_reading_content, save_reading, delete_reading, 
                      save_user_settings, get_user_settings, log_reading_session)
from rsvp_engine import tokenize_text, get_delay_multiplier

app = Flask(__name__)
# Use environment variable for secret key if available, otherwise fallback to a random one for local dev
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# Ensure database is initialized
init_db()

@app.route('/googled4b34a2a2616e236.html')
def google_verification():
    return send_from_directory('.', 'googled4b34a2a2616e236.html')

@app.route('/robots.txt')
def robots():
    return send_from_directory('.', 'robots.txt')

@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('.', 'sitemap.xml')

@app.route('/')
def index():
    if 'user_id' not in session:
        return render_template('index.html', user=None)
    return render_template('index.html', user={
        "username": session.get('username'),
        "is_premium": session.get('is_premium'),
        "user_id": session.get('user_id')
    })

@app.route('/about')
def about():
    if 'user_id' not in session:
        return render_template('about.html', user=None)
    return render_template('about.html', user={
        "username": session.get('username'),
        "is_premium": session.get('is_premium'),
        "user_id": session.get('user_id')
    })
@app.route('/api/auth/signup', methods=['POST'])
def signup_api():
    data = request.json
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')
    
    if create_user(email, username, password):
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "User already exists or error occurred"})

@app.route('/api/auth/login', methods=['POST'])
def login_api():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    success, result = login(email, password)
    if success:
        session['user_id'] = result['user_id']
        session['username'] = result['username']
        session['email'] = result['email']
        session['is_premium'] = result['is_premium']
        return jsonify({"success": True, "user": result})
    return jsonify({"success": False, "message": result})

@app.route('/api/auth/logout', methods=['POST'])
def logout_api():
    session.clear()
    return jsonify({"success": True})

@app.route('/api/readings', methods=['GET'])
def list_readings():
    if 'user_id' not in session:
        return jsonify([])
    readings = get_readings(session['user_id'])
    return jsonify(readings)

@app.route('/api/readings/<int:reading_id>', methods=['GET'])
def get_reading(reading_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    text, index = get_reading_content(reading_id, session['user_id'])
    return jsonify({"text": text, "index": index})

@app.route('/api/readings', methods=['POST'])
def save_reading_api():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    reading_id = data.get('id')
    text = data.get('text')
    index = data.get('index', 0)
    title = data.get('title', 'Untitled Reading')
    
    new_id = save_reading(session['user_id'], reading_id, text, index, title)
    return jsonify({"success": True, "id": new_id})

@app.route('/api/readings/<int:reading_id>', methods=['DELETE'])
def delete_reading_api(reading_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    delete_reading(reading_id, session['user_id'])
    return jsonify({"success": True})

@app.route('/api/settings', methods=['GET'])
def get_settings_api():
    if 'user_id' not in session:
        return jsonify({})
    settings = get_user_settings(session['user_id'])
    return jsonify(settings)

@app.route('/api/settings', methods=['POST'])
def save_settings_api():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    save_user_settings(session['user_id'], request.json)
    return jsonify({"success": True})

@app.route('/api/sessions', methods=['POST'])
def log_session_api():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    log_reading_session(
        session['user_id'], 
        data.get('words_read', 0), 
        data.get('duration_seconds', 0)
    )
    return jsonify({"success": True})

@app.route('/api/tokenize', methods=['POST'])
def tokenize_api():
    data = request.json
    text = data.get('text', '')
    words = tokenize_text(text)
    # Include delay multipliers to avoid redundant client-side logic
    processed_words = []
    for w in words:
        processed_words.append({
            "word": w,
            "delay_multiplier": get_delay_multiplier(w)
        })
    return jsonify(processed_words)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', debug=True, port=port)
