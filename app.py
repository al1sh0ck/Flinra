from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
from flask_pymongo import PyMongo
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Database configuration
app.config["MONGO_URI"] = "mongodb+srv://al1sh0ck:az0990za@flinra.ksrqb.mongodb.net/flinra"
mongo = PyMongo(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Home route
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('main'))
    return render_template('signin.html')

# Sign-up route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username')
        phone = request.form.get('phone')
        avatar_url = request.form.get('avatar_url')
        password = request.form.get('password')

        if mongo.db.users.find_one({'username': username}):
            flash("Username already exists", "danger")
            return redirect(url_for('signup'))

        user_data = {
            'name': name,
            'username': username,
            'phone': phone,
            'avatar_url': avatar_url,
            'password': generate_password_hash(password),
            'created_at': datetime.datetime.utcnow(),
            'online': False
        }
        mongo.db.users.insert_one(user_data)
        flash("Account created successfully! Please sign in.", "success")
        return redirect(url_for('signin'))
    return render_template('signup.html')

# Sign-in route
@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = mongo.db.users.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            session['username'] = user['username']
            session['name'] = user['name']
            mongo.db.users.update_one({'username': username}, {'$set': {'online': True}})
            flash("Successfully signed in!", "success")
            return redirect(url_for('main'))
        else:
            flash("Invalid username or password", "danger")
            return redirect(url_for('signin'))
    return render_template('signin.html')

# Main chat page
@app.route('/main')
def main():
    if 'username' not in session:
        flash("Please sign in first", "warning")
        return redirect(url_for('signin'))

    # Получаем чаты
    chats = list(mongo.db.chats.find({
        'participants': session['username']
    }))

    # Получаем группы
    groups = list(mongo.db.groups.find({
        'members': session['username']
    }))

    return render_template('main.html', username=session['username'], name=session['name'], chats=chats, groups=groups)


# Sign-out route
@app.route('/signout')
def signout():
    if 'username' in session:
        mongo.db.users.update_one({'username': session['username']}, {'$set': {'online': False}})
    session.clear()
    flash("Signed out successfully", "info")
    return redirect(url_for('signin'))


# Create a group
@app.route('/create_group', methods=['POST'])
def create_group():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 403

    group_name = request.form.get('group_name')
    if not group_name:
        return jsonify({"error": "Group name required"}), 400

    if mongo.db.groups.find_one({'name': group_name}):
        return jsonify({"error": "Group name already exists"}), 400

    group_data = {
        'name': group_name,
        'members': [session['username']],
        'created_at': datetime.datetime.utcnow()
    }
    mongo.db.groups.insert_one(group_data)
    return jsonify({"message": "Group created successfully"}), 200


# Create a chat between users
@app.route('/create_chat', methods=['POST'])
def create_chat():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 403

    recipient = request.form.get('recipient')
    if not recipient:
        return jsonify({"error": "Recipient username is required"}), 400

    if not mongo.db.users.find_one({'username': recipient}):
        return jsonify({"error": "Recipient does not exist"}), 404

    chat_data = {
        'participants': sorted([session['username'], recipient]),
        'created_at': datetime.datetime.utcnow()
    }

    if mongo.db.chats.find_one({'participants': chat_data['participants']}):
        return jsonify({"message": "Chat already exists"}), 200

    mongo.db.chats.insert_one(chat_data)
    return jsonify({"message": "Chat created successfully"}), 201


# Send a message
@app.route('/send_message', methods=['POST'])
def send_message():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 403

    recipient = request.form.get('recipient')
    message_text = request.form.get('message')

    if not recipient or not message_text:
        return jsonify({"error": "Recipient and message text required"}), 400

    message_data = {
        'sender': session['username'],
        'recipient': recipient,
        'message': message_text,
        'timestamp': datetime.datetime.utcnow()
    }
    mongo.db.messages.insert_one(message_data)
    socketio.emit('new_message', message_data, room=recipient)
    return jsonify({"message": "Message sent successfully"}), 200

# Get online users
@app.route('/online_users', methods=['GET'])
def online_users():
    users = mongo.db.users.find({'online': True}, {'username': 1, '_id': 0})
    return jsonify([user['username'] for user in users])

# Inbox page
@app.route('/inbox')
def inbox():
    if 'username' not in session:
        flash("Please sign in first", "warning")
        return redirect(url_for('signin'))
    messages = list(mongo.db.messages.find({'recipient': session['username']}))
    return render_template('inbox.html', messages=messages)

# SocketIO event handlers
@socketio.on('join')
def handle_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    emit('user_joined', {'username': username}, room=room)

@socketio.on('leave')
def handle_leave(data):
    username = data['username']
    room = data['room']
    leave_room(room)
    emit('user_left', {'username': username}, room=room)

@socketio.on('send_message')
def handle_send_message(data):
    sender = data['sender']
    recipient = data['recipient']
    message_text = data['message']

    message_data = {
        'sender': sender,
        'recipient': recipient,
        'message': message_text,
        'timestamp': datetime.datetime.utcnow()
    }
    mongo.db.messages.insert_one(message_data)
    emit('new_message', message_data, room=recipient)

# Run the app
if __name__ == '__main__':
    socketio.run(app, debug=True)
