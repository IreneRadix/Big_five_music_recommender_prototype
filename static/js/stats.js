// stats.js - Статистика пользователя
const API_BASE = 'http://localhost:5000/api';

function getCurrentUsername() {
    const path = window.location.pathname;
    const match = path.match(/\/stats\/(.+)/);
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

// Форматирование длительности
function formatDuration(seconds) {
    if (!seconds || seconds < 60) return '< 1 мин';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
        return `${hours} ч ${minutes} мин`;
    }
    return `${minutes} мин`;
}

// Загрузка статистики
async function loadStats() {
    const username = getCurrentUsername();
    
    if (!username) {
        showError('Пользователь не найден');
        return;
    }
    
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE}/user_stats_full/${username}`);
        const data = await response.json();
        
        if (data.success) {
            displayStats(data.stats);
            initTabs(data.stats);
        } else {
            showError(data.error || 'Ошибка загрузки статистики');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showError('Не удалось загрузить статистику');
    } finally {
        hideLoading();
    }
}

// Отображение статистики
function displayStats(stats) {
    const container = document.getElementById('statsContent');
    
    // Общая статистика
    const totalStats = stats.all_time;
    
    container.innerHTML = `
        <div class="stats-overview">
            <div class="stat-card">
                <div class="stat-icon">🎵</div>
                <div class="stat-value">${totalStats.total_plays || 0}</div>
                <div class="stat-label">Всего прослушиваний</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">⭐</div>
                <div class="stat-value">${totalStats.favorites_count || 0}</div>
                <div class="stat-label">В избранном</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">⏱️</div>
                <div class="stat-value">${formatDuration(totalStats.total_listening_time || 0)}</div>
                <div class="stat-label">Время прослушивания</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">🎸</div>
                <div class="stat-value">${totalStats.unique_artists || 0}</div>
                <div class="stat-label">Уникальных исполнителей</div>
            </div>
        </div>
        
        <div class="stats-period-tabs">
            <button class="period-tab active" data-period="week">📅 За неделю</button>
            <button class="period-tab" data-period="month">📆 За месяц</button>
            <button class="period-tab" data-period="year">📅 За год</button>
            <button class="period-tab" data-period="all_time">📊 За всё время</button>
        </div>
        
        <div class="charts-container">
            <div class="chart-row">
                <div class="chart-card">
                    <h3>🎧 Распределение прослушиваний по настроению</h3>
                    <div class="chart-wrapper">
                        <canvas id="playsMoodChart"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <h3>⭐ Распределение избранного по настроению</h3>
                    <div class="chart-wrapper">
                        <canvas id="favoritesMoodChart"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="chart-row">
                <div class="chart-card full-width">
                    <h3>📈 Активность прослушиваний</h3>
                    <div class="chart-wrapper">
                        <canvas id="activityChart"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="chart-row">
                <div class="chart-card">
                    <h3>🎤 Топ исполнителей</h3>
                    <div id="topArtistsList" class="top-list">
                        ${renderTopArtists(totalStats.top_artists || [])}
                    </div>
                </div>
                <div class="chart-card">
                    <h3>🎼 Топ жанров</h3>
                    <div id="topGenresList" class="top-list">
                        ${renderTopGenres(totalStats.top_genres || [])}
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Инициализация графиков с данными за всё время
    updateCharts(stats.all_time);
}

// Отрисовка топ исполнителей
function renderTopArtists(artists) {
    if (!artists || artists.length === 0) {
        return '<div class="empty-list">Нет данных</div>';
    }
    
    return artists.slice(0, 10).map((item, index) => `
        <div class="list-item">
            <span class="item-rank">${index + 1}</span>
            <span class="item-name">${escapeHtml(item.artist)}</span>
            <span class="item-count">${item.count} 🎵</span>
        </div>
    `).join('');
}

// Отрисовка топ жанров
function renderTopGenres(genres) {
    if (!genres || genres.length === 0) {
        return '<div class="empty-list">Нет данных</div>';
    }
    
    return genres.slice(0, 10).map((item, index) => `
        <div class="list-item">
            <span class="item-rank">${index + 1}</span>
            <span class="item-name">${escapeHtml(item.genre || 'Без жанра')}</span>
            <span class="item-count">${item.count} 🎵</span>
        </div>
    `).join('');
}

// Глобальные переменные для графиков
let playsMoodChart = null;
let favoritesMoodChart = null;
let activityChart = null;

