document.getElementById('start-button').addEventListener('click', function() {
    const talkingVideoUrl = this.getAttribute('data-talking-video');
    fetch('/start', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            console.log(data);
            document.getElementById('video').src = talkingVideoUrl;
        });
});

document.getElementById('stop-button').addEventListener('click', function() {
    const pauseVideoUrl = this.getAttribute('data-pause-video');
    fetch('/stop', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            console.log(data);
            document.getElementById('video').src = pauseVideoUrl;
        });
});

const socket = io();

socket.on('log', function(data) {
    const logPanel = document.getElementById('log');
    const logMessage = document.createElement('div');
    logMessage.textContent = data.message;
    logPanel.appendChild(logMessage);
    logPanel.scrollTop = logPanel.scrollHeight;
});

socket.on('play_talking_video', function() {
    const talkingVideoUrl = document.getElementById('start-button').getAttribute('data-talking-video');
    document.getElementById('video').src = talkingVideoUrl;
});

socket.on('play_pause_video', function() {
    const pauseVideoUrl = document.getElementById('start-button').getAttribute('data-pause-video');
    document.getElementById('video').src = pauseVideoUrl;
});