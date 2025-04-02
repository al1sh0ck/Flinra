import os

import pymongo
from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify, send_from_directory
from flask_pymongo import PyMongo
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
from bson import ObjectId
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Database configuration
app.config["MONGO_URI"] = "mongodb+srv://al1sh0ck:az0990za@flinra.ksrqb.mongodb.net/flinra"
mongo = PyMongo(app)
socketio = SocketIO(app, cors_allowed_origins="*")

UPLOAD_FOLDER = 'static/uploads'  # Папка, куда сохраняются файлы
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt', 'zip'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def json_serializable(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, datetime.datetime):
        return obj.isoformat()  # Преобразуем datetime в ISO 8601 строку
    raise TypeError(f"Type {type(obj)} not serializable")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash("Please sign in first", "warning")
            return redirect(url_for('signin'))
        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('main'))
    return render_template('signin.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)

        file_url = f'/static/uploads/{filename}'

        return jsonify({'success': True, 'filename': filename, 'url': file_url})

    return jsonify({'error': 'File type not allowed'}), 400




@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    username = session['username']
    user = mongo.db.users.find_one({'username': username})

    if request.method == 'POST':
        name = request.form.get('name')
        new_username = request.form.get('username')
        phone = request.form.get('phone')

        # Обновляем пользователя
        mongo.db.users.update_one({'username': username}, {
            '$set': {
                'name': name,
                'username': new_username,
                'phone': phone
            }
        })

        # Обновим сессию, если username изменился
        session['username'] = new_username

        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)



@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username')
        phone = request.form.get('phone')
        avatar_url = request.form.get('avatar_url') or '/static/default-avatar.png'
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
            'created_at': datetime.utcnow(),
            'online': False
        }
        mongo.db.users.insert_one(user_data)
        flash("Account created successfully! Please sign in.", "success")
        return redirect(url_for('signin'))
    return render_template('signup.html')


@app.route('/edit_group/<group_id>', methods=['GET', 'POST'])
@login_required
def edit_group(group_id):
    group = mongo.db.groups.find_one({'_id': ObjectId(group_id)})

    if not group or session['username'] not in group['members']:
        return "Access denied", 403

    if request.method == 'POST':
        new_name = request.form.get('name')
        new_description = request.form.get('description')
        new_members = request.form.get('members').split(',')

        # Удалим пустые пробелы и дубликаты
        cleaned_members = list(set([m.strip() for m in new_members if m.strip()] + group['members']))

        mongo.db.groups.update_one({'_id': ObjectId(group_id)}, {
            '$set': {
                'name': new_name,
                'description': new_description,
                'members': cleaned_members
            }
        })

        return redirect(url_for('main'))

    return render_template('edit_group.html', group=group)


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = mongo.db.users.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            session['username'] = user['username']
            session['name'] = user['name']
            session['avatar_url'] = user['avatar_url']
            mongo.db.users.update_one({'username': username}, {'$set': {'online': True}})
            flash("Successfully signed in!", "success")
            return redirect(url_for('main'))
        else:
            flash("Invalid username or password", "danger")
            return redirect(url_for('signin'))
    return render_template('signin.html')


@app.route('/main')
@login_required
def main():
        # Получаем чаты и группы, в которых текущий пользователь является участником
        chats = list(mongo.db.chats.find({
            'participants': session['username']
        }))

        groups = list(mongo.db.groups.find({
            'members': session['username']
        }))

        # Подготавливаем данные чатов с последними сообщениями и аватарами
        chat_list = []
        for chat in chats:
            other_user = [u for u in chat['participants'] if u != session['username']][0]
            user_data = mongo.db.users.find_one({'username': other_user})

            last_message_cursor = mongo.db.messages.find({
                '$or': [
                    {'sender': session['username'], 'recipient': other_user},
                    {'sender': other_user, 'recipient': session['username']}
                ]
            }).sort('timestamp', -1).limit(1)

            last_message = list(last_message_cursor)  # Преобразуем Cursor в список для удобства работы

            # Проверяем наличие avatar_url в session
            avatar_url = session.get('avatar_url', '/static/default-avatar.png')  # Путь к аватарке по умолчанию

            chat_data = {
                '_id': str(chat['_id']),
                'name': other_user,
                'avatar_url': avatar_url,
                'last_message': last_message[0]['message'] if last_message else 'No messages yet'
            }
            chat_list.append(chat_data)

        # Подготавливаем данные групп
        group_list = []
        for group in groups:
            last_message_cursor = mongo.db.group_messages.find({
                'group_id': str(group['_id'])
            }).sort('timestamp', -1).limit(1)

            last_message = list(last_message_cursor)  # Преобразуем Cursor в список для удобства работы

            # Проверяем наличие avatar_url в session
            avatar_url = session.get('avatar_url', '/static/group-avatar.png')  # Путь к аватарке по умолчанию

            group_data = {
                '_id': str(group['_id']),
                'name': group['name'],
                'avatar_url': avatar_url,
                'last_message': last_message[0]['message'] if last_message else 'No messages yet'
            }
            group_list.append(group_data)

        return render_template('main.html',
                               username=session['username'],
                               name=session['name'],
                               avatar_url=session.get('avatar_url', '/static/default-avatar.png'),  # Проверка тут тоже
                               chats=chat_list,
                               groups=group_list)
