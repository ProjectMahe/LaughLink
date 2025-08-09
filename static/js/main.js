// Homepage actions: create room or join

async function createRoom(username, rounds=5){
  const res = await fetch('/create_room', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({rounds})
  });
  const data = await res.json();
  if(data.room_id){
    localStorage.setItem('laughlink_username', username);
    location.href = '/room/' + data.room_id;
  }
}

window.addEventListener('DOMContentLoaded', () => {
  const createBtn = document.getElementById('createBtn');
  const joinBtn = document.getElementById('joinBtn');

  createBtn.onclick = () => {
    const username = document.getElementById('username').value.trim() || 'Player' + Math.floor(Math.random()*99);
    createRoom(username);
  }

  joinBtn.onclick = () => {
    const username = document.getElementById('username').value.trim() || 'Player' + Math.floor(Math.random()*99);
    const room = document.getElementById('joinRoomInput').value.trim();
    if(!room) return alert('Enter room code to join');
    localStorage.setItem('laughlink_username', username);
    location.href = '/room/' + room;
  }
});
