window.API_BASE = window.API_BASE || 'http://localhost:5000';
let charts = {}; 

function formatNumber(num) {
    if (num >= 1e6) return (num / 1e6).toFixed(1) + 'M';
    if (num >= 1e3) return (num / 1e3).toFixed(0) + 'K';
    return num.toString();
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

function showMessage(msg, type) {
    const container = document.getElementById('messageContainer');
    if (!container) return;
    container.innerHTML = `<div class="${type}-message">${msg}</div>`;
    setTimeout(() => container.innerHTML = '', 3000);
}

async function checkAdminAccess() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/login';
        return false;
    }
    return true;
}

async function loadOverviewStats() {
    const token = localStorage.getItem('token');
    try {
        const resp = await fetch(`${API_BASE}/admin/api/stats/overview`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!resp.ok) throw new Error('HTTP error');
        const data = await resp.json();
        if (data.success && data.stats) {
            document.getElementById('totalUsers').textContent = data.stats.total_users ?? 0;
            document.getElementById('activeUsers').textContent = data.stats.active_users ?? 0;
            document.getElementById('totalTracks').textContent = formatNumber(data.stats.total_tracks ?? 0);
            document.getElementById('totalListens').textContent = formatNumber(data.stats.total_listens ?? 0);
        } else {
            throw new Error('Invalid response');
        }
    } catch (err) {
        console.error('loadOverviewStats error:', err);
        showMessage('Ошибка загрузки статистики', 'error');
        document.getElementById('totalUsers').textContent = '?';
        document.getElementById('activeUsers').textContent = '?';
        document.getElementById('totalTracks').textContent = '?';
        document.getElementById('totalListens').textContent = '?';
    }
}

async function createActivityChart() {
    const canvas = document.getElementById('activityChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (charts.activity) charts.activity.destroy();

    const token = localStorage.getItem('token');
    let labels = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
    let values = [0,0,0,0,0,0,0];
    try {
        const resp = await fetch(`${API_BASE}/admin/api/stats/activity`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (resp.ok) {
            const data = await resp.json();
            if (data.success && data.activity) {
                labels = data.activity.map(item => item.day);
                values = data.activity.map(item => item.count);
            }
        }
    } catch(e) { console.warn('Activity data not available, using zeros'); }

    charts.activity = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Прослушивания',
                data: values,
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.15)',
                borderWidth: 3,
                tension: 0.4,
                fill: true,
                pointBackgroundColor: '#667eea',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 5,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: (ctx) => `${formatNumber(ctx.parsed.y)} прослушиваний` } }
            },
            scales: {
                y: { beginAtZero: true, ticks: { callback: (val) => formatNumber(val) } }
            }
        }
    });
}

