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
        window.location.href = '/auth_choice/' + username;
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
        localStorage.setItem('username', username);
        localStorage.setItem('user_name', username);
        window.location.href = '/feed/' + username;
    } else {
        alert(data.error);
    }
});

// Выход из системы
function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('username');
    localStorage.removeItem('user_name');
    window.location.href = '/login';
}

// Получение текущего username
function getCurrentUsername() {
    const path = window.location.pathname;
    const match = path.match(/\/feed\/(.+)/);
    if (match && match[1]) {
        return match[1];
    }
    return localStorage.getItem('username') || localStorage.getItem('user_name');
}

// Вспомогательные функции
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

function showLoading() {
    const container = document.getElementById('recommendations');
    if (container) {
        container.innerHTML = '<div class="loading">🎵 Анализируем ваш профиль и подбираем музыку...</div>';
    }
}

function hideLoading() {}

// Показ уведомлений
function showNotification(message, type = 'success') {
    const oldNotifications = document.querySelectorAll('.notification');
    oldNotifications.forEach(notif => notif.remove());
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    const colors = {
        success: '#4caf50',
        error: '#ff4757',
        info: '#2196f3',
        warning: '#ff9800'
    };
    
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${colors[type] || colors.success};
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        z-index: 1000;
        animation: slideInRight 0.3s ease;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        font-size: 14px;
        font-weight: 500;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Обновление нумерации треков
function updateTrackNumbers() {
    const trackCards = document.querySelectorAll('.track-card');
    trackCards.forEach((card, index) => {
        const numberDiv = card.querySelector('.track-number');
        if (numberDiv) {
            numberDiv.textContent = (index + 1).toString();
        }
    });
}

// Обновление счетчика избранного
async function updateFavoritesCount() {
    const username = getCurrentUsername();
    if (!username) return;
    
    try {
        const response = await fetch(`${API_BASE}/user_stats/${username}`);
        const data = await response.json();
        
        if (data.success) {
            let statsElement = document.querySelector('.user-info-stats');
            if (!statsElement) {
                const container = document.getElementById('recommendations');
                if (container && container.firstChild) {
                    const existingStats = container.querySelector('.user-info-stats');
                    if (existingStats) {
                        statsElement = existingStats;
                    } else if (container.firstChild && container.firstChild.className === 'user-info-stats') {
                        statsElement = container.firstChild;
                    }
                }
            }
            
            if (statsElement) {
                const count = data.favorites_count;
                statsElement.innerHTML = `📊 У вас ${count} ${getFavoritesWord(count)} в избранном`;
            }
        }
    } catch (error) {
        console.error('Ошибка обновления счетчика:', error);
    }
}

// Добавление трека в конец списка
function appendTrackToEnd(track, newNumber) {
    const container = document.getElementById('recommendations');
    if (!container) return;
    
    let gridContainer = container.querySelector('.recommendations-grid');
    if (!gridContainer) {
        gridContainer = document.createElement('div');
        gridContainer.className = 'recommendations-grid';
        container.appendChild(gridContainer);
    }
    
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
                ${track.genre ? `<div class="track-genre">🎵 ${escapeHtml(track.genre)}</div>` : ''}
                <div class="track-reason">💡 ${track.recommendation_reason || 'Рекомендовано для вас'}</div>
            </div>
            <div class="track-actions">
                <button onclick="addToFavorites(${track.id}, this)" class="fav-btn">
                    ❤️ В избранное
                </button>
                <button onclick="skipTrack(${track.id}, this)" class="skip-btn" style="background: #999; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-size: 14px;">
                    ⏭️ Убрать из списка
                </button>
                <audio controls src="${track.file_url}" class="audio-player" preload="none"></audio>
            </div>
        </div>
    `;
    
    gridContainer.insertAdjacentHTML('beforeend', trackHtml);
    
    const newCard = gridContainer.lastElementChild;
    setTimeout(() => {
        if (newCard) newCard.style.animation = '';
    }, 500);
}

// Загрузка заменяющего трека
async function loadReplacementTrack() {
    const username = getCurrentUsername();
    if (!username) return;
    
    try {
        const currentTrackIds = Array.from(document.querySelectorAll('.track-card'))
            .map(card => parseInt(card.dataset.trackId))
            .filter(id => !isNaN(id));
        
        const response = await fetch(`${API_BASE}/recommendations/${username}?limit=25`);
        const data = await response.json();
        
        if (data.success && data.recommendations) {
            const newTrack = data.recommendations.find(track => !currentTrackIds.includes(track.id));
            
            if (newTrack) {
                appendTrackToEnd(newTrack, currentTrackIds.length + 1);
                showNotification(`✨ Новый трек: ${newTrack.title} - ${newTrack.artist}`, 'info');
            } else {
                const globalResponse = await fetch(`${API_BASE}/recommendations?limit=10`);
                const globalTracks = await globalResponse.json();
                
                if (Array.isArray(globalTracks) && globalTracks.length > 0) {
                    const newGlobalTrack = globalTracks.find(track => !currentTrackIds.includes(track.id));
                    if (newGlobalTrack) {
                        newGlobalTrack.recommendation_reason = 'Популярный трек';
                        appendTrackToEnd(newGlobalTrack, currentTrackIds.length + 1);
                        showNotification(`✨ Новый популярный трек: ${newGlobalTrack.title} - ${newGlobalTrack.artist}`, 'info');
                    }
                }
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки замены:', error);
        showNotification('Не удалось загрузить новый трек', 'warning');
    }
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
            button.innerHTML = '✅ В избранном';
            button.style.opacity = '0.6';
            
            const trackCard = button.closest('.track-card');
            if (trackCard) {
                trackCard.style.transition = 'all 0.3s ease';
                trackCard.style.opacity = '0.5';
                trackCard.style.transform = 'translateX(20px)';
                
                setTimeout(() => {
                    trackCard.remove();
                    updateTrackNumbers();
                    showNotification('Трек добавлен в избранное!', 'success');
                    loadReplacementTrack();
                    updateFavoritesCount();
                }, 300);
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

// Пропуск трека
async function skipTrack(trackId, button) {
    const trackCard = button.closest('.track-card');
    if (trackCard) {
        trackCard.style.transition = 'all 0.3s ease';
        trackCard.style.opacity = '0';
        trackCard.style.transform = 'translateX(-20px)';
        
        setTimeout(() => {
            trackCard.remove();
            updateTrackNumbers();
            loadReplacementTrack();
            showNotification('Трек убран из списка', 'info');
        }, 300);
    }
}

// Отображение рекомендаций
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
    
    const userInfo = stats && stats.favorites_count !== undefined 
        ? `<div class="user-info-stats">
            📊 У вас ${stats.favorites_count} ${getFavoritesWord(stats.favorites_count)} в избранном
           </div>`
        : '';
    
    container.innerHTML = userInfo;
    
    const gridContainer = document.createElement('div');
    gridContainer.className = 'recommendations-grid';
    container.appendChild(gridContainer);
    
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
                ${track.genre ? `<div class="track-genre">🎵 ${escapeHtml(track.genre)}</div>` : ''}
                <div class="track-reason">💡 ${track.recommendation_reason || 'Рекомендовано для вас'}</div>
            </div>
            <div class="track-actions">
                <button onclick="addToFavorites(${track.id}, this)" class="fav-btn">
                    ❤️ В избранное
                </button>
                <button onclick="skipTrack(${track.id}, this)" class="skip-btn" style="background: #999; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-size: 14px;">
                    ⏭️ Убрать из списка
                </button>
                <audio controls src="${track.file_url}" class="audio-player" preload="none"></audio>
            </div>
        `;
        gridContainer.appendChild(trackCard);
    });
}

