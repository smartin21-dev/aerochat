import os
import random
import requests
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project structure
basedir = os.path.abspath(os.path.dirname(__file__))
template_folder = os.path.join(basedir, '..', 'client')
static_folder = os.path.join(basedir, '..', 'client')

app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# API configuration
API_KEY = os.getenv('API_NINJAS_KEY')
API_URL = 'https://api.api-ninjas.com/v1/randomword'

# Track active users
active_names = set()
users = {}

fallback_adjectives = ["Brave", "Clever", "Witty", "Chill", "Loyal", "Zany", "Bright", "Gentle", "Bold", "Jolly"]
fallback_nouns = ["Otter", "Falcon", "Lynx", "Moose", "Bear", "Rocket", "Wolf", "Candle", "Pine", "Tiger"]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/random_username')
def random_username():
    username = generate_username()
    return jsonify({'username': username})

def fetch_random_word():
    try:
        response = requests.get(API_URL, headers={'X-Api-Key': API_KEY})
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and "word" in data and isinstance(data["word"], list):
                return data["word"][0]
    except Exception as e:
        print(f"[fetch_random_word] Error: {e}")
    return None

def generate_username():
    for _ in range(10):
        adj = fetch_random_word() or random.choice(fallback_adjectives)
        noun = fetch_random_word() or random.choice(fallback_nouns)
        name = f"{adj.capitalize()}{noun.capitalize()}"
        return name

    base = "CoolPanda"
    i = 1
    while f"{base}{i}" in active_names:
        i += 1
    return f"{base}{i}"

@socketio.on('set_username')
def handle_set_username(data):
    sid = request.sid
    username = data.get('username')

    if not username:
        fallback = generate_username()
        users[sid] = fallback
        active_names.add(fallback)
        emit('assign_username', {'username': fallback})
        emit('message', {'msg': f"{fallback} joined the chat."}, broadcast=True)
        emit('update_user_list', list(users.values()), broadcast=True)
        return

    if username not in active_names:
        users[sid] = username
        active_names.add(username)
        emit('assign_username', {'username': username})
        emit('message', {'msg': f"{username} joined the chat."}, broadcast=True)
        emit('update_user_list', list(users.values()), broadcast=True)
    else:
        fallback = generate_username()
        users[sid] = fallback
        active_names.add(fallback)
        emit('assign_username', {'username': fallback})
        emit('message', {'msg': f"{fallback} joined the chat."}, broadcast=True)
        emit('update_user_list', list(users.values()), broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    username = users.pop(sid, None)
    if username:
        active_names.discard(username)
        emit('message', {'msg': f"{username} left the chat."}, broadcast=True)
        emit('update_user_list', list(users.values()), broadcast=True)

@socketio.on('message')
def handle_message(data):
    sid = request.sid
    username = users.get(sid, "Anon")
    print(f"[MESSAGE] {username}: {data['msg']}")
    emit('message', {'msg': f"{username}: {data['msg']}"}, broadcast=True)

@socketio.on('refresh_user_list')
def refresh_user_list():
    sid = request.sid
    emit('update_user_list', list(users.values()), room=sid)

if __name__ == '__main__':
    socketio.run(app, debug=True)