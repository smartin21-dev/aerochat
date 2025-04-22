import os # Add this import
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

# Get the absolute path of the directory the script is in
basedir = os.path.abspath(os.path.dirname(__file__))
# Construct absolute paths for template and static folders
template_folder = os.path.join(basedir, '..', 'client')
static_folder = os.path.join(basedir, '..', 'client')

app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
app.config['SECRET_KEY'] = 'secret!' # Replace with a real secret key in production
socketio = SocketIO(app)

@app.route('/')
def index():
    # We'll serve the main index.html from the client folder
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print('Client connected:', request.sid)
    emit('message', {'msg': 'Welcome!'}) # Send a welcome message to the connected client

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected:', request.sid)

@socketio.on('message')
def handle_message(data):
    print('Received message:', data)
    # Broadcast the received message to all clients
    emit('message', {'msg': f"{request.sid[:5]}: {data['msg']}"}, broadcast=True)

if __name__ == '__main__':
    # Use socketio.run for development server
    socketio.run(app, debug=True) 