// Загрузка рекомендаций по умолчанию
async function loadDefaultRecommendations() {
    try {
        const response = await fetch(`${API_BASE}/recommendations?limit=20`);
        const tracks = await response.json();
        
        if (Array.isArray(tracks)) {
            const tracksWithReason = tracks.map(track => ({
                ...track,
                recommendation_reason: 'Популярный трек'
            }));
            displayRecommendations(tracksWithReason, { favorites_count: 0 });
        }
    } catch (error) {
        console.error('Ошибка:', error);
        const container = document.getElementById('recommendations');
        if (container) {
            container.innerHTML = '<div class="no-recommendations">❌ Ошибка загрузки рекомендаций</div>';
        }
    }
}

// Основная функция загрузки рекомендаций
async function loadRecommendations() {
    const username = getCurrentUsername();
    
    if (!username) {
        console.log('Пользователь не авторизован');
        loadDefaultRecommendations();
        return;
    }
    
    showLoading();
    
    try {
        const statsResponse = await fetch(`${API_BASE}/user_stats/${username}`);
        const stats = await statsResponse.json();
        
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

// Добавление CSS анимаций
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
    
    .notification {
        pointer-events: none;
    }
    
    .skip-btn:hover {
        opacity: 0.8;
        transform: scale(1.05);
    }
`;

if (!document.querySelector('style[data-dynamic]')) {
    style.setAttribute('data-dynamic', 'true');
    document.head.appendChild(style);
}

// Инициализация при загрузке страницы
if (window.location.pathname === '/' || 
    window.location.pathname.includes('/feed/')) {
    document.addEventListener('DOMContentLoaded', loadRecommendations);
}