import os
import random
import requests
import time
import re
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
from collections import defaultdict

# Load environment variables
load_dotenv()

# Project structure
basedir = os.path.abspath(os.path.dirname(__file__))
template_folder = os.path.join(basedir, '..', 'client')
static_folder = os.path.join(basedir, '..', 'client')

app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# Rate limiting configuration
MESSAGE_COOLDOWN = 3  # seconds between messages
user_last_message = defaultdict(float)  # Track last message time for each user

# Admin configuration
admin_sid = None  # Store the admin's session ID

# Spam detection configuration
SPAM_PATTERNS = [
    r'(?i)(buy|sell|discount|offer|deal|price|cheap|free|limited)',
    r'(?i)(http|www|\.com|\.org|\.net)',
    r'(?i)(casino|bet|gambling|lottery)',
    r'(?i)(viagra|cialis|levitra)',
    r'(?i)(click here|sign up|register now)',
    r'(?i)(earn money|make money|work from home)',
    r'(?i)(weight loss|diet|supplement)',
    r'(?i)(bitcoin|crypto|nft|token)',
]

# API configuration
API_KEY = os.getenv('API_NINJAS_KEY')
API_URL = 'https://api.api-ninjas.com/v1/randomword'

# Track active users
active_names = set()
users = {}
votekicks = {}  # Store active votekicks
video_queue = []  # Store video queue
voteskips = set()  # Store voteskip votes

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
    global admin_sid
    sid = request.sid
    username = data.get('username')

    # Check if this is the first user (will be admin)
    is_admin = admin_sid is None
    if is_admin:
        admin_sid = sid
        username = f"[ADMIN] {username}" if username else "[ADMIN] " + generate_username()

    if not username:
        fallback = generate_username()
        if is_admin:
            fallback = f"[ADMIN] {fallback}"
        users[sid] = fallback
        active_names.add(fallback)
        emit('assign_username', {'username': fallback, 'is_admin': is_admin})
        emit('message', {'msg': f"{fallback} joined the chat."}, broadcast=True)
        emit('update_user_list', list(users.values()), broadcast=True)
        return

    if username not in active_names:
        users[sid] = username
        active_names.add(username)
        emit('assign_username', {'username': username, 'is_admin': is_admin})
        emit('message', {'msg': f"{username} joined the chat."}, broadcast=True)
        emit('update_user_list', list(users.values()), broadcast=True)
    else:
        fallback = generate_username()
        if is_admin:
            fallback = f"[ADMIN] {fallback}"
        users[sid] = fallback
        active_names.add(fallback)
        emit('assign_username', {'username': fallback, 'is_admin': is_admin})
        emit('message', {'msg': f"{fallback} joined the chat."}, broadcast=True)
        emit('update_user_list', list(users.values()), broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    global admin_sid
    sid = request.sid
    username = users.pop(sid, None)
    if username:
        active_names.discard(username)
        # Clean up any votekicks involving this user
        if username in votekicks:
            del votekicks[username]
        # Remove voteskip vote if user had voted
        if sid in voteskips:
            voteskips.remove(sid)
        # If admin disconnects, clear admin status
        if sid == admin_sid:
            admin_sid = None
        emit('message', {'msg': f"{username} left the chat."}, broadcast=True)
        emit('update_user_list', list(users.values()), broadcast=True)

@socketio.on('message')
def handle_message(data):
    sid = request.sid
    username = users.get(sid, "Anon")
    msg = data['msg']
    
    # Check rate limiting
    current_time = time.time()
    last_message_time = user_last_message[sid]
    if current_time - last_message_time < MESSAGE_COOLDOWN:
        remaining_time = MESSAGE_COOLDOWN - (current_time - last_message_time)
        emit('message', {'msg': f"Please wait {remaining_time:.1f} seconds before sending another message."}, room=sid)
        return

    # Check for spam
    if any(re.search(pattern, msg) for pattern in SPAM_PATTERNS):
        emit('message', {'msg': "Your message was blocked due to spam detection."}, room=sid)
        return

    # Update last message time
    user_last_message[sid] = current_time
    
    # Handle admin commands
    if sid == admin_sid:
        if msg == '/forceskip':
            if video_queue:
                next_video = video_queue.pop(0)
                emit('play_next_video', next_video, broadcast=True)
                emit('queue_update', {'queue': video_queue}, broadcast=True)
                emit('message', {'msg': f"[ADMIN] Video force skipped. Now playing: {next_video['title']}"}, broadcast=True)
                voteskips.clear()  # Reset voteskips
            else:
                emit('message', {'msg': "No videos in queue to skip to."}, room=sid)
            return
        elif msg == '/clearqueue':
            video_queue.clear()
            emit('queue_update', {'queue': video_queue}, broadcast=True)
            emit('message', {'msg': "[ADMIN] Video queue has been cleared."}, broadcast=True)
            return
    
    # Handle votekick command
    if msg.startswith('/votekick '):
        target = msg.split(' ', 1)[1].strip()
        if target not in users.values():
            emit('message', {'msg': f"User {target} not found."}, room=sid)
            return
        
        if target == username:
            emit('message', {'msg': "You cannot votekick yourself."}, room=sid)
            return
            
        # Initialize or update votekick
        if target not in votekicks:
            votekicks[target] = {'votes': set(), 'initiator': sid}
        
        # Check if user already voted
        if sid in votekicks[target]['votes']:
            emit('message', {'msg': "You have already voted to kick this user."}, room=sid)
            return
            
        # Add vote
        votekicks[target]['votes'].add(sid)
        vote_count = len(votekicks[target]['votes'])
        
        # Broadcast votekick status
        emit('message', {'msg': f"Votekick for {target}: {vote_count}/3 votes"}, broadcast=True)
        
        # Check if kick threshold reached
        if vote_count >= 3:
            # Find target's sid
            target_sid = None
            for s, u in users.items():
                if u == target:
                    target_sid = s
                    break
            
            if target_sid:
                # Disconnect the user
                socketio.disconnect(target_sid)
                # Clean up votekick
                del votekicks[target]
                emit('message', {'msg': f"{target} has been kicked from the chat."}, broadcast=True)
    # Handle voteskip command
    elif msg == '/voteskip':
        if not video_queue:  # No video playing
            emit('message', {'msg': "No video is currently playing."}, room=sid)
            return
            
        if sid in voteskips:
            emit('message', {'msg': "You have already voted to skip."}, room=sid)
            return
            
        voteskips.add(sid)
        total_users = len(users)
        required_votes = max(2, int(total_users * 0.3))  # At least 2 votes or 30% of users
        current_votes = len(voteskips)
        
        if current_votes >= required_votes:
            # Skip the current video
            if video_queue:
                next_video = video_queue.pop(0)
                emit('play_next_video', next_video, broadcast=True)
                emit('queue_update', {'queue': video_queue}, broadcast=True)
                emit('message', {'msg': f"Video skipped! Now playing: {next_video['title']}"}, broadcast=True)
            voteskips.clear()  # Reset votes
        else:
            votes_needed = required_votes - current_votes
            emit('message', {'msg': f"Voteskip: {current_votes}/{required_votes} votes. {votes_needed} more votes needed to skip."}, broadcast=True)
    else:
        print(f"[MESSAGE] {username}: {msg}")
        emit('message', {'msg': f"{username}: {msg}"}, broadcast=True)

@socketio.on('refresh_user_list')
def refresh_user_list():
    sid = request.sid
    emit('update_user_list', list(users.values()), room=sid)

@socketio.on('add_to_queue')
def handle_add_to_queue(data):
    video_data = {
        'url': data['url'],
        'title': data['title'],
        'duration': data['duration'],
        'added_by': users.get(request.sid, "Anon")
    }
    video_queue.append(video_data)
    emit('queue_update', {'queue': video_queue}, broadcast=True)
    emit('message', {'msg': f"{video_data['added_by']} added a video to the queue."}, broadcast=True)

@socketio.on('remove_from_queue')
def handle_remove_from_queue(data):
    index = data.get('index')
    if 0 <= index < len(video_queue):
        removed_video = video_queue.pop(index)
        emit('queue_update', {'queue': video_queue}, broadcast=True)
        emit('message', {'msg': f"{users.get(request.sid, 'Anon')} removed a video from the queue."}, broadcast=True)

@socketio.on('video_ended')
def handle_video_ended():
    if video_queue:
        next_video = video_queue.pop(0)
        emit('play_next_video', next_video, broadcast=True)
        emit('queue_update', {'queue': video_queue}, broadcast=True)
        emit('message', {'msg': f"Now playing: {next_video['title']}"}, broadcast=True)
    voteskips.clear()  # Reset voteskips when video ends naturally

@socketio.on('sync_video')
def handle_sync_video(data):
    emit('sync_video', data, broadcast=True)

# Add forceskip command handler
def forceskip():
    """Force skip the current video and play the next one in queue."""
    if video_queue:
        next_video = video_queue.pop(0)
        socketio.emit('play_next_video', next_video, broadcast=True)
        socketio.emit('queue_update', {'queue': video_queue}, broadcast=True)
        socketio.emit('message', {'msg': f"[ADMIN] Video force skipped. Now playing: {next_video['title']}"}, broadcast=True)
        voteskips.clear()  # Reset voteskips
        return True
    return False

# Add command handler for console
@app.cli.command('forceskip')
def forceskip_command():
    """Force skip the current video from the console."""
    if forceskip():
        print("Video force skipped successfully.")
    else:
        print("No videos in queue to skip to.")

if __name__ == '__main__':
    socketio.run(app, debug=True)