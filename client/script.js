document.addEventListener('DOMContentLoaded', () => {
    // Connect to the Socket.IO server. 
    // The 'autoConnect: false' option prevents connection on load.
    // We will connect manually later if needed, or Socket.IO will connect automatically.
    const socket = io(); 

    const messages = document.getElementById('messages');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');

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

    // Send message when send button is clicked
    sendButton.addEventListener('click', () => {
        const message = messageInput.value.trim();
        if (message) {
            socket.emit('message', { msg: message });
            messageInput.value = '';
            messageInput.focus();
        }
    });

    // Send message when Enter key is pressed in the input field
    messageInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            sendButton.click(); // Trigger the send button click event
            event.preventDefault(); // Prevent default form submission or line break
        }
    });

    // Optional: Handle connection and disconnection events for debugging or UI feedback
    socket.on('connect', () => {
        console.log('Connected to server', socket.id);
        // You could add a message to the chat like "You are connected"
        // addMessage('You are connected.');
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from server');
        // You could add a message like "You have been disconnected"
        // addMessage('You have been disconnected.');
    });

}); 