document.addEventListener('DOMContentLoaded', () => {
    let socket;
    let username = '';
    let player;
    let currentVideo = null;
    let isPlayerReady = false;
    let pendingVideo = null;  // Store video that needs to be played once player is ready
    let messageCooldown = false;
    let cooldownTimer = null;
    let isAdmin = false;

    const welcomeScreen = document.getElementById('welcome-screen');
    const randomUsernameDisplay = document.getElementById('random-username');
    const rerollButton = document.getElementById('reroll-button');
    const joinButton = document.getElementById('join-button');

    const mainLayout = document.getElementById('main-layout');
    const inputArea = document.getElementById('input-area');
    const messages = document.getElementById('messages');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const userList = document.getElementById('users');
    const toggleBtn = document.getElementById('toggle-users');
    const charCounter = document.getElementById('char-counter');

    const videoUrl = document.getElementById('video-url');
    const addToQueueBtn = document.getElementById('add-to-queue');
    const videoQueue = document.getElementById('video-queue');

    let showingAllUsers = false;

    function updateCharCounter() {
        const length = messageInput.value.length;
        charCounter.textContent = `${length}/500`;
        if (length > 450) {
            charCounter.style.color = '#ff4444';
        } else {
            charCounter.style.color = '#666';
        }
    }

    function addMessage(msg) {
        const item = document.createElement('li');
        const now = new Date();
        const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        // Check if message contains an admin username
        if (msg.includes('[ADMIN]')) {
            const parts = msg.split(':');
            if (parts.length > 1) {
                const username = parts[0];
                const message = parts.slice(1).join(':');
                item.innerHTML = `[${timeStr}] <span class="admin-username">${username}</span>:${message}`;
            } else {
                item.innerHTML = `[${timeStr}] <span class="admin-username">${msg}</span>`;
            }
        } else {
            item.textContent = `[${timeStr}] ${msg}`;
        }
        
        messages.appendChild(item);
        messages.scrollTop = messages.scrollHeight;
    }

    function fetchRandomUsername() {
        fetch('/random_username')
            .then(response => response.json())
            .then(data => {
                username = data.username;
                randomUsernameDisplay.textContent = username;
            })
            .catch(err => {
                console.error('Failed to fetch random username:', err);
            });
    }

    function connectSocket() {
        socket = io();

        socket.emit('set_username', { username: username });

        socket.on('assign_username', (data) => {
            console.log('Assigned username:', data.username);
            isAdmin = data.is_admin;
            if (isAdmin) {
                addMessage('You are the administrator. Available commands: /forceskip, /clearqueue');
            }
        });

        socket.on('message', (data) => {
            addMessage(data.msg);
        });

        socket.on('update_user_list', (userListArray) => {
            userList.innerHTML = '';
            const visibleLimit = 5;
            const toShow = showingAllUsers ? userListArray : userListArray.slice(0, visibleLimit);

            toShow.forEach(username => {
                const li = document.createElement('li');
                li.textContent = username;
                userList.appendChild(li);
            });

            if (userListArray.length > visibleLimit) {
                toggleBtn.style.display = 'block';
                toggleBtn.textContent = showingAllUsers ? 'Show Less' : 'Show All';
            } else {
                toggleBtn.style.display = 'none';
            }
        });

        socket.on('connect', () => {
            console.log('Connected to server', socket.id);
        });

        socket.on('disconnect', () => {
            console.log('Disconnected from server');
        });

        socket.on('queue_update', (data) => {
            updateQueueDisplay(data.queue);
        });

        socket.on('play_next_video', (video) => {
            console.log('Received play_next_video event:', video);
            currentVideo = video;
            playVideo(video);
        });

        socket.on('sync_video', (data) => {
            if (player && data.videoId) {
                player.seekTo(data.currentTime, true);
            }
        });
    }

    // YouTube Player API
    window.onYouTubeIframeAPIReady = function() {
        console.log('YouTube API Ready');
        initializePlayer();
    };

    function initializePlayer() {
        console.log('Initializing player');
        player = new YT.Player('player', {
            height: '360',
            width: '640',
            videoId: '',
            playerVars: {
                'playsinline': 1,
                'controls': 1,
                'autoplay': 0,  // Changed to 0 to prevent autoplay issues
                'enablejsapi': 1,
                'origin': window.location.origin,
                'rel': 0,  // Disable related videos
                'modestbranding': 1  // Reduce YouTube branding
            },
            events: {
                'onStateChange': onPlayerStateChange,
                'onReady': onPlayerReady,
                'onError': onPlayerError
            }
        });
    }

    function onPlayerReady(event) {
        console.log('Player is ready');
        isPlayerReady = true;
        // Play any pending video
        if (pendingVideo) {
            console.log('Playing pending video:', pendingVideo);
            playVideo(pendingVideo);
            pendingVideo = null;
        }
    }

    function playVideo(video) {
        console.log('Attempting to play video:', video);
        const videoId = extractVideoId(video.url);
        if (videoId) {
            if (isPlayerReady && player && player.loadVideoById) {
                console.log('Player ready, loading video:', videoId);
                try {
                    // First cue the video
                    player.cueVideoById({
                        videoId: videoId,
                        startSeconds: 0,
                        suggestedQuality: 'default'
                    });
                    
                    // Then play it after a short delay to ensure proper loading
                    setTimeout(() => {
                        if (player && player.playVideo) {
                            player.playVideo();
                            console.log('Video play command sent');
                        }
                    }, 1000);
                } catch (error) {
                    console.error('Error loading video:', error);
                }
            } else {
                console.log('Player not ready, storing video for later');
                pendingVideo = video;
            }
        }
    }

    function onPlayerError(event) {
        console.error('Player Error:', event.data);
        addMessage('Error playing video. Please try another one.');
        // Try to play the next video in queue if available
        if (videoQueue.children.length > 0) {
            const nextVideo = videoQueue.children[0];
            const videoData = {
                url: nextVideo.querySelector('.video-title').textContent,
                title: nextVideo.querySelector('.video-title').textContent,
                duration: nextVideo.querySelector('.video-duration').textContent
            };
            playVideo(videoData);
        }
    }

    function onPlayerStateChange(event) {
        console.log('Player State Change:', event.data);
        if (event.data === YT.PlayerState.ENDED) {
            socket.emit('video_ended');
        }
    }

    function extractVideoId(url) {
        const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/;
        const match = url.match(regExp);
        return (match && match[2].length === 11) ? match[2] : null;
    }

    function getVideoTitle(videoId) {
        return new Promise((resolve) => {
            // Try to get title from oEmbed API first (no key required)
            fetch(`https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=${videoId}&format=json`)
                .then(response => response.json())
                .then(data => {
                    resolve(data.title);
                })
                .catch(() => {
                    // Fallback to iframe method if oEmbed fails
                    const iframe = document.createElement('iframe');
                    iframe.style.display = 'none';
                    iframe.src = `https://www.youtube.com/embed/${videoId}`;
                    
                    iframe.onload = () => {
                        try {
                            const title = iframe.contentWindow.document.title;
                            resolve(title.replace(' - YouTube', ''));
                        } catch (e) {
                            resolve('Unknown Title');
                        }
                        document.body.removeChild(iframe);
                    };
                    
                    iframe.onerror = () => {
                        resolve('Unknown Title');
                        document.body.removeChild(iframe);
                    };
                    
                    document.body.appendChild(iframe);
                });
        });
    }

    function formatDuration(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }

    function updateQueueDisplay(queue) {
        videoQueue.innerHTML = '';
        queue.forEach((video, index) => {
            const li = document.createElement('li');
            li.innerHTML = `
                <span class="video-title">${video.title}</span>
                <span class="video-duration">${video.duration}</span>
                <button class="remove-video" data-index="${index}">×</button>
            `;
            videoQueue.appendChild(li);
        });

        document.querySelectorAll('.remove-video').forEach(button => {
            button.addEventListener('click', () => {
                const index = parseInt(button.dataset.index);
                socket.emit('remove_from_queue', { index });
            });
        });
    }

    function updateSendButtonState() {
        if (messageCooldown) {
            sendButton.disabled = true;
            sendButton.style.backgroundColor = '#cccccc';
            messageInput.disabled = true;
            messageInput.style.backgroundColor = '#f5f5f5';
        } else {
            sendButton.disabled = false;
            sendButton.style.backgroundColor = '#3390ec';
            messageInput.disabled = false;
            messageInput.style.backgroundColor = '#ffffff';
        }
    }

    function startCooldown(seconds) {
        messageCooldown = true;
        updateSendButtonState();
        
        let remainingTime = seconds;
        const originalText = sendButton.textContent;
        
        if (cooldownTimer) {
            clearInterval(cooldownTimer);
        }
        
        cooldownTimer = setInterval(() => {
            remainingTime -= 0.1;
            if (remainingTime <= 0) {
                clearInterval(cooldownTimer);
                messageCooldown = false;
                sendButton.textContent = originalText;
                updateSendButtonState();
            } else {
                sendButton.textContent = `Wait ${remainingTime.toFixed(1)}s`;
            }
        }, 100);
    }

    rerollButton.addEventListener('click', () => {
        fetchRandomUsername();
    });

    joinButton.addEventListener('click', () => {
        welcomeScreen.style.display = 'none';
        mainLayout.style.display = 'flex';
        inputArea.style.display = 'flex';
        document.body.classList.add('chat-active');
        connectSocket();
    });

    sendButton.addEventListener('click', () => {
        const message = messageInput.value.trim();
        if (message && !messageCooldown) {
            socket.emit('message', { msg: message });
            messageInput.value = '';
            messageInput.focus();
            startCooldown(3); // Start 3-second cooldown
        }
    });

    messageInput.addEventListener('input', updateCharCounter);

    messageInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter' && !messageCooldown) {
            const message = messageInput.value.trim();
            if (message) {
                socket.emit('message', { msg: message });
                messageInput.value = '';
                messageInput.focus();
                startCooldown(3); // Start 3-second cooldown
            }
            event.preventDefault();
        }
    });

    toggleBtn.addEventListener('click', () => {
        showingAllUsers = !showingAllUsers;
        if (socket) {
            socket.emit('refresh_user_list');
        }
    });

    addToQueueBtn.addEventListener('click', async () => {
        const url = videoUrl.value.trim();
        const videoId = extractVideoId(url);
        
        if (videoId) {
            try {
                const title = await getVideoTitle(videoId);
                const videoData = {
                    url: url,
                    title: title,
                    duration: 'Unknown'
                };
                socket.emit('add_to_queue', videoData);
                videoUrl.value = '';

                // If this is the first video, start playing it
                if (!currentVideo) {
                    console.log('First video added, triggering playback');
                    currentVideo = videoData;
                    playVideo(videoData);
                }
            } catch (error) {
                console.error('Error adding video to queue:', error);
                addMessage('Error adding video to queue');
            }
        } else {
            addMessage('Invalid YouTube URL');
        }
    });

    fetchRandomUsername();
});