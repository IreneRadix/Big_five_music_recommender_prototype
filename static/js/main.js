const API_BASE = 'http://localhost:5000/api';

// Регистрация
document.getElementById('registerForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    const registerRes = await fetch(`${API_BASE}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password })
    });
    const registerData = await registerRes.json();
    
    if (registerRes.ok) {
        
            localStorage.setItem('user_id', registerData.user_id);
            localStorage.setItem('user_name', username);
            localStorage.setItem('username', username);
            
            // Убедимся, что данные сохранились
            console.log('Сохранено в localStorage:', {
   
                user_id: registerData.user_id,

            });
            
            //alert('Регистрация успешна, пройдите опрос');
            
            window.location.href = '/auth_choice/' + username;//'/survey/' + username;
       
    } else {
        alert(registerData.error);
    }
});

// Вход
document.getElementById('loginForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    const res = await fetch(`${API_BASE}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    if (res.ok) {
        localStorage.setItem('token', data.token);
        localStorage.setItem('user_id', data.user_id);
        window.location.href = '/feed/' + username;
    } else {
        alert(data.error);
    }
});

// Загрузка рекомендаций на главной
async function loadRecommendations() {
    const res = await fetch(`${API_BASE}/recommendations`);
    const tracks = await res.json();
    const container = document.getElementById('recommendations');
    container.innerHTML = tracks.map(track => `
        <div class="track">
            <img src="${track.cover_url}" alt="cover" width="100">
            <div>
                <strong>${track.title}</strong> - ${track.artist}
            </div>
            <button onclick="addToFavorites(${track.id})">❤️ В избранное</button>
            <audio controls src="${track.file_url}"></audio>
        </div>
    `).join('');
}

// Добавление в избранное
async function addToFavorites(trackId, button) {
    const token = localStorage.getItem('token');
    
    if (!token) {
        alert('Войдите, чтобы добавить в избранное');
        return;
    }
    
    const originalText = button.textContent;
    button.textContent = '⏳ Добавление...';
    button.disabled = true;
    
    try {
        const res = await fetch(`${API_BASE}/favorites`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ track_id: trackId })
        });
        
        if (res.ok) {
            // Визуально отмечаем трек как добавленный
            button.innerHTML = '✅ В избранном';
            button.style.opacity = '0.6';
            
            // Находим карточку трека и добавляем анимацию удаления
            const trackCard = button.closest('.track-card');
            if (trackCard) {
                trackCard.style.transition = 'all 0.3s ease';
                trackCard.style.opacity = '0.5';
                trackCard.style.transform = 'translateX(20px)';
                
                // Ждем анимацию, затем удаляем карточку
                setTimeout(() => {
                    trackCard.remove();
                    
                    // Обновляем нумерацию оставшихся треков
                    updateTrackNumbers();
                    
                    // Показываем уведомление
                    showNotification('Трек добавлен в избранное! Рекомендации обновлены');
                    
                    // Загружаем новый трек на место удаленного (без перезагрузки страницы)
                    loadReplacementTrack();
                }, 300);
            } else {
                // Если не нашли карточку, просто перезагружаем рекомендации
                setTimeout(() => {
                    loadRecommendations();
                }, 500);
            }
        } else {
            const data = await res.json();
            alert(data.error || 'Ошибка при добавлении в избранное');
            button.textContent = originalText;
            button.disabled = false;
        }
    } catch (error) {
        console.error('Ошибка:', error);
        alert('Ошибка соединения');
        button.textContent = originalText;
        button.disabled = false;
    }
}

// Функция для обновления нумерации треков
function updateTrackNumbers() {
    const trackCards = document.querySelectorAll('.track-card');
    trackCards.forEach((card, index) => {
        const numberDiv = card.querySelector('.track-number');
        if (numberDiv) {
            numberDiv.textContent = (index + 1).toString();
        }
    });
}

