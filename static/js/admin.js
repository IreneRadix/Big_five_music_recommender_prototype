const API_BASE = 'http://localhost:5000';
let charts = {};

// Проверка прав администратора
async function checkAdminAccess() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/login';
        return false;
    }
    return true;
}

// Загрузка общей статистики
async function loadOverviewStats() {
    const token = localStorage.getItem('token');
    
    try {
        const response = await fetch(`${API_BASE}/admin/api/stats/overview`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                document.getElementById('totalUsers').textContent = data.stats.total_users;
                document.getElementById('activeUsers').textContent = data.stats.active_users;
                document.getElementById('totalTracks').textContent = data.stats.total_tracks;
                document.getElementById('totalListens').textContent = data.stats.total_listens;
            }
        } else if (response.status === 403) {
            showMessage('У вас нет прав администратора', 'error');
            setTimeout(() => window.location.href = '/feed/admin', 2000);
        }
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
    }
}

// Загрузка популярных треков
async function loadPopularTracks() {
    const token = localStorage.getItem('token');
    const filter = document.getElementById('trackFilter')?.value || 'overall';
    const container = document.getElementById('popularTracksContainer');
    
    container.innerHTML = '<div class="loading">Загрузка...</div>';
    
    try {
        const response = await fetch(`${API_BASE}/admin/api/stats/popular-tracks?limit=50&filter=${filter}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                displayPopularTracks(data.tracks, filter);
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки треков:', error);
        container.innerHTML = '<div class="error-message">Ошибка загрузки данных</div>';
    }
}

// Отображение популярных треков
function displayPopularTracks(tracks, filter) {
    const container = document.getElementById('popularTracksContainer');
    
    if (filter === 'overall') {
        container.innerHTML = `
            <table class="users-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Обложка</th>
                        <th>Название</th>
                        <th>Исполнитель</th>
                        <th>Жанр</th>
                        <th>В избранном</th>
                        <th>Прослушиваний</th>
                    </tr>
                </thead>
                <tbody>
                    ${tracks.map((track, index) => `
                        <tr>
                            <td>${index + 1}</td>
                            <td><img src="${track.cover_url || '/static/default_cover.jpg'}" style="width: 40px; height: 40px; border-radius: 5px;"></td>
                            <td>${escapeHtml(track.title)}</td>
                            <td>${escapeHtml(track.artist)}</td>
                            <td>${escapeHtml(track.genre || '—')}</td>
                            <td>${track.favorites_count || 0}</td>
                            <td>${track.listens_count || 0}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    } else if (filter === 'by_age') {
        // Группировка по возрастным группам
        const ageGroups = {};
        tracks.forEach(track => {
            if (!ageGroups[track.age_group]) {
                ageGroups[track.age_group] = [];
            }
            ageGroups[track.age_group].push(track);
        });
        
        let html = '';
        for (const [ageGroup, groupTracks] of Object.entries(ageGroups)) {
            html += `
                <div class="chart-container">
                    <div class="chart-title">Возрастная группа: ${ageGroup}</div>
                    <table class="users-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Название</th>
                                <th>Исполнитель</th>
                                <th>Жанр</th>
                                <th>В избранном</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${groupTracks.slice(0, 10).map((track, index) => `
                                <tr>
                                    <td>${index + 1}</td>
                                    <td>${escapeHtml(track.title)}</td>
                                    <td>${escapeHtml(track.artist)}</td>
                                    <td>${escapeHtml(track.genre || '—')}</td>
                                    <td>${track.favorites_count || 0}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }
        container.innerHTML = html;
    } else if (filter === 'by_gender') {
        const genderGroups = {};
        tracks.forEach(track => {
            if (!genderGroups[track.gender]) {
                genderGroups[track.gender] = [];
            }
            genderGroups[track.gender].push(track);
        });
        
        let html = '';
        for (const [gender, groupTracks] of Object.entries(genderGroups)) {
            const genderName = gender === 'male' ? 'Мужчины' : gender === 'female' ? 'Женщины' : gender;
            html += `
                <div class="chart-container">
                    <div class="chart-title">${genderName}</div>
                    <table class="users-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Название</th>
                                <th>Исполнитель</th>
                                <th>Жанр</th>
                                <th>В избранном</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${groupTracks.slice(0, 10).map((track, index) => `
                                <tr>
                                    <td>${index + 1}</td>
                                    <td>${escapeHtml(track.title)}</td>
                                    <td>${escapeHtml(track.artist)}</td>
                                    <td>${escapeHtml(track.genre || '—')}</td>
                                    <td>${track.favorites_count || 0}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }
        container.innerHTML = html;
    }
}

// Загрузка анализа жанров
async function loadGenreAnalysis() {
    const token = localStorage.getItem('token');
    
    try {
        const response = await fetch(`${API_BASE}/admin/api/stats/genre-analysis`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                // График жанров по возрасту
                const ageData = processGenreAgeData(data.genre_by_age);
                createGenreAgeChart(ageData);
                
                // График жанров по полу
                const genderData = processGenreGenderData(data.genre_by_gender);
                createGenreGenderChart(genderData);
                
                // Общая статистика жанров
                createOverallGenreChart(data.overall_genre);
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки анализа жанров:', error);
    }
}

function processGenreAgeData(data) {
    const ageGroups = [...new Set(data.map(d => d.age_group))];
    const genres = [...new Set(data.map(d => d.genre))].slice(0, 10);
    
    const datasets = ageGroups.map(ageGroup => {
        return {
            label: ageGroup,
            data: genres.map(genre => {
                const item = data.find(d => d.genre === genre && d.age_group === ageGroup);
                return item ? item.favorites_count : 0;
            }),
            backgroundColor: getRandomColor(),
        };
    });
    
    return { labels: genres, datasets };
}

function processGenreGenderData(data) {
    const genders = [...new Set(data.map(d => d.gender))];
    const genres = [...new Set(data.map(d => d.genre))].slice(0, 10);
    
    const datasets = genders.map(gender => {
        const genderName = gender === 'male' ? 'Мужчины' : gender === 'female' ? 'Женщины' : gender;
        return {
            label: genderName,
            data: genres.map(genre => {
                const item = data.find(d => d.genre === genre && d.gender === gender);
                return item ? item.favorites_count : 0;
            }),
            backgroundColor: gender === 'male' ? '#4A90E2' : '#E24A8D',
        };
    });
    
    return { labels: genres, datasets };
}

function createGenreAgeChart(data) {
    const ctx = document.getElementById('genreAgeChart').getContext('2d');
    if (charts.genreAge) charts.genreAge.destroy();
    
    charts.genreAge = new Chart(ctx, {
        type: 'bar',
        data: data,
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'top' },
                title: { display: false }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

function createGenreGenderChart(data) {
    const ctx = document.getElementById('genreGenderChart').getContext('2d');
    if (charts.genreGender) charts.genreGender.destroy();
    
    charts.genreGender = new Chart(ctx, {
        type: 'bar',
        data: data,
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'top' }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

function createOverallGenreChart(data) {
    const ctx = document.getElementById('genreChart').getContext('2d');
    if (charts.overallGenre) charts.overallGenre.destroy();
    
    const topGenres = data.slice(0, 8);
    
    charts.overallGenre = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: topGenres.map(g => g.genre),
            datasets: [{
                data: topGenres.map(g => g.total_favorites),
                backgroundColor: topGenres.map(() => getRandomColor())
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'right' }
            }
        }
    });
}

// Загрузка сегментации пользователей
async function loadUserSegments() {
    const token = localStorage.getItem('token');
    
    try {
        const response = await fetch(`${API_BASE}/admin/api/stats/user-segments`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                // Распределение по возрасту
                createAgeDistributionChart(data.age_distribution);
                
                // Распределение по полу
                createGenderDistributionChart(data.gender_distribution);
                
                // Типы личности
                createPersonalityChart(data.personality_distribution);
                
                // Жанры по типам личности
                displayPersonalityGenres(data.personality_genres);
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки сегментации:', error);
    }
}

function createAgeDistributionChart(data) {
    const ctx = document.getElementById('ageDistributionChart').getContext('2d');
    if (charts.ageDist) charts.ageDist.destroy();
    
    charts.ageDist = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: data.map(d => d.age_group),
            datasets: [{
                data: data.map(d => d.count),
                backgroundColor: ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'bottom' }
            }
        }
    });
}

function createGenderDistributionChart(data) {
    const ctx = document.getElementById('genderDistributionChart').getContext('2d');
    if (charts.genderDist) charts.genderDist.destroy();
    
    const labels = data.map(d => d.gender === 'male' ? 'Мужчины' : d.gender === 'female' ? 'Женщины' : d.gender);
    
    charts.genderDist = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data.map(d => d.count),
                backgroundColor: ['#4A90E2', '#E24A8D', '#95A5A6']
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'bottom' }
            }
        }
    });
}

function createPersonalityChart(data) {
    const ctx = document.getElementById('personalityChart').getContext('2d');
    if (charts.personality) charts.personality.destroy();
    
    charts.personality = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(d => d.personality_type),
            datasets: [{
                label: 'Количество пользователей',
                data: data.map(d => d.count),
                backgroundColor: ['#FF6B6B', '#4ECDC4', '#FFEAA7']
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false }
            }
        }
    });
}

function displayPersonalityGenres(data) {
    const container = document.getElementById('personalityGenres');
    let html = '';
    
    for (const [personality, genres] of Object.entries(data)) {
        html += `
            <div style="margin-bottom: 20px;">
                <h4 style="color: var(--text-primary); margin-bottom: 10px;">${personality}</h4>
                <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                    ${genres.map(g => `
                        <span style="background: #667eea; color: white; padding: 5px 12px; border-radius: 20px; font-size: 14px;">
                            ${escapeHtml(g.genre)} (${g.count})
                        </span>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    container.innerHTML = html;
}

// Загрузка списка пользователей
let currentUserPage = 1;
let userSearchTerm = '';

async function loadUsers(page = 1) {
    const token = localStorage.getItem('token');
    const container = document.getElementById('usersTableContainer');
    
    container.innerHTML = '<div class="loading">Загрузка пользователей...</div>';
    
    try {
        const response = await fetch(
            `${API_BASE}/admin/api/users?page=${page}&per_page=20&search=${userSearchTerm}`,
            { headers: { 'Authorization': `Bearer ${token}` } }
        );
        
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                displayUsers(data);
                currentUserPage = page;
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки пользователей:', error);
        container.innerHTML = '<div class="error-message">Ошибка загрузки данных</div>';
    }
}

function displayUsers(data) {
    const container = document.getElementById('usersTableContainer');
    
    let html = `
        <table class="users-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Пользователь</th>
                    <th>Email</th>
                    <th>Возраст</th>
                    <th>Пол</th>
                    <th>Экстраверсия</th>
                    <th>Открытость</th>
                    <th>Избранное</th>
                    <th>Прослушиваний</th>
                    <th>Статус</th>
                    <th>Действия</th>
                </tr>
            </thead>
            <tbody>
                ${data.users.map(user => `
                    <tr>
                        <td>${user.id}</td>
                        <td>${escapeHtml(user.username)}</td>
                        <td>${escapeHtml(user.email || '—')}</td>
                        <td>${user.age || '—'}</td>
                        <td>${user.gender === 'male' ? 'М' : user.gender === 'female' ? 'Ж' : '—'}</td>
                        <td>${user.extraversion || '—'}</td>
                        <td>${user.openness || '—'}</td>
                        <td>${user.favorites_count || 0}</td>
                        <td>${user.listens_count || 0}</td>
                        <td>
                            ${user.is_admin ? '<span class="admin-badge">Админ</span>' : 'Пользователь'}
                        </td>
                        <td>
                            <button onclick="toggleAdminStatus(${user.id})" class="page-btn" style="padding: 5px 10px; font-size: 12px;">
                                ${user.is_admin ? 'Снять админа' : 'Сделать админом'}
                            </button>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    // Добавляем пагинацию
    if (data.total_pages > 1) {
        html += '<div class="pagination">';
        for (let i = 1; i <= data.total_pages; i++) {
            html += `<button class="page-btn ${i === data.page ? 'active' : ''}" onclick="loadUsers(${i})">${i}</button>`;
        }
        html += '</div>';
    }
    
    container.innerHTML = html;
}

async function toggleAdminStatus(userId) {
    const token = localStorage.getItem('token');
    
    try {
        const response = await fetch(`${API_BASE}/admin/api/users/${userId}/toggle-admin`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            showMessage(data.message, 'success');
            loadUsers(currentUserPage);
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showMessage('Ошибка изменения статуса', 'error');
    }
}

function searchUsers() {
    userSearchTerm = document.getElementById('userSearch').value;
    loadUsers(1);
}

// Вспомогательные функции
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getRandomColor() {
    const colors = [
        '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
        '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2'
    ];
    return colors[Math.floor(Math.random() * colors.length)];
}

function showMessage(message, type) {
    const container = document.getElementById('messageContainer');
    container.innerHTML = `<div class="${type}-message">${message}</div>`;
    setTimeout(() => container.innerHTML = '', 3000);
}

// Инициализация табов
function initTabs() {
    const tabs = document.querySelectorAll('.admin-tab');
    const contents = document.querySelectorAll('.tab-content');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabId = tab.dataset.tab;
            
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            contents.forEach(c => c.classList.remove('active'));
            document.getElementById(`tab-${tabId}`).classList.add('active');
            
            // Загружаем данные для соответствующего таба
            if (tabId === 'overview') {
                // Уже загружено
            } else if (tabId === 'tracks') {
                loadPopularTracks();
            } else if (tabId === 'genres') {
                loadGenreAnalysis();
            } else if (tabId === 'segments') {
                loadUserSegments();
            } else if (tabId === 'users') {
                loadUsers();
            }
        });
    });
}

// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', async () => {
    if (await checkAdminAccess()) {
        await loadOverviewStats();
        initTabs();
        
        // Загружаем топ треков для превью
        const token = localStorage.getItem('token');
        try {
            const response = await fetch(`${API_BASE}/admin/api/stats/popular-tracks?limit=5`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    const preview = document.getElementById('topTracksPreview');
                    preview.innerHTML = data.tracks.map((track, i) => `
                        <div style="display: flex; align-items: center; padding: 10px; border-bottom: 1px solid var(--card-border);">
                            <span style="width: 30px; color: var(--text-secondary);">${i + 1}.</span>
                            <img src="${track.cover_url || '/static/default_cover.jpg'}" style="width: 30px; height: 30px; border-radius: 5px; margin-right: 10px;">
                            <div style="flex: 1;">
                                <div style="font-weight: 500;">${escapeHtml(track.title)}</div>
                                <div style="font-size: 12px; color: var(--text-secondary);">${escapeHtml(track.artist)}</div>
                            </div>
                            <span style="color: #667eea;">❤️ ${track.favorites_count || 0}</span>
                        </div>
                    `).join('');
                }
            }
        } catch (error) {
            console.error('Ошибка загрузки топ треков:', error);
        }
    }
});