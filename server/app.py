import os # Add this import
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, disconnect

# Get the absolute path of the directory the script is in
basedir = os.path.abspath(os.path.dirname(__file__))
# Construct absolute paths for template and static folders
template_folder = os.path.join(basedir, '..', 'client')
static_folder = os.path.join(basedir, '..', 'client')

app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
app.config['SECRET_KEY'] = 'secret!' # Replace with a real secret key in production
socketio = SocketIO(app)

# Track connected users and handle vote-kick and word limit
usernames = {}  # sid -> username (placeholder until teammate sets real ones)
votes = {}      # target_username -> set of voter names

def emit_user_count():
    count = len(usernames)
    socketio.emit('user_count', {'count': count})

@app.route('/')
def index():
    # We'll serve the main index.html from the client folder
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    usernames[request.sid] = request.sid[:5]  # Temporary username until Dom adds his part on my end
    emit_user_count()
    print('Client connected:', request.sid)
    emit('message', {'msg': 'Welcome!'}) # Send a welcome message to the connected client

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in usernames:
        del usernames[request.sid]
    emit_user_count()
    print('Client disconnected:', request.sid)

@socketio.on('message')
def handle_message(data):
    sid = request.sid
    msg = data.get('msg', '').strip()
    sender = usernames.get(sid, sid[:5])

    # Enforce 500-word limit
    if len(msg.split()) > 500:
        emit('notice', {'msg': 'Message too long. Limit is 500 words.'})
        return

    # Handle vote to kick command
    if msg.startswith('/votekick '):
        target = msg.split(' ', 1)[1].strip()
        if target == sender:
            emit('notice', {'msg': "You can't vote to kick yourself."})
            return
        if target not in usernames.values():
            emit('notice', {'msg': f"User '{target}' not found."})
            return
        votes.setdefault(target, set()).add(sender)
        vote_count = len(votes[target])
        socketio.emit('notice', {'msg': f"{sender} voted to kick {target} ({vote_count}/3)"})
        if vote_count >= 3:
            for s, name in usernames.items():
                if name == target:
                    socketio.emit('notice', {'msg': f"{target} has been kicked from the chat."})
                    socketio.disconnect(s)
                    break
            votes.pop(target, None)
        return

    print('Received message:', data)
    # Broadcast the received message to all clients
    emit('message', {'msg': f"{sender}: {msg}"}, broadcast=True)

if __name__ == '__main__':
    # Use socketio.run for development server
    socketio.run(app, debug=True)
