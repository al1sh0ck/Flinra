document.querySelector('.menu-btn').addEventListener('click', function() {
    const navMenu = document.querySelector('.nav-menu');
    navMenu.classList.toggle('hidden');
    navMenu.style.display = navMenu.style.display === 'flex' ? 'none' : 'flex';
});

document.addEventListener('DOMContentLoaded', function () {
    // Получаем кнопки и модальные окна
    const createChatButton = document.getElementById('create-chat-button');
    const createGroupButton = document.getElementById('create-group-button');
    const createChatModal = document.getElementById('create-chat-modal');
    const createGroupModal = document.getElementById('create-group-modal');
    const closeModals = document.querySelectorAll('.close-modal');

    // Открытие модального окна для создания чата
    createChatButton.addEventListener('click', () => {
        console.log('Открытие модального окна для чата');
        createChatModal.classList.remove('hidden'); // Убираем класс, который скрывает окно
        createGroupModal.classList.add('hidden');   // Закрываем окно группы, если оно было открыто
    });

    // Открытие модального окна для создания группы
    createGroupButton.addEventListener('click', () => {
        console.log('Открытие модального окна для группы');
        createGroupModal.classList.remove('hidden'); // Убираем класс, который скрывает окно
        createChatModal.classList.add('hidden');      // Закрываем окно чата, если оно было открыто
    });

    // Закрытие модальных окон
    closeModals.forEach(closeBtn => {
        closeBtn.addEventListener('click', () => {
            closeBtn.closest('.modal').classList.add('hidden'); // Скрываем окно
        });
    });

    // Закрытие модальных окон при клике за пределами окна
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            e.target.classList.add('hidden'); // Закрываем окно при клике за пределами
        }
    });
});