async function loadPopularTracks() {
    const filter = document.getElementById('trackFilter')?.value || 'overall';
    const container = document.getElementById('popularTracksContainer');
    if (!container) return;
    container.innerHTML = '<div class="loading">Загрузка...</div>';

    const token = localStorage.getItem('token');
    try {
        const resp = await fetch(`${API_BASE}/admin/api/stats/popular-tracks?limit=50&filter=${filter}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!resp.ok) throw new Error('Network error');
        const data = await resp.json();
        if (data.success && data.tracks) {
            displayPopularTracks(data.tracks, filter);
        } else {
            container.innerHTML = '<div class="error-message">Нет данных</div>';
        }
    } catch(err) {
        console.error(err);
        container.innerHTML = '<div class="error-message">Ошибка загрузки треков</div>';
    }
}

function displayPopularTracks(tracks, filter) {
    const container = document.getElementById('popularTracksContainer');
    if (!tracks.length) {
        container.innerHTML = '<div class="error-message">Нет данных</div>';
        return;
    }

    if (filter === 'overall') {
        let html = `<table class="users-table"><thead><tr>
            <th>#</th><th>Обложка</th><th>Название</th><th>Исполнитель</th><th>Жанр</th>
            <th>В избранном</th><th>Прослушиваний</th>
        </tr></thead><tbody>`;
        tracks.forEach((track, idx) => {
            html += `<tr>
                <td>${idx+1}</td>
                <td><img src="${track.cover_url || '/static/default_cover.jpg'}" style="width:40px;height:40px;border-radius:5px;"></td>
                <td>${escapeHtml(track.title)}</td>
                <td>${escapeHtml(track.artist)}</td>
                <td>${escapeHtml(track.genre || '—')}</td>
                <td>${track.favorites_count || 0}</td>
                <td>${track.listens_count || 0}</td>
            </tr>`;
        });
        html += '</tbody></table>';
        container.innerHTML = html;
    }
    else if (filter === 'by_age') {
        
        const groups = {};
        tracks.forEach(t => { groups[t.age_group] = groups[t.age_group] || []; groups[t.age_group].push(t); });
        let html = '';
        for (const [age, items] of Object.entries(groups)) {
            html += `<div class="chart-container"><div class="chart-title">Возраст: ${age}</div>
            <table class="users-table"><thead><tr><th>#</th><th>Название</th><th>Исполнитель</th><th>В избранном</th></tr></thead><tbody>`;
            items.slice(0,10).forEach((t, idx) => {
                html += `<tr><td>${idx+1}</td><td>${escapeHtml(t.title)}</td><td>${escapeHtml(t.artist)}</td><td>${t.favorites_count}</td></tr>`;
            });
            html += '</tbody></table></div>';
        }
        container.innerHTML = html || '<div>Нет данных для этой группы</div>';
    }
    else if (filter === 'by_gender') {
        const groups = {};
        tracks.forEach(t => { groups[t.gender] = groups[t.gender] || []; groups[t.gender].push(t); });
        let html = '';
        for (const [gender, items] of Object.entries(groups)) {
            const genderName = gender === 'male' ? 'Мужчины' : gender === 'female' ? 'Женщины' : gender;
            html += `<div class="chart-container"><div class="chart-title">${genderName}</div>
            <table class="users-table"><thead><tr><th>#</th><th>Название</th><th>Исполнитель</th><th>В избранном</th></tr></thead><tbody>`;
            items.slice(0,10).forEach((t, idx) => {
                html += `<tr><td>${idx+1}</td><td>${escapeHtml(t.title)}</td><td>${escapeHtml(t.artist)}</td><td>${t.favorites_count}</td></tr>`;
            });
            html += '</tbody></table></div>';
        }
        container.innerHTML = html || '<div>Нет данных</div>';
    }
}

async function loadGenreAnalysis() {
    const token = localStorage.getItem('token');
    try {
        const resp = await fetch(`${API_BASE}/admin/api/stats/genre-analysis`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!resp.ok) throw new Error();
        const data = await resp.json();
        if (data.success) {
            
            createOverallGenreChart(data.overall_genre);
            createGenreAgeChart(data.genre_by_age);
            createGenreGenderChart(data.genre_by_gender);
        } else {
            throw new Error('Invalid data');
        }
    } catch(err) {
        console.error(err);
        showMessage('Ошибка загрузки анализа жанров', 'error');
    }
}

function createOverallGenreChart(genres) {
    const ctx = document.getElementById('genreChart')?.getContext('2d');
    if (!ctx) return;
    if (charts.overallGenre) charts.overallGenre.destroy();
    const top = genres.slice(0,8);
    const labels = top.map(g => g.genre);
    const values = top.map(g => g.total_favorites || g.unique_listeners);
    charts.overallGenre = new Chart(ctx, {
        type: 'doughnut',
        data: { labels, datasets: [{ data: values, backgroundColor: getRandomColors(8) }] },
        options: { responsive: true, plugins: { legend: { position: 'right' } } }
    });
}

function createGenreAgeChart(data) {
    const ctx = document.getElementById('genreAgeChart')?.getContext('2d');
    if (!ctx) return;
    if (charts.genreAge) charts.genreAge.destroy();
    
    const ageGroups = [...new Set(data.map(d => d.age_group))];
    const genres = [...new Set(data.map(d => d.genre))].slice(0,10);
    const datasets = ageGroups.map(age => ({
        label: age,
        data: genres.map(genre => {
            const item = data.find(d => d.genre === genre && d.age_group === age);
            return item ? item.favorites_count : 0;
        }),
        backgroundColor: `hsl(${ageGroups.indexOf(age) * 60}, 70%, 60%)`
    }));
    charts.genreAge = new Chart(ctx, { type: 'bar', data: { labels: genres, datasets }, options: { responsive: true, scales: { y: { beginAtZero: true } } } });
}