@app.route('/signout')
def signout():
    if 'username' in session:
        mongo.db.users.update_one({'username': session['username']}, {'$set': {'online': False}})
    session.clear()
    flash("Signed out successfully", "info")
    return redirect(url_for('signin'))


@app.route('/api/create_chat', methods=['POST'])
@login_required
def api_create_chat():
    data = request.get_json()
    username = data.get('username')
    first_message = data.get('message')

    if not username:
        return jsonify({"error": "Username is required"}), 400

    if username == session['username']:
        return jsonify({"error": "Cannot create chat with yourself"}), 400

    if not mongo.db.users.find_one({'username': username}):
        return jsonify({"error": "User not found"}), 404

    # Check if chat already exists
    participants = sorted([session['username'], username])
    existing_chat = mongo.db.chats.find_one({'participants': participants})
    if existing_chat:
        return jsonify({"error": "Chat already exists"}), 400

    # Create new chat
    chat_data = {
        'participants': participants,
        'created_at': datetime.utcnow()
    }
    chat_id = mongo.db.chats.insert_one(chat_data).inserted_id

    # Send first message if provided
    if first_message:
        message_data = {
            'sender': session['username'],
            'recipient': username,
            'message': first_message,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'chat_id': str(chat_id)  # Преобразуем ObjectId в строку
        }
        mongo.db.messages.insert_one(message_data)
        socketio.emit('new_message', {
            'sender': message_data['sender'],
            'recipient': message_data['recipient'],
            'message': message_data['message'],
            'timestamp': message_data['timestamp'],
            'chat_id': str(chat_id)  # Преобразуем chat_id в строку
        }, room=username)

    return jsonify({
        "success": True,
        "chat_id": str(chat_id),  # Преобразуем ObjectId в строку
        "name": username
    }), 201



@app.route('/api/create_group', methods=['POST'])
@login_required
def api_create_group():
    data = request.get_json()
    group_name = data.get('name')
    members = data.get('members', '').split(',')
    first_message = data.get('message')

    if not group_name:
        return jsonify({"error": "Group name is required"}), 400

    if len(members) < 1:
        return jsonify({"error": "At least one member required"}), 400

    # Clean members list
    members = [m.strip() for m in members if m.strip()]
    members.append(session['username'])  # Add creator to members

    # Check if all members exist
    for member in members:
        if not mongo.db.users.find_one({'username': member}):
            return jsonify({"error": f"User {member} not found"}), 404

    # Create group
    group_data = {
        'name': group_name,
        'members': members,
        'created_by': session['username'],
        'created_at': datetime.utcnow()
    }
    group_id = mongo.db.groups.insert_one(group_data).inserted_id

    # Send first message if provided
    if first_message:
        message_data = {
            'sender': session['username'],
            'group_id': str(group_id),  # Строка, не ObjectId
            'message': first_message,
            'timestamp': datetime.utcnow()  # Лучше сохранить как datetime
        }
        mongo.db.group_messages.insert_one({
            **message_data,
            'group_id': group_id  # тут можно как ObjectId
        })

        # Отправляем клиенту — только сериализуемое
        socketio.emit('new_group_message', {
            **message_data,
            'timestamp': message_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')  # строка
        }, room=str(group_id))

    return jsonify({
        "success": True,
        "group_id": str(group_id),
        "name": group_name
    }), 201


# В функции api_get_messages
@app.route('/api/get_messages/<chat_id>')
@login_required
def api_get_messages(chat_id):
    try:
        chat = mongo.db.chats.find_one({'_id': ObjectId(chat_id)})
        if not chat or session['username'] not in chat['participants']:
            return jsonify({"error": "Chat not found or access denied"}), 404

        # Определяем собеседника (если групповой чат — можно адаптировать)
        other_user = next((u for u in chat['participants'] if u != session['username']), session['username'])

        # Загружаем сообщения по chat_id (а не только по sender/recipient)
        messages_cursor = mongo.db.messages.find(
            {'chat_id': chat_id}  # без ObjectId
        ).sort('timestamp', pymongo.ASCENDING)

        formatted_messages = []
        for msg in messages_cursor:
            formatted_messages.append({
                'text': msg.get('message', ''),
                'sender': msg.get('sender'),
                'time': datetime.strptime(msg.get('timestamp'), '%Y-%m-%d %H:%M:%S').strftime('%H:%M'),
                'is_current_user': msg.get('sender') == session['username']
            })

        return jsonify({
            "messages": formatted_messages,
            "current_user": session['username'],
            "chat_name": other_user
        })

    except Exception as e:
        print(f"Ошибка в api_get_messages: {e}")
        return jsonify({"error": "Server error"}), 500



