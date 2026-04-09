const API_BASE = 'http://localhost:5000/api';

// Получение username из URL
function getCurrentUsername() {
    const path = window.location.pathname;
    const match = path.match(/\/favorites\/(.+)/);
    if (match && match[1]) {
        return match[1];
    }
    return localStorage.getItem('username') || localStorage.getItem('user_name');
}

// Загрузка избранных треков
async function loadFavorites() {
    const token = localStorage.getItem('token');
    
    if (!token) {
        alert('Пожалуйста, войдите в систему');
        window.location.href = '/login';
        return;
    }
    
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE}/favorites`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.status === 401) {
            // Токен истек или недействителен
            localStorage.removeItem('token');
            localStorage.removeItem('user_id');
            alert('Сессия истекла, пожалуйста, войдите снова');
            window.location.href = '/login';
            return;
        }
        
        const tracks = await response.json();
        displayFavorites(tracks);
        
    } catch (error) {
        console.error('Ошибка:', error);
        showError('Не удалось загрузить избранные треки');
    } finally {
        hideLoading();
    }
}

// Отображение избранных треков
function displayFavorites(tracks) {
    const container = document.getElementById('favoritesContent');
    
    if (!tracks || tracks.length === 0) {
        container.innerHTML = `
            <div class="empty-favorites">
                😔 У вас пока нет избранных треков<br><br>
                <a href="/feed/${getCurrentUsername()}">🎵 Перейти к рекомендациям</a> и добавьте понравившиеся треки!
            </div>
        `;
        return;
    }
    
    container.innerHTML = `
        <div class="favorites-header">
            <div class="favorites-count">⭐ У вас ${tracks.length} ${getFavoritesWord(tracks.length)} в избранном</div>
            <button class="clear-all-btn" onclick="clearAllFavorites()">🗑️ Очистить всё</button>
        </div>
        <div class="favorites-grid">
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
                    </div>
                    <div class="track-actions">
                        <button class="remove-btn" onclick="removeFromFavorites(${track.id}, this)">
                            ❌ Удалить
                        </button>
                        <audio controls src="${track.file_url}" class="audio-player" preload="none"></audio>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

// Удаление трека из избранного
async function removeFromFavorites(trackId, button) {
    const token = localStorage.getItem('token');
    
    if (!token) {
        alert('Пожалуйста, войдите в систему');
        return;
    }
    
    const originalText = button.textContent;
    button.textContent = '⏳ Удаление...';
    button.disabled = true;
    
    try {
        const response = await fetch(`${API_BASE}/favorites/${trackId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            // Находим карточку трека и удаляем её с анимацией
            const trackCard = button.closest('.track-card');
            trackCard.style.transition = 'all 0.3s ease';
            trackCard.style.opacity = '0';
            trackCard.style.transform = 'translateX(-20px)';
            
            setTimeout(() => {
                trackCard.remove();
                showNotification('Трек удален из избранного', 'success');
                
                // Обновляем счетчик
                const remainingTracks = document.querySelectorAll('.track-card').length;
                const countElement = document.querySelector('.favorites-count');
                if (countElement) {
                    if (remainingTracks === 0) {
                        // Если треков не осталось, показываем пустое состояние
                        loadFavorites();
                    } else {
                        countElement.textContent = `⭐ У вас ${remainingTracks} ${getFavoritesWord(remainingTracks)} в избранном`;
                    }
                }
            }, 300);
        } else {
            const data = await response.json();
            alert(data.error || 'Ошибка при удалении');
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

// Очистка всех избранных треков
async function clearAllFavorites() {
    const confirmed = confirm('Вы уверены, что хотите удалить все треки из избранного? Это действие нельзя отменить.');
    
    if (!confirmed) return;
    
    const token = localStorage.getItem('token');
    
    if (!token) {
        alert('Пожалуйста, войдите в систему');
        return;
    }
    
    const button = document.querySelector('.clear-all-btn');
    const originalText = button.textContent;
    button.textContent = '⏳ Очистка...';
    button.disabled = true;
    
    try {
        // Получаем все треки
        const response = await fetch(`${API_BASE}/favorites`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const tracks = await response.json();
        
        // Удаляем каждый трек
        let deletedCount = 0;
        for (const track of tracks) {
            const deleteResponse = await fetch(`${API_BASE}/favorites/${track.id}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (deleteResponse.ok) {
                deletedCount++;
            }
        }
        
        if (deletedCount > 0) {
            showNotification(`Удалено ${deletedCount} треков из избранного`, 'success');
            loadFavorites(); // Перезагружаем страницу
        } else {
            alert('Не удалось удалить треки');
            button.textContent = originalText;
            button.disabled = false;
        }
    } catch (error) {
        console.error('Ошибка:', error);
        alert('Ошибка при очистке избранного');
        button.textContent = originalText;
        button.disabled = false;
    }
}

// Выход из системы
function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('username');
    localStorage.removeItem('user_name');
    window.location.href = '/login';
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
    const container = document.getElementById('favoritesContent');
    if (container) {
        container.innerHTML = '<div class="loading">⭐ Загрузка избранных треков...</div>';
    }
}

function hideLoading() {
    // Индикатор исчезнет при отображении треков
}

function showError(message) {
    const container = document.getElementById('favoritesContent');
    if (container) {
        container.innerHTML = `
            <div class="empty-favorites">
                ❌ ${message}<br><br>
                <a href="/feed/${getCurrentUsername()}">Вернуться к рекомендациям</a>
            </div>
        `;
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
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Добавляем CSS анимации
const style = document.createElement('style');
style.textContent = `
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
`;
document.head.appendChild(style);

// Загрузка при старте
document.addEventListener('DOMContentLoaded', loadFavorites);