function createGenreGenderChart(data) {
    const ctx = document.getElementById('genreGenderChart')?.getContext('2d');
    if (!ctx) return;
    if (charts.genreGender) charts.genreGender.destroy();
    const genders = [...new Set(data.map(d => d.gender))];
    const genres = [...new Set(data.map(d => d.genre))].slice(0,10);
    const datasets = genders.map(g => ({
        label: g === 'male' ? 'Мужчины' : 'Женщины',
        data: genres.map(genre => {
            const item = data.find(d => d.genre === genre && d.gender === g);
            return item ? item.favorites_count : 0;
        }),
        backgroundColor: g === 'male' ? '#4A90E2' : '#E24A8D'
    }));
    charts.genreGender = new Chart(ctx, { type: 'bar', data: { labels: genres, datasets }, options: { responsive: true, scales: { y: { beginAtZero: true } } } });
}

async function loadUserSegments() {
    const token = localStorage.getItem('token');
    try {
        const resp = await fetch(`${API_BASE}/admin/api/stats/user-segments`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!resp.ok) throw new Error();
        const data = await resp.json();
        if (data.success) {
            createAgeDistributionChart(data.age_distribution);
            createGenderDistributionChart(data.gender_distribution);
            createPersonalityChart(data.personality_distribution);
            displayPersonalityGenres(data.personality_genres);
        } else throw new Error();
    } catch(err) {
        console.error(err);
        showMessage('Ошибка загрузки сегментации', 'error');
    }
}

function createAgeDistributionChart(data) {
    const ctx = document.getElementById('ageDistributionChart')?.getContext('2d');
    if (!ctx) return;
    if (charts.ageDist) charts.ageDist.destroy();
    charts.ageDist = new Chart(ctx, {
        type: 'pie',
        data: { labels: data.map(d => d.age_group), datasets: [{ data: data.map(d => d.count), backgroundColor: ['#FF6B6B','#4ECDC4','#45B7D1','#96CEB4','#FFEAA7'] }] },
        options: { responsive: true, plugins: { tooltip: { callbacks: { label: (ctx) => `${ctx.label}: ${ctx.parsed}` } } } }
    });
}

function createGenderDistributionChart(data) {
    const ctx = document.getElementById('genderDistributionChart')?.getContext('2d');
    if (!ctx) return;
    if (charts.genderDist) charts.genderDist.destroy();
    const labels = data.map(d => d.gender === 'male' ? 'Мужчины' : d.gender === 'female' ? 'Женщины' : d.gender);
    charts.genderDist = new Chart(ctx, {
        type: 'doughnut',
        data: { labels, datasets: [{ data: data.map(d => d.count), backgroundColor: ['#4A90E2','#E24A8D'] }] },
        options: { responsive: true }
    });
}

function createPersonalityChart(data) {
    const ctx = document.getElementById('personalityChart')?.getContext('2d');
    if (!ctx) return;
    if (charts.personality) charts.personality.destroy();
    charts.personality = new Chart(ctx, {
        type: 'bar',
        data: { labels: data.map(d => d.personality_type), datasets: [{ label: 'Пользователи', data: data.map(d => d.count), backgroundColor: '#667eea' }] },
        options: { responsive: true, plugins: { legend: { display: false } } }
    });
}

function displayPersonalityGenres(genresObj) {
    const container = document.getElementById('personalityGenres');
    if (!container) return;
    let html = '';
    for (const [personality, genres] of Object.entries(genresObj)) {
        html += `<div><h4>${personality}</h4><div class="genre-tags">`;
        genres.forEach(g => { html += `<span class="tag">${escapeHtml(g.genre)} (${g.count})</span>`; });
        html += `</div></div>`;
    }
    container.innerHTML = html || '<div>Нет данных</div>';
}

let currentUserPage = 1;
let userSearchTerm = '';

