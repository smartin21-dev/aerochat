document.addEventListener('DOMContentLoaded', () => {
    // Connect to the Socket.IO server. 
    // The 'autoConnect: false' option prevents connection on load.
    // We will connect manually later if needed, or Socket.IO will connect automatically.
    const socket = io(); 

    const messages = document.getElementById('messages');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const wordCountDisplay = document.getElementById('word-count');

    // Function to add a message to the chat window
    function addMessage(msg) {
        const item = document.createElement('li');
        item.textContent = msg;
        messages.appendChild(item);
        // Scroll to the bottom
        messages.scrollTop = messages.scrollHeight;
    }

    // Handle incoming messages from the server
    socket.on('message', (data) => {
        addMessage(data.msg);
    });

    // Show notices (e.g., word limit errors or votekick updates)
    socket.on('notice', (data) => {
        addMessage(`[Server]: ${data.msg}`);
    });

    // Update user count from server
    socket.on('user_count', (data) => {
        const userCountDiv = document.getElementById('user-count');
        userCountDiv.textContent = `Users Online: ${data.count}`;
    });

    // Send message when send button is clicked
    sendButton.addEventListener('click', () => {
        const message = messageInput.value.trim();
        if (message) {
            socket.emit('message', { msg: message });
            messageInput.value = '';
            messageInput.focus();
            wordCountDisplay.textContent = '0 / 500 characters'; // Reset character count
        }
    });

    // Send message when Enter key is pressed in the input field
    messageInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            sendButton.click(); // Trigger the send button click event
            event.preventDefault(); // Prevent default form submission or line break
        }
    });

    // Live update character count and block input at 500 chars
    messageInput.addEventListener('input', () => {
        let charCount = messageInput.value.length;
        if (charCount > 500) {
            messageInput.value = messageInput.value.slice(0, 500); // Trim excess
            charCount = 500;
        }
        wordCountDisplay.textContent = `${charCount} / 500 characters`;
    });

    // Optional: Handle connection and disconnection events for debugging or UI feedback
    socket.on('connect', () => {
        console.log('Connected to server', socket.id);
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from server');
    });
});
