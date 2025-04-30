document.addEventListener('DOMContentLoaded', () => {
    let socket;
    let username = '';

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

    let showingAllUsers = false;

    function addMessage(msg) {
        const item = document.createElement('li');
        const now = new Date();
        const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        item.textContent = `[${timeStr}] ${msg}`;
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
    }

    rerollButton.addEventListener('click', () => {
        fetchRandomUsername();
    });

    joinButton.addEventListener('click', () => {
        welcomeScreen.style.display = 'none';
        mainLayout.style.display = 'flex';
        inputArea.style.display = 'flex';
        connectSocket();
    });

    sendButton.addEventListener('click', () => {
        const message = messageInput.value.trim();
        if (message) {
            socket.emit('message', { msg: message });
            messageInput.value = '';
            messageInput.focus();
        }
    });

    messageInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            sendButton.click();
            event.preventDefault();
        }
    });

    toggleBtn.addEventListener('click', () => {
        showingAllUsers = !showingAllUsers;
        if (socket) {
            socket.emit('refresh_user_list');
        }
    });

    fetchRandomUsername();
});