// Цвета для настроений
const moodColors = {
    'energetic': '#ff4757',
    'энергичная': '#ff4757',
    'calm': '#4ecdc4',
    'спокойная': '#4ecdc4',
    'happy': '#ffa502',
    'радостная': '#ffa502',
    'sad': '#5f27cd',
    'грустная': '#5f27cd',
    'меланхоличная': '#5f27cd',
    'romantic': '#ff6b81',
    'романтичная': '#ff6b81',
    'other': '#7bed9f',
    'другое': '#7bed9f'
};

const moodLabels = {
    'energetic': '⚡ Энергичная',
    'calm': '😌 Спокойная',
    'happy': '😊 Радостная',
    'sad': '😔 Грустная',
    'romantic': '💕 Романтичная',
    'other': '🎵 Другое'
};

// Обновление графиков
function updateCharts(periodStats) {
    // График прослушиваний по настроению
    const playsMoodData = periodStats.plays_by_mood || {};
    updateMoodChart('playsMoodChart', playsMoodData, 'Прослушивания');
    
    // График избранного по настроению
    const favoritesMoodData = periodStats.favorites_by_mood || {};
    updateMoodChart('favoritesMoodChart', favoritesMoodData, 'В избранном');
    
    // График активности
    const activityData = periodStats.daily_activity || [];
    updateActivityChart(activityData);
    
    // Обновление топ-списков
    updateTopLists(periodStats);
}

// Обновление графика настроения
function updateMoodChart(canvasId, data, label) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // Подготовка данных
    const moods = ['energetic', 'calm', 'happy', 'sad', 'romantic', 'other'];
    const values = moods.map(m => data[m] || 0);
    const labels = moods.map(m => moodLabels[m] || m);
    const colors = moods.map(m => moodColors[m] || '#7bed9f');
    
    // Уничтожаем старый график если есть
    if (canvasId === 'playsMoodChart' && playsMoodChart) {
        playsMoodChart.destroy();
    } else if (canvasId === 'favoritesMoodChart' && favoritesMoodChart) {
        favoritesMoodChart.destroy();
    }
    
    const newChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: getComputedStyle(document.documentElement)
                    .getPropertyValue('--card-bg').trim() || '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: getComputedStyle(document.documentElement)
                            .getPropertyValue('--text-primary').trim() || '#333333',
                        font: { size: 12 }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const value = context.raw;
                            const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                            return `${context.label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
    
    if (canvasId === 'playsMoodChart') {
        playsMoodChart = newChart;
    } else {
        favoritesMoodChart = newChart;
    }
}

// Обновление графика активности
function updateActivityChart(data) {
    const canvas = document.getElementById('activityChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    if (activityChart) {
        activityChart.destroy();
    }
    
    // Подготовка данных
    const labels = data.map(d => d.date);
    const values = data.map(d => d.count);
    
    activityChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Прослушиваний',
                data: values,
                backgroundColor: '#667eea',
                borderRadius: 8,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1,
                        color: getComputedStyle(document.documentElement)
                            .getPropertyValue('--text-secondary').trim() || '#666666'
                    },
                    grid: {
                        color: getComputedStyle(document.documentElement)
                            .getPropertyValue('--card-border').trim() || 'rgba(0,0,0,0.1)'
                    }
                },
                x: {
                    ticks: {
                        color: getComputedStyle(document.documentElement)
                            .getPropertyValue('--text-secondary').trim() || '#666666'
                    },
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

// Обновление топ-списков
function updateTopLists(periodStats) {
    const topArtistsList = document.getElementById('topArtistsList');
    const topGenresList = document.getElementById('topGenresList');
    
    if (topArtistsList) {
        topArtistsList.innerHTML = renderTopArtists(periodStats.top_artists || []);
    }
    
    if (topGenresList) {
        topGenresList.innerHTML = renderTopGenres(periodStats.top_genres || []);
    }
}

// Инициализация переключения периодов
function initTabs(stats) {
    const tabs = document.querySelectorAll('.period-tab');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Обновление активного класса
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            // Получение данных для периода
            const period = tab.dataset.period;
            const periodStats = stats[period] || stats.all_time;
            
            // Обновление графиков
            updateCharts(periodStats);
        });
    });
}

// Вспомогательные функции
function showLoading() {
    const container = document.getElementById('statsContent');
    if (container) {
        container.innerHTML = '<div class="loading">📊 Загрузка статистики...</div>';
    }
}

function hideLoading() {}

function showError(message) {
    const container = document.getElementById('statsContent');
    if (container) {
        container.innerHTML = `
            <div class="empty-stats">
                ❌ ${message}<br><br>
                <a href="/feed/${getCurrentUsername()}">Вернуться к рекомендациям</a>
            </div>
        `;
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

// Загрузка при старте
document.addEventListener('DOMContentLoaded', loadStats);