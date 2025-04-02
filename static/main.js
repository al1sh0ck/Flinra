document.addEventListener('DOMContentLoaded', function() {
    // Connect to Socket.IO
    const socket = io();

    // DOM Elements
    const menuBtn = document.getElementById('toggle-nav-menu');
    const editGroupBtn = document.getElementById('editGroupBtn');
    const navMenu = document.getElementById('nav-menu');
    const createChatBtn = document.getElementById('create-chat-button');
    const createGroupBtn = document.getElementById('create-group-button');
    const chatItems = document.querySelectorAll('.chat-item');
    const chatWindow = document.getElementById('chat-window');
    const welcomeScreen = document.getElementById('welcome-screen');
    const chatMessages = document.getElementById('chat-messages');
    const messageInput = document.getElementById('message-input');
    const sendMessageBtn = document.getElementById('send-message');

    // Modal Elements
    const createChatModal = document.getElementById('create-chat-modal');
    const createGroupModal = document.getElementById('create-group-modal');
    const closeModalBtns = document.querySelectorAll('.close-modal');
    const createChatConfirm = document.getElementById('create-chat-confirm');
    const createGroupConfirm = document.getElementById('create-group-confirm');

    // Current chat state
    let currentChatId = null;
    let currentChatType = null; // 'chat' or 'group'

    // Toggle menu
    menuBtn.addEventListener('click', () => {
    if (navMenu.classList.contains('hidden')) {
        navMenu.classList.remove('hidden');
    } else {
        navMenu.classList.add('hidden');
    }
});

    // Close menu when clicking on links
    document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', () => {
        navMenu.classList.add('hidden');
    });
});

    // Open create chat modal
    createChatBtn.addEventListener('click', () => {
        createChatModal.classList.remove('hidden');
        createGroupModal.classList.add('hidden');
    });

    // Open create group modal
    createGroupBtn.addEventListener('click', () => {
        createGroupModal.classList.remove('hidden');
        createChatModal.classList.add('hidden');
    });

    // Close modals
    closeModalBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            btn.closest('.modal').classList.add('hidden');
        });
    });

    // Close modal when clicking outside
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            e.target.classList.add('hidden');
        }
    });

    // Create new chat
    createChatConfirm.addEventListener('click', () => {
        const username = document.getElementById('chat-username').value.trim();
        const message = document.getElementById('chat-first-message').value.trim();

        if (!username) {
            alert('Please enter a username');
            return;
        }

        fetch('/api/create_chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                message: message
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }

            // Add new chat to the list
            const chatItem = createChatItem({
                _id: data.chat_id,
                name: data.name,
                avatar_url: '/static/default-avatar.png',
                last_message: message || 'No messages yet'
            });

            document.getElementById('chats-container').prepend(chatItem);
            createChatModal.classList.add('hidden');

            // Clear inputs
            document.getElementById('chat-username').value = '';
            document.getElementById('chat-first-message').value = '';
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to create chat');
        });
    });

    // Create new group
    createGroupConfirm.addEventListener('click', () => {
        const groupName = document.getElementById('group-name').value.trim();
        const raw = document.getElementById('group-members').value.trim();
        const membersList = raw.split(',').map(u=>u.trim());
        const message = document.getElementById('group-first-message').value.trim();

        if (!groupName) {
            alert('Please enter a group name');
            return;
        }

        if (membersList.length === 0 || !raw) {
            alert('Please enter at least one member');
            return;
        }

        fetch('/api/create_group', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
  name: groupName,
  members: membersList.join(','),   // or just members: raw   // ← теперь строка "user1,user2"
  message: message
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }

            // Add new group to the list
            const groupItem = createChatItem({
                _id: data.group_id,
                name: data.name,
                avatar_url: '/static/group-avatar.png',
                last_message: message || 'No messages yet'
            }, 'group');

            document.getElementById('groups-container').prepend(groupItem);
            createGroupModal.classList.add('hidden');

            // Clear inputs
            document.getElementById('group-name').value = '';
            document.getElementById('group-members').value = '';
            document.getElementById('group-first-message').value = '';
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to create group');
        });
    });

    // Load chat when clicking on a chat item
    document.addEventListener('click', (e) => {
        const chatItem = e.target.closest('.chat-item');
        if (chatItem) {
            const chatId = chatItem.dataset.chatId || chatItem.dataset.groupId;
            const isGroup = !!chatItem.dataset.groupId;

            if (isGroup) {
                loadGroupChat(chatId);
            } else {
                loadPrivateChat(chatId);
            }
        }
    });

    // Send message
    sendMessageBtn.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    const attachFileBtn = document.getElementById('attachFileBtn');
const fileInput = document.getElementById('fileInput');
const fileList = document.getElementById('fileList');

// Множественный выбор файлов
fileInput.setAttribute('multiple', true);

// При нажатии — открываем диалог выбора
attachFileBtn.addEventListener('click', () => {
    fileInput.click();
});