# В функции api_send_message
@app.route('/api/send_message/<chat_id>', methods=['POST'])
@login_required
def api_send_message(chat_id):
    data = request.get_json()
    message_text = data.get('text')

    if not message_text:
        return jsonify({"error": "Message text is required"}), 400

    # Преобразуем chat_id в строку для MongoDB запроса
    chat = mongo.db.chats.find_one({'_id': ObjectId(chat_id)})
    if not chat or session['username'] not in chat['participants']:
        return jsonify({"error": "Chat not found or access denied"}), 404

    other_user = [u for u in chat['participants'] if u != session['username']][0]

    message_data = {
        'sender': session['username'],
        'recipient': other_user,
        'message': message_text,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'chat_id': str(chat['_id'])  # Преобразуем ObjectId в строку
    }

    # Вставляем сообщение в базу данных
    mongo.db.messages.insert_one(message_data)

    # Отправляем сообщение по сокетам
    socketio.emit('new_message', {
        'sender': message_data['sender'],
        'recipient': message_data['recipient'],
        'message': message_data['message'],
        'timestamp': message_data['timestamp'],
        'chat_id': str(message_data['chat_id'])  # Преобразуем chat_id в строку
    }, room=other_user)

    return jsonify({
        "success": True,
        "message": {
            'text': message_text,
            'sender': session['username'],
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_current_user': True
        }
    }), 201


from bson import ObjectId

@app.route('/api/send_group_message/<group_id>', methods=['POST'])
@login_required
def api_send_group_message(group_id):
    try:
        # Получаем данные из запроса
        data = request.get_json()
        message_text = data.get('text')

        if not message_text:
            return jsonify({"error": "Message text is required"}), 400

        group = mongo.db.groups.find_one({'_id': ObjectId(group_id)})
        if not group or session['username'] not in group['members']:
            return jsonify({"error": "Group not found or access denied"}), 404

        # Сохраняем сообщение в коллекции group_messages
        timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message_data = {
            'sender': session['username'],
            'group_id': group_id,
            'message': message_text,
            'timestamp': timestamp_str,
        }
        mongo.db.group_messages.insert_one(message_data)

        # Эмитим событие для обновления всех участников
        socketio.emit('new_group_message', {
            'sender': message_data['sender'],
            'group_id': str(group_id),  # Преобразуем group_id в строку
            'message': message_data['message'],
            'timestamp': message_data['timestamp']
        }, room=str(group_id))  # Преобразуем group_id в строку для socketio

        return jsonify({
            "success": True,
            "message": {
                'text': message_text,
                'sender': session['username'],
                'time': timestamp_str,
                'is_current_user': True,
                'group_id': str(group_id)  # Преобразуем group_id в строку
            }
        })

    except Exception as e:
        print(f"Error in api_send_group_message: {e}")
        return jsonify({"error": "Server error"}), 500





@app.route('/api/get_group_messages/<group_id>')
@login_required
def api_get_group_messages(group_id):
    try:
        group = mongo.db.groups.find_one({'_id': ObjectId(group_id)})
        if not group or session['username'] not in group['members']:
            return jsonify({"error": "Group not found or access denied"}), 404

        # Получаем сообщения группы по group_id
        messages_cursor = mongo.db.group_messages.find(
            {'group_id': group_id}
        ).sort('timestamp', pymongo.ASCENDING)

        formatted_messages = []
        for msg in messages_cursor:
            timestamp = msg.get('timestamp')
            if isinstance(timestamp, str):
                time_display = timestamp.split(' ')[1][:5]  # hh:mm
            else:
                time_display = timestamp.strftime('%H:%M')

            formatted_messages.append({
                'text': msg.get('message', ''),
                'sender': msg.get('sender'),
                'time': time_display,
                'is_current_user': msg.get('sender') == session['username']
            })

        return jsonify({
            "messages": formatted_messages,
            "current_user": session['username'],
            "group_name": group['name']
        })

    except Exception as e:
        print(f"Ошибка в api_get_group_messages: {e}")
        return jsonify({"error": "Server error"}), 500



@socketio.on('connect')
def handle_connect():
    if 'username' in session:
        join_room(session['username'])
        emit('connection_status', {'status': 'connected'})


@socketio.on('disconnect')
def handle_disconnect(sid=None):
    if 'username' in session:
        leave_room(session['username'])
        mongo.db.users.update_one(
            {'username': session['username']},
            {'$set': {'online': False, 'last_seen': datetime.utcnow()}}
        )


@socketio.on('join_chat')
def handle_join_chat(data):
    chat_id = data.get('chat_id')
    if chat_id and 'username' in session:
        join_room(chat_id)


if __name__ == '__main__':
    socketio.run(app, debug=True)