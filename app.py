import os
import random
import string
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_socketio import SocketIO, join_room, leave_room, emit

# config
BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, 'database', 'game.db')
IMAGE_DIR = os.path.join('static', 'images')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key-change-me'
socketio = SocketIO(app, cors_allowed_origins='*')

# In-memory rooms state for current games
rooms_state = {}
# rooms_state[room_id] = {
#   'players': {sid: username},
#   'usernames': [username1, ...],
#   'current_round': 0,
#   'round_image': 'static/images/meme1.jpg',
#   'captions': {username: caption},
#   'votes': {caption_id: count},
#}


def get_db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def random_room_code(n=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=n))


def list_images():
    # Return filenames of images inside static/images
    try:
        files = os.listdir(os.path.join(BASE_DIR, IMAGE_DIR))
        images = [os.path.join('static', 'images', f) for f in files if f.lower().endswith(('png', 'jpg', 'jpeg', 'gif'))]
        return images
    except Exception:
        return []


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/room/<room_id>')
def room_page(room_id):
    return render_template('room.html', room_id=room_id)


@app.route('/scoreboard/<room_id>')
def scoreboard(room_id):
    return render_template('scoreboard.html', room_id=room_id)


# API to create new room
@app.route('/create_room', methods=['POST'])
def create_room():
    data = request.json or {}
    rounds = data.get('rounds', 5)
    room_id = random_room_code()

    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute('INSERT OR REPLACE INTO rooms (id, rounds) VALUES (?, ?)', (room_id, rounds))
    conn.commit()
    conn.close()

    # initialize in-memory state
    rooms_state[room_id] = {
        'players': {},
        'usernames': [],
        'current_round': 0,
        'round_image': None,
        'captions': {},
        'votes': {},
        'rounds': rounds
    }

    return jsonify({'room_id': room_id})


@socketio.on('join')
def on_join(data):
    username = data.get('username')
    room = data.get('room')
    sid = request.sid
    if not username or not room:
        return

    join_room(room)
    # create room state if missing
    if room not in rooms_state:
        rooms_state[room] = {
            'players': {},
            'usernames': [],
            'current_round': 0,
            'round_image': None,
            'captions': {},
            'votes': {},
            'rounds': 5
        }

    rooms_state[room]['players'][sid] = username
    if username not in rooms_state[room]['usernames']:
        rooms_state[room]['usernames'].append(username)

    # save player in DB
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute('INSERT INTO players (username, room_id, score) VALUES (?, ?, ?)', (username, room, 0))
    conn.commit()
    conn.close()

    emit('player_list', {'players': rooms_state[room]['usernames']}, room=room)


@socketio.on('start_round')
def on_start_round(data):
    room = data.get('room')
    if room not in rooms_state:
        return

    state = rooms_state[room]
    # increment round
    state['current_round'] += 1
    state['captions'] = {}
    state['votes'] = {}

    images = list_images()
    if not images:
        state['round_image'] = None
    else:
        state['round_image'] = random.choice(images)

    emit('round_started', {
        'round': state['current_round'],
        'image': state['round_image'],
        'rounds': state['rounds']
    }, room=room)


@socketio.on('submit_caption')
def on_submit_caption(data):
    room = data.get('room')
    username = data.get('username')
    caption = data.get('caption')

    if not room or room not in rooms_state:
        return

    state = rooms_state[room]
    state['captions'][username] = caption

    # store into DB (captions table)
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute('INSERT INTO captions (room_id, round, username, caption) VALUES (?, ?, ?, ?)',
                (room, state['current_round'], username, caption))
    conn.commit()
    conn.close()

    # If everyone has submitted, move to voting
    if len(state['captions']) >= len(state['usernames']):
        # prepare list of captions
        items = []
        for u, c in state['captions'].items():
            items.append({'username': u, 'caption': c})
        emit('voting_start', {'captions': items}, room=room)


@socketio.on('vote')
def on_vote(data):
    room = data.get('room')
    voted_for = data.get('username')  # username whose caption got vote

    if not room or room not in rooms_state or not voted_for:
        return

    state = rooms_state[room]
    state['votes'][voted_for] = state['votes'].get(voted_for, 0) + 1

    # once all players vote (simple rule: total votes == number of players)
    if sum(state['votes'].values()) >= len(state['usernames']):
        # update scores in DB and in-memory
        conn = get_db_conn()
        cur = conn.cursor()
        for username, count in state['votes'].items():
            # simple scoring: votes * 10
            points = count * 10
            cur.execute('UPDATE players SET score = score + ? WHERE username = ? AND room_id = ?', (points, username, room))
        conn.commit()
        # fetch updated scoreboard
        cur.execute('SELECT username, score FROM players WHERE room_id = ? ORDER BY score DESC', (room,))
        rows = cur.fetchall()
        conn.close()

        leaderboard = [{'username': r[0], 'score': r[1]} for r in rows]

        # send round result
        emit('round_result', {'votes': state['votes'], 'leaderboard': leaderboard}, room=room)

        # check if game over
        if state['current_round'] >= state['rounds']:
            emit('game_over', {'leaderboard': leaderboard}, room=room)


@socketio.on('leave')
def on_leave(data):
    room = data.get('room')
    sid = request.sid
    if room in rooms_state and sid in rooms_state[room]['players']:
        username = rooms_state[room]['players'].pop(sid)
        try:
            rooms_state[room]['usernames'].remove(username)
        except ValueError:
            pass
        leave_room(room)
        emit('player_list', {'players': rooms_state[room]['usernames']}, room=room)


if __name__ == '__main__':
    os.makedirs(os.path.join(BASE_DIR, 'database'), exist_ok=True)
    # ensure DB exists
    if not os.path.exists(DB_PATH):
        print('Initializing DB... run init_db.py separately if you want control')
    print('Starting LaughLink on http://127.0.0.1:5000')
    socketio.run(app, host='0.0.0.0', port=5000)