// После выбора файлов
fileInput.addEventListener('change', () => {
    const files = fileInput.files;
    fileList.innerHTML = '';

    for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);

        const listItem = document.createElement('div');
        listItem.textContent = `📎 ${file.name} (${Math.round(file.size / 1024)} KB)`;
        fileList.appendChild(listItem);

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                const message = `<a href="${data.url}" target="_blank">${data.filename}</a>`;

                // Отправка файла как сообщение — с учётом типа чата
                const endpoint = currentChatType === 'group'
                    ? `/api/send_group_message/${currentChatId}`
                    : `/api/send_message/${currentChatId}`;

                fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: message })
                })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        addMessageToChat(data.message, true);
                    } else {
                        alert('Ошибка отправки файла как сообщения!');
                    }
                });
            } else {
                alert('Ошибка загрузки файла: ' + data.error);
            }
        })
        .catch(err => {
            console.error('Ошибка отправки:', err);
            alert('Ошибка загрузки файла!');
        });
    }
});



if (editGroupBtn) {
    console.log('Кнопка найдена');
    editGroupBtn.addEventListener('click', () => {
        window.location.href = `/edit_group/${currentChatId}`;
    });
} else {
    console.error('Кнопка не найдена!');
}



    // Socket.IO events
    socket.on('new_message', (data) => {
        if (currentChatId === data.chat_id && currentChatType === 'chat') {
            addMessageToChat(data, false);
        }
    });

    socket.on('new_group_message', (data) => {
        if (currentChatId === data.group_id && currentChatType === 'group') {
            addMessageToChat(data, false);
        }
    });

    // Helper functions
    function loadPrivateChat(chatId) {
        console.log(`Loading private chat with ID: ${chatId}`); // Логирование ID чата
    fetch(`/api/get_messages/${chatId}`)
        .then(response => response.json())
        .then(data => {
            console.log('API Response:', data); // Логируем весь ответ от сервера

            if (!data || !Array.isArray(data.messages)) {
                console.error('Invalid data structure:', data);
                alert('Failed to load messages');
                return;
            }

            currentChatId = chatId;
            currentChatType = 'chat';

            // Update UI
            welcomeScreen.classList.add('hidden');
            chatWindow.classList.remove('hidden');
            document.getElementById('chat-title').textContent = data.chat_name;

            // Load messages
            chatMessages.innerHTML = '';
            data.messages.forEach(msg => {
                console.log('Message:', msg); // Логируем каждое сообщение
                addMessageToChat(msg, msg.is_current_user);
            });

            // Scroll to bottom
            chatMessages.scrollTop = chatMessages.scrollHeight;

            // Join chat room
            socket.emit('join_chat', { chat_id: chatId });
        })
        .catch(error => {
            console.error('Error loading chat:', error);
            alert('Failed to load chat');
        });
}

    function loadGroupChat(groupId) {
    console.log(`Loading group chat with ID: ${groupId}`);

    fetch(`/api/get_group_messages/${groupId}`)
        .then(response => response.json())
        .then(data => {
            console.log('API Response:', data);

            if (!data || !Array.isArray(data.messages)) {
                console.error('Invalid data structure:', data);
                alert('Failed to load group messages');
                return;
            }

            currentChatId = groupId;
            currentChatType = 'group';

            // Update UI
            welcomeScreen.classList.add('hidden');
            chatWindow.classList.remove('hidden');
            document.getElementById('chat-title').textContent = data.group_name;

            // Load messages
            chatMessages.innerHTML = '';
            data.messages.forEach(msg => {
                console.log('Group Message:', msg);
                addMessageToChat(msg, msg.is_current_user);
            });

            // Scroll to bottom
            chatMessages.scrollTop = chatMessages.scrollHeight;

            // Join group room
            socket.emit('join_group', { group_id: groupId });
        })
        .catch(error => {
            console.error('Error loading group chat:', error);
            alert('Failed to load group chat');
        });
}

    function addMessageToChat(message, isCurrentUser) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message ' + (isCurrentUser ? 'self' : 'other');

        messageDiv.innerHTML = `
            <div class="message-content">${message.text}</div>
            <div class="message-time">${message.time}</div>
        `;

        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function sendMessage() {
        const text = messageInput.value.trim();
        if (!text || !currentChatId) return;

        if (currentChatType === 'chat') {
            fetch(`/api/send_message/${currentChatId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({text})
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        addMessageToChat(data.message, true);
                        messageInput.value = '';
                    } else {
                        alert('Failed to send message');
                    }
                })
                .catch(error => {
                    console.error('Error sending message:', error);
                    alert('Failed to send message');
                });
        } else if (currentChatType === 'group') {
            // Отправка сообщения в групповой чат
            fetch(`/api/send_group_message/${currentChatId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({text})
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        addMessageToChat(data.message, true);
                        messageInput.value = '';
                    } else {
                        alert('Failed to send group message');
                    }
                })
                .catch(error => {
                    console.error('Error sending group message:', error);
                    alert('Failed to send group message');
                });
        }
    }

    function createChatItem(chatData, type = 'chat') {
        const chatItem = document.createElement('div');
        chatItem.className = 'chat-item';

        if (type === 'chat') {
            chatItem.dataset.chatId = chatData._id;
        } else {
            chatItem.dataset.groupId = chatData._id;
        }

        chatItem.innerHTML = `
            <img src="${chatData.avatar_url}" alt="Avatar" class="chat-avatar">
            <div class="chat-info">
                <div class="chat-name">${chatData.name}</div>
                <div class="chat-last-message">${chatData.last_message}</div>
            </div>
        `;

        return chatItem;
    }
});
