let socket;
let username = localStorage.getItem('laughlink_username') || ('Guest' + Math.floor(Math.random()*999));

function connectSocket(){
  socket = io();

  socket.on('connect', () => {
    socket.emit('join', {username, room: ROOM_ID});
  });

  socket.on('player_list', data => {
    const ul = document.getElementById('playersList');
    ul.innerHTML = '';
    data.players.forEach(p => {
      const li = document.createElement('li'); li.innerText = p; ul.appendChild(li);
    });
  });

  socket.on('round_started', data => {
    document.getElementById('votingArea').style.display = 'none';
    document.getElementById('resultArea').style.display = 'none';
    document.getElementById('captionEntry').style.display = 'block';

    document.getElementById('roundInfo').innerText = `Round ${data.round} / ${data.rounds}`;
    if(data.image){
      document.getElementById('memeImg').src = '/' + data.image.replace('\\\\', '/');
    } else {
      document.getElementById('memeImg').src = '';
    }
  });

  socket.on('voting_start', data => {
    document.getElementById('captionEntry').style.display = 'none';
    const list = document.getElementById('captionsList');
    list.innerHTML = '';
    data.captions.forEach(it => {
      const div = document.createElement('div');
      div.className = 'caption-item';
      const btn = document.createElement('button');
      btn.innerText = 'Vote';
      btn.onclick = () => {
        socket.emit('vote', {room: ROOM_ID, username: it.username});
        // disable buttons after voting
        Array.from(document.querySelectorAll('.caption-item button')).forEach(b => b.disabled = true);
      };
      div.innerHTML = `<strong>${it.username}</strong>: <span>${escapeHtml(it.caption)}</span> `;
      div.appendChild(btn);
      list.appendChild(div);
    });
    document.getElementById('votingArea').style.display = 'block';
  });

  socket.on('round_result', data => {
    document.getElementById('resultArea').style.display = 'block';
    document.getElementById('resultArea').innerHTML = '<h3>Round Results</h3>' +
      '<pre>' + JSON.stringify(data.votes, null, 2) + '</pre>' +
      '<h4>Leaderboard</h4><ol>' + data.leaderboard.map(x => `<li>${x.username} — ${x.score}</li>`).join('') + '</ol>';
  });

  socket.on('game_over', data => {
    alert('Game over! Check scoreboard.');
    location.href = '/scoreboard/' + ROOM_ID;
  });
}

function escapeHtml(text){
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(text));
  return div.innerHTML;
}

window.addEventListener('DOMContentLoaded', () => {
  document.getElementById('startRound').onclick = () => {
    socket.emit('start_round', {room: ROOM_ID});
  }

  document.getElementById('submitCaption').onclick = () => {
    const caption = document.getElementById('captionText').value.trim();
    if(!caption) return alert('Write something funny!');
    socket.emit('submit_caption', {room: ROOM_ID, username, caption});
    document.getElementById('captionText').value = '';
    document.getElementById('captionEntry').style.display = 'none';
  }

  connectSocket();
});