// Функция для загрузки одного трека на место удаленного
async function loadReplacementTrack() {
    const username = getCurrentUsername();
    if (!username) return;
    
    try {
        // Получаем текущие ID треков
        const currentTrackIds = Array.from(document.querySelectorAll('.track-card'))
            .map(card => parseInt(card.dataset.trackId))
            .filter(id => !isNaN(id));
        
        // Запрашиваем новые рекомендации
        const response = await fetch(`${API_BASE}/recommendations/${username}?limit=25`);
        const data = await response.json();
        
        if (data.success && data.recommendations) {
            // Находим трек, которого нет в текущем списке
            const newTrack = data.recommendations.find(track => !currentTrackIds.includes(track.id));
            
            if (newTrack) {
                // Добавляем новый трек в конец списка
                appendTrackToEnd(newTrack, currentTrackIds.length + 1);
                showNotification(`✨ Новый трек: ${newTrack.title} - ${newTrack.artist}`);
            } else {
                // Если нет новых треков, просто показываем сообщение
                showNotification('🎵 Все рекомендации обновлены!', 'info');
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки замены:', error);
    }
}

// Функция для добавления трека в конец списка
function appendTrackToEnd(track, newNumber) {
    const container = document.getElementById('recommendations');
    if (!container) return;
    
    // Находим контейнер с треками (не user-info)
    const tracksContainer = container.querySelector('.recommendations-grid') || container;
    
    const trackHtml = `
        <div class="track-card" data-track-id="${track.id}" style="animation: slideIn 0.5s ease;">
            <div class="track-number">${newNumber}</div>
            <img src="${track.cover_url || '/static/default_cover.jpg'}" 
                 alt="cover" 
                 class="track-cover"
                 onerror="this.src='/static/default_cover.jpg'">
            <div class="track-info">
                <div class="track-title">${escapeHtml(track.title)}</div>
                <div class="track-artist">${escapeHtml(track.artist)}</div>
                ${track.genre ? `<div class="track-genre">🎵 ${track.genre}</div>` : ''}
                <div class="track-reason">💡 ${track.recommendation_reason || 'Рекомендовано для вас'}</div>
            </div>
            <div class="track-actions">
                <button onclick="addToFavorites(${track.id}, this)" class="fav-btn">
                    ❤️ В избранное
                </button>
                <audio controls src="${track.file_url}" class="audio-player" preload="none"></audio>
            </div>
        </div>
    `;
    
    tracksContainer.insertAdjacentHTML('beforeend', trackHtml);
    
    // Добавляем анимацию
    const newCard = tracksContainer.lastElementChild;
    setTimeout(() => {
        if (newCard) newCard.style.animation = '';
    }, 500);
}

// Функция для показа уведомлений
function showNotification(message, type = 'success') {
    // Создаем элемент уведомления
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#4caf50' : '#2196f3'};
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        z-index: 1000;
        animation: slideInRight 0.3s ease;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    `;
    
    document.body.appendChild(notification);
    
    // Удаляем через 3 секунды
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Функция для получения текущего username из URL
function getCurrentUsername() {
    const path = window.location.pathname;
    const match = path.match(/\/feed\/(.+)/);
    if (match && match[1]) {
        return match[1];
    }
    return localStorage.getItem('username') || localStorage.getItem('user_name');
}

// Обновите функцию displayRecommendations, добавив data-track-id
function displayRecommendations(tracks, stats) {
    const container = document.getElementById('recommendations');
    if (!container) return;
    
    if (!tracks || tracks.length === 0) {
        container.innerHTML = `
            <div class="no-recommendations">
                😔 Пока нет рекомендаций.<br>
                Добавьте несколько треков в избранное, и мы подберем для вас музыку!
            </div>
        `;
        return;
    }
    
    // Показываем информацию о пользователе
    const userInfo = stats && stats.favorites_count !== undefined 
        ? `<div class="user-info-stats">
            📊 У вас ${stats.favorites_count} ${getFavoritesWord(stats.favorites_count)} в избранном
           </div>`
        : '';
    
    container.innerHTML = userInfo + '<div class="recommendations-grid">';
    
    const gridContainer = container.querySelector('.recommendations-grid');
    
    tracks.forEach((track, index) => {
        const trackCard = document.createElement('div');
        trackCard.className = 'track-card';
        trackCard.setAttribute('data-track-id', track.id);
        trackCard.innerHTML = `
            <div class="track-number">${index + 1}</div>
            <img src="${track.cover_url || '/static/default_cover.jpg'}" 
                 alt="cover" 
                 class="track-cover"
                 onerror="this.src='/static/default_cover.jpg'">
            <div class="track-info">
                <div class="track-title">${escapeHtml(track.title)}</div>
                <div class="track-artist">${escapeHtml(track.artist)}</div>
                ${track.genre ? `<div class="track-genre">🎵 ${track.genre}</div>` : ''}
                <div class="track-reason">💡 ${track.recommendation_reason || 'Рекомендовано для вас'}</div>
            </div>
            <div class="track-actions">
                <button onclick="addToFavorites(${track.id}, this)" class="fav-btn">
                    ❤️ В избранное
                </button>
                <audio controls src="${track.file_url}" class="audio-player" preload="none"></audio>
            </div>
        `;
        gridContainer.appendChild(trackCard);
    });
    
    container.innerHTML += '</div>';
}

// Добавьте CSS анимации в ваш HTML файл
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateX(20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .recommendations-grid {
        display: grid;
        gap: 20px;
    }
    
    .user-info-stats {
        background: white;
        border-radius: 15px;
        padding: 15px 25px;
        margin-bottom: 20px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        text-align: center;
        color: #764ba2;
        font-weight: 500;
    }
`;
document.head.appendChild(style);

// Загрузка избранного на странице /favorites.html
async function loadFavorites() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/login.html';
        return;
    }
    const res = await fetch(`${API_BASE}/favorites`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const tracks = await res.json();
    // отображение аналогично рекомендациям, добавить кнопку удаления
}

// Вызов функций при загрузке страницы
if (window.location.pathname === '/' || window.location.pathname === '/index.html') {
    loadRecommendations();
}
if (window.location.pathname === '/favorites.html') {
    loadFavorites();
}

// Добавьте в конец main.js
document.getElementById('vkForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const consent = document.getElementById('consent').checked;
    const parseResult = document.getElementById('parseResult');
    
    if (!consent) {
        alert('Необходимо дать согласие на обработку данных');
        return;
    }
    
    // Проверяем, был ли выполнен парсинг
    if (!parseResult.style.display === 'block' || !parseResult.innerHTML.includes('Успешно')) {
        alert('Сначала выполните парсинг данных VK');
        return;
    }
    
    // Перенаправляем на главную
    window.location.href = '/';
});



function getCurrentUsername() {
    // Сначала пробуем получить из URL (для страницы /feed/username)
    const path = window.location.pathname;
    const match = path.match(/\/feed\/(.+)/);
    if (match && match[1]) {
        return match[1];
    }
    
    // Если нет, берем из localStorage
    return localStorage.getItem('username') || localStorage.getItem('user_name');
}

// Загрузка рекомендаций
async function loadRecommendations() {
    const username = getCurrentUsername();
    
    if (!username) {
        console.log('Пользователь не авторизован');
        loadDefaultRecommendations();
        return;
    }
    
    showLoading();
    
    try {
        // Получаем статистику пользователя
        const statsResponse = await fetch(`${API_BASE}/user_stats/${username}`);
        const stats = await statsResponse.json();
        
        // Получаем рекомендации
        const response = await fetch(`${API_BASE}/recommendations/${username}?limit=20`);
        const data = await response.json();
        
        if (data.success) {
            displayRecommendations(data.recommendations, stats);
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        console.error('Ошибка:', error);
        loadDefaultRecommendations();
    } finally {
        hideLoading();
    }
}

function displayRecommendations(tracks, stats) {
    const container = document.getElementById('recommendations');
    if (!container) return;
    
    if (!tracks || tracks.length === 0) {
        container.innerHTML = `
            <div class="no-recommendations">
                😔 Пока нет рекомендаций.<br>
                Добавьте несколько треков в избранное, и мы подберем для вас музыку!
            </div>
        `;
        return;
    }
    
    // Показываем информацию о пользователе
    const userInfo = stats && stats.favorites_count !== undefined 
        ? `<div class="user-info">
            📊 У вас ${stats.favorites_count} ${getFavoritesWord(stats.favorites_count)} в избранном
           </div>`
        : '';
    
    container.innerHTML = userInfo + tracks.map((track, index) => `
        <div class="track-card">
            <div class="track-number">${index + 1}</div>
            <img src="${track.cover_url || '/static/default_cover.jpg'}" 
                 alt="cover" 
                 class="track-cover"
                 onerror="this.src='/static/default_cover.jpg'">
            <div class="track-info">
                <div class="track-title">${escapeHtml(track.title)}</div>
                <div class="track-artist">${escapeHtml(track.artist)}</div>
                ${track.genre ? `<div class="track-genre">🎵 ${track.genre}</div>` : ''}
                <div class="track-reason">💡 ${track.recommendation_reason || 'Рекомендовано для вас'}</div>
            </div>
            <div class="track-actions">
                <button onclick="addToFavorites(${track.id}, this)" class="fav-btn">
                    ❤️ В избранное
                </button>
                <audio controls src="${track.file_url}" class="audio-player" preload="none"></audio>
            </div>
        </div>
    `).join('');
}

function getFavoritesWord(count) {
    if (count % 10 === 1 && count % 100 !== 11) return 'трек';
    if ([2, 3, 4].includes(count % 10) && ![12, 13, 14].includes(count % 100)) return 'трека';
    return 'треков';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function addToFavorites(trackId, button) {
    const token = localStorage.getItem('token');
    
    if (!token) {
        alert('Войдите, чтобы добавить в избранное');
        return;
    }
    
    const originalText = button.textContent;
    button.textContent = '⏳ ...';
    button.disabled = true;
    
    try {
        const res = await fetch(`${API_BASE}/favorites`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ track_id: trackId })
        });
        
        if (res.ok) {
            button.innerHTML = '✅ В избранном';
            setTimeout(() => {
                button.innerHTML = '❤️ В избранное';
            }, 2000);
            
            // Обновляем рекомендации
            setTimeout(() => {
                loadRecommendations();
            }, 1000);
        } else {
            const data = await res.json();
            alert(data.error || 'Ошибка');
            button.textContent = originalText;
            button.disabled = false;
        }
    } catch (error) {
        console.error('Ошибка:', error);
        alert('Ошибка соединения');
        button.textContent = originalText;
        button.disabled = false;
    }
}

function loadDefaultRecommendations() {
    fetch(`${API_BASE}/recommendations`)
        .then(res => res.json())
        .then(tracks => {
            if (Array.isArray(tracks)) {
                const tracksWithReason = tracks.map(track => ({
                    ...track,
                    recommendation_reason: 'Популярный трек'
                }));
                displayRecommendations(tracksWithReason, { favorites_count: 0 });
            }
        })
        .catch(error => console.error('Ошибка:', error));
}

function showLoading() {
    const container = document.getElementById('recommendations');
    if (container) {
        container.innerHTML = '<div class="loading">🎵 Анализируем ваш профиль и подбираем музыку...</div>';
    }
}

function hideLoading() {
    // Индикатор исчезнет при отображении рекомендаций
}

// Инициализация при загрузке страницы
if (window.location.pathname === '/' || 
    window.location.pathname.includes('/feed/')) {
    document.addEventListener('DOMContentLoaded', loadRecommendations);
}