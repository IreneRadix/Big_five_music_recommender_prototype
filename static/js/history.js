// history.js
const STORAGE_KEY = 'recently_played_tracks';
const MAX_HISTORY_ITEMS = 20;

function getCurrentUsername() {
    const path = window.location.pathname;
    const match = path.match(/\/history\/(.+)/);
    if (match && match[1]) {
        return match[1];
    }
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

function loadHistory() {
    const container = document.getElementById('historyContent');
    
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        let tracks = stored ? JSON.parse(stored) : [];
        
        // Проверяем, что это массив и сортируем по времени (сначала новые)
        if (!Array.isArray(tracks)) tracks = [];
        tracks.sort((a, b) => new Date(b.played_at) - new Date(a.played_at));
        
        if (tracks.length === 0) {
            container.innerHTML = `
                <div class="empty-history">
                    🎧 Вы пока не слушали треки<br><br>
                    <a href="/feed/${getCurrentUsername()}">🎵 Перейти к рекомендациям</a> и начните слушать музыку!
                </div>
            `;
            return;
        }
        
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
        container.innerHTML = `
            <div class="empty-history">
                ❌ Ошибка загрузки истории<br><br>
                <a href="/feed/${getCurrentUsername()}">Вернуться к рекомендациям</a>
            </div>
        `;
    }
}

function removeFromHistory(trackId) {
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        let tracks = stored ? JSON.parse(stored) : [];
        
        tracks = tracks.filter(t => t.id !== trackId);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(tracks));
        
        // Обновляем отображение
        loadHistory();
        showNotification('Трек удалён из истории', 'success');
    } catch (error) {
        console.error('Ошибка удаления:', error);
        showNotification('Не удалось удалить трек', 'error');
    }
}

function clearAllHistory() {
    if (!confirm('Вы уверены, что хотите очистить всю историю прослушивания?')) return;
    
    try {
        localStorage.removeItem(STORAGE_KEY);
        loadHistory();
        showNotification('История очищена', 'success');
    } catch (error) {
        console.error('Ошибка очистки:', error);
        showNotification('Не удалось очистить историю', 'error');
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

// Добавляем стили для анимаций
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

// Загрузка при старте
document.addEventListener('DOMContentLoaded', loadHistory);