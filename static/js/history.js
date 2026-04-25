if (typeof API_BASE === 'undefined') {
    const API_BASE = 'http://localhost:5000/api';
}

function getToken() {
    return localStorage.getItem('token');
}

function getCurrentUsername() {
    const path = window.location.pathname;
    const match = path.match(/\/history\/(.+)/);
    if (match && match[1]) return match[1];
    return localStorage.getItem('username') || localStorage.getItem('user_name');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getFavoritesWord(count) {
    if (count % 10 === 1 && count % 100 !== 11) return 'трек';
    if ([2, 3, 4].includes(count % 10) && ![12, 13, 14].includes(count % 100)) return 'трека';
    return 'треков';
}

function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Только что';
    if (diff < 3600000) return `${Math.floor(diff / 60000)} мин. назад`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} ч. назад`;
    
    return date.toLocaleDateString('ru-RU', { 
        day: 'numeric', 
        month: 'long',
        hour: '2-digit',
        minute: '2-digit'
    });
}

async function loadHistory() {
    const token = getToken();
    if (!token) {
        window.location.href = '/login';
        return;
    }

    const container = document.getElementById('historyContent');
    container.innerHTML = '<div class="loading">🕒 Загрузка истории...</div>';

    try {
        const response = await fetch(`${API_BASE}/history`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.status === 401) {
            localStorage.removeItem('token');
            alert('Сессия истекла, войдите снова');
            window.location.href = '/login';
            return;
        }
        const history = await response.json();
        
        if (!history.length) {
            container.innerHTML = `
                <div class="empty-history">
                    🎧 Вы пока не слушали треки<br><br>
                    <a href="/feed/${getCurrentUsername()}">🎵 Перейти к рекомендациям</a>
                </div>
            `;
            return;
        }
        
        const tracks = history.map(item => ({
            id: item.track_id,
            title: item.title,
            artist: item.artist,
            genre: item.genre,
            cover_url: item.cover_url,
            file_url: item.file_url,
            played_at: item.played_at
        }));
        
        container.innerHTML = `
            <div class="history-header">
                <div class="history-count">🕒 Прослушано ${tracks.length} ${getFavoritesWord(tracks.length)}</div>
                <button class="clear-all-btn" onclick="clearAllHistory()">🗑️ Очистить историю</button>
            </div>
            <div class="history-grid">
                ${tracks.map((track, index) => `
                    <div class="track-card" data-track-id="${track.id}">
                        <img src="${track.cover_url || '/static/default_cover.jpg'}" 
                             alt="cover" 
                             class="track-cover"
                             onerror="this.src='/static/default_cover.jpg'">
                        <div class="track-info">
                            <div class="track-title">${escapeHtml(track.title)}</div>
                            <div class="track-artist">${escapeHtml(track.artist)}</div>
                            ${track.genre ? `<div class="track-genre">🎵 ${escapeHtml(track.genre)}</div>` : ''}
                            <div class="track-timestamp">🕐 ${formatTimestamp(track.played_at)}</div>
                        </div>
                        <div class="track-actions">
                            <button class="remove-btn" onclick="removeFromHistory(${track.id})">
                                ❌ Удалить
                            </button>
                            <audio controls src="${track.file_url}" class="audio-player" preload="none"></audio>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (error) {
        console.error('Ошибка загрузки истории:', error);
        container.innerHTML = '<div class="empty-history">❌ Ошибка загрузки истории</div>';
    }
}

async function removeFromHistory(trackId) {
    const token = getToken();
    if (!token) return;
    
    try {
        const response = await fetch(`${API_BASE}/history/${trackId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
            loadHistory();
            showNotification('Трек удалён из истории', 'success');
        } else {
            const data = await response.json();
            showNotification(data.error || 'Ошибка удаления', 'error');
        }
    } catch (error) {
        console.error('Ошибка удаления:', error);
        showNotification('Не удалось удалить трек', 'error');
    }
}

async function clearAllHistory() {
    if (!confirm('Вы уверены, что хотите очистить всю историю прослушивания?')) return;
    const token = getToken();
    if (!token) return;
    
    try {
        const response = await fetch(`${API_BASE}/history`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
            loadHistory();
            showNotification('История очищена', 'success');
        } else {
            const data = await response.json();
            showNotification(data.error || 'Ошибка очистки', 'error');
        }
    } catch (error) {
        console.error('Ошибка очистки:', error);
        showNotification('Не удалось очистить историю', 'error');
    }
}

async function addToHistory(track) {
    const token = getToken();
    if (!token) return; 
    
    try {
        await fetch(`${API_BASE}/history`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ track_id: track.id })
        });
        
    } catch (error) {
        console.error('Ошибка сохранения истории:', error);
    }
}

function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#4caf50' : '#ff4757'};
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

const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

document.addEventListener('play', function(e) {
    const audio = e.target;
    if (audio.classList.contains('audio-player')) {
        const trackCard = audio.closest('.track-card');
        if (trackCard) {
            const track = {
                id: parseInt(trackCard.dataset.trackId),
                title: trackCard.querySelector('.track-title')?.textContent || 'Неизвестный трек',
                artist: trackCard.querySelector('.track-artist')?.textContent || 'Неизвестный исполнитель',
                genre: trackCard.querySelector('.track-genre')?.textContent?.replace('🎵 ', '') || '',
                cover_url: trackCard.querySelector('.track-cover')?.src || '',
                file_url: audio.src
            };
            addToHistory(track);
        }
    }
}, true);

document.addEventListener('DOMContentLoaded', loadHistory);