async function loadUsers(page = 1) {
    const token = localStorage.getItem('token');
    const container = document.getElementById('usersTableContainer');
    if (!container) return;
    container.innerHTML = '<div class="loading">Загрузка...</div>';
    try {
        const resp = await fetch(`${API_BASE}/admin/api/users?page=${page}&per_page=20&search=${encodeURIComponent(userSearchTerm)}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!resp.ok) throw new Error();
        const data = await resp.json();
        if (data.success) {
            displayUsers(data);
            currentUserPage = page;
        } else throw new Error();
    } catch(err) {
        console.error(err);
        container.innerHTML = '<div class="error-message">Ошибка загрузки пользователей</div>';
    }
}

function displayUsers(data) {
    const container = document.getElementById('usersTableContainer');
    let html = `<table class="users-table"><thead><tr>
        <th>ID</th><th>Имя</th><th>Email</th><th>Возраст</th><th>Пол</th>
        <th>Экстраверсия</th><th>Открытость</th><th>Избранное</th><th>Прослушиваний</th><th>Статус</th><th>Действия</th>
    </tr></thead><tbody>`;
    data.users.forEach(user => {
        html += `<tr>
            <td>${user.id}</td>
            <td>${escapeHtml(user.username)}</td>
            <td>${escapeHtml(user.email || '—')}</td>
            <td>${user.age || '—'}</td>
            <td>${user.gender === 'male' ? 'М' : user.gender === 'female' ? 'Ж' : '—'}</td>
            <td>${user.extraversion || '—'}</td>
            <td>${user.openness || '—'}</td>
            <td>${user.favorites_count || 0}</td>
            <td>${user.listens_count || 0}</td>
            <td>${user.is_admin ? '<span class="admin-badge">Админ</span>' : 'Пользователь'}</td>
            <td><button onclick="toggleAdminStatus(${user.id})" class="page-btn">${user.is_admin ? 'Снять админа' : 'Сделать админом'}</button></td>
        </tr>`;
    });
    html += `</tbody></table>`;
    if (data.total_pages > 1) {
        html += `<div class="pagination">`;
        for (let i = 1; i <= data.total_pages; i++) {
            html += `<button class="page-btn ${i === data.page ? 'active' : ''}" onclick="loadUsers(${i})">${i}</button>`;
        }
        html += `</div>`;
    }
    container.innerHTML = html;
}

async function toggleAdminStatus(userId) {
    const token = localStorage.getItem('token');
    try {
        const resp = await fetch(`${API_BASE}/admin/api/users/${userId}/toggle-admin`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await resp.json();
        if (resp.ok && data.success) {
            showMessage(data.message, 'success');
            loadUsers(currentUserPage);
        } else {
            showMessage(data.error || 'Ошибка', 'error');
        }
    } catch(err) {
        console.error(err);
        showMessage('Ошибка сети', 'error');
    }
}

function searchUsers() {
    userSearchTerm = document.getElementById('userSearch')?.value || '';
    loadUsers(1);
}

function initTabs() {
    const tabs = document.querySelectorAll('.admin-tab');
    const contents = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabId = tab.dataset.tab;
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            contents.forEach(c => c.classList.remove('active'));
            document.getElementById(`tab-${tabId}`)?.classList.add('active');
            if (tabId === 'tracks') loadPopularTracks();
            else if (tabId === 'genres') loadGenreAnalysis();
            else if (tabId === 'segments') loadUserSegments();
            else if (tabId === 'users') loadUsers();
        });
    });
}

function getRandomColors(n) {
    const colors = ['#FF6B6B','#4ECDC4','#45B7D1','#96CEB4','#FFEAA7','#DDA0DD','#98D8C8','#F7DC6F'];
    return colors.slice(0,n);
}

document.addEventListener('DOMContentLoaded', async () => {
    if (await checkAdminAccess()) {
        await loadOverviewStats();
        await createActivityChart(); 
        initTabs();
        
        const preview = document.getElementById('topTracksPreview');
        if (preview) {
            
            preview.innerHTML = '<div class="loading">Загрузка...</div>';
            loadPopularTracks().catch(() => { preview.innerHTML = '<div>Нет данных</div>'; });
        }
    }
});