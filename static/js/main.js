const API_BASE = 'http://localhost:5000/api';

// Регистрация
document.getElementById('registerForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    const res = await fetch(`${API_BASE}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password })
    });
    const data = await res.json();
    if (res.ok) {
        alert('Регистрация успешна, теперь войдите');
        window.location.href = '/login.html';
    } else {
        alert(data.error);
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
async function addToFavorites(trackId) {
    const token = localStorage.getItem('token');
    if (!token) {
        alert('Войдите, чтобы добавить в избранное');
        return;
    }
    const res = await fetch(`${API_BASE}/favorites`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ track_id: trackId })
    });
    if (res.ok) {
        alert('Добавлено в избранное');
    } else {
        const data = await res.json();
        alert(data.error);
    }
}

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