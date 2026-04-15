const API_BASE = 'http://localhost:5000';
let charts = {};

// ДЕМО-ДАННЫЕ ДЛЯ ГРАФИКОВ
// ДЕМО-ДАННЫЕ ДЛЯ ГРАФИКОВ (масштаб: 350 пользователей, 600 000 треков)
const DEMO_DATA = {
    // Активность по дням недели (прослушивания)
    activityByDay: {
        'Пн': 2847,
        'Вт': 3156,
        'Ср': 3421,
        'Чт': 3892,
        'Пт': 5234,
        'Сб': 7845,
        'Вс': 6923
    },
    
    // Распределение по жанрам (в процентах от прослушиваний)
    genreDistribution: {
        'Поп': 28,
        'Рок': 22,
        'Хип-хоп': 15,
        'Электроника': 12,
        'R&B': 8,
        'Классика': 6,
        'Джаз': 5,
        'Метал': 4
    },
    
    // Популярность жанров по возрастным группам (количество прослушиваний)
    genreByAge: {
        '18-24': { 
            'Хип-хоп': 12500, 
            'Поп': 11800, 
            'Электроника': 9500, 
            'R&B': 7200, 
            'Рок': 5800,
            'Латино': 4200,
            'Инди': 3800
        },
        '25-34': { 
            'Поп': 15600, 
            'Рок': 13400, 
            'Хип-хоп': 11200, 
            'Электроника': 9800, 
            'R&B': 8500,
            'Джаз': 4500,
            'Классика': 3200
        },
        '35-44': { 
            'Рок': 18200, 
            'Поп': 14500, 
            'Джаз': 7800, 
            'Классика': 6500, 
            'Электроника': 5400,
            'Метал': 4800,
            'Блюз': 3500
        },
        '45-54': { 
            'Рок': 15600, 
            'Классика': 9800, 
            'Поп': 9200, 
            'Джаз': 7500, 
            'Блюз': 5200,
            'Метал': 3800,
            'Фолк': 2900
        },
        '55+': { 
            'Классика': 12400, 
            'Джаз': 8900, 
            'Рок': 6500, 
            'Фолк': 4800, 
            'Поп': 4200,
            'Блюз': 3600,
            'Кантри': 2500
        }
    },
    
    // Популярность жанров по полу (количество прослушиваний)
    genreByGender: {
        'Мужчины': { 
            'Рок': 45800, 
            'Хип-хоп': 32500, 
            'Электроника': 24800, 
            'Метал': 15600, 
            'Поп': 14200,
            'Джаз': 8900,
            'Классика': 5600
        },
        'Женщины': { 
            'Поп': 52400, 
            'R&B': 25600, 
            'Рок': 18400, 
            'Классика': 15200, 
            'Джаз': 12800,
            'Электроника': 9800,
            'Хип-хоп': 7500
        }
    },
    
    // Распределение по возрастам (всего 350 пользователей)
    ageDistribution: [
        { age_group: '18-24', count: 78 },
        { age_group: '25-34', count: 112 },
        { age_group: '35-44', count: 85 },
        { age_group: '45-54', count: 52 },
        { age_group: '55+', count: 23 }
    ],
    
    // Распределение по полу
    genderDistribution: [
        { gender: 'male', count: 168 },
        { gender: 'female', count: 182 }
    ],
    
    // Типы личности (на основе экстраверсии)
    personalityDistribution: [
        { personality_type: 'Экстраверты', count: 145, avg_extraversion: 4.3 },
        { personality_type: 'Амбиверты', count: 128, avg_extraversion: 3.1 },
        { personality_type: 'Интроверты', count: 77, avg_extraversion: 1.7 }
    ],
    
    // Открытость опыту
    opennessDistribution: [
        { openness_type: 'Высокая открытость', count: 156, avg_openness: 4.4 },
        { openness_type: 'Средняя открытость', count: 132, avg_openness: 3.0 },
        { openness_type: 'Низкая открытость', count: 62, avg_openness: 1.8 }
    ],
    
    // Жанры по типам личности (топ-5 для каждого)
    personalityGenres: {
        'Экстраверты': [
            { genre: 'Поп', count: 18700 },
            { genre: 'Хип-хоп', count: 15400 },
            { genre: 'Электроника', count: 13200 },
            { genre: 'Рок', count: 11800 },
            { genre: 'R&B', count: 9500 }
        ],
        'Амбиверты': [
            { genre: 'Рок', count: 15200 },
            { genre: 'Поп', count: 13800 },
            { genre: 'Джаз', count: 8200 },
            { genre: 'Классика', count: 6500 },
            { genre: 'Электроника', count: 5800 }
        ],
        'Интроверты': [
            { genre: 'Классика', count: 11200 },
            { genre: 'Джаз', count: 8900 },
            { genre: 'Инди', count: 6200 },
            { genre: 'Амбиент', count: 4800 },
            { genre: 'Фолк', count: 3500 }
        ]
    },
    
    // Топ треков (глобальный)
    topTracks: [
        { title: 'Blinding Lights', artist: 'The Weeknd', favorites_count: 187, listens_count: 12450, genre: 'Поп' },
        { title: 'Bohemian Rhapsody', artist: 'Queen', favorites_count: 176, listens_count: 11340, genre: 'Рок' },
        { title: 'Shape of You', artist: 'Ed Sheeran', favorites_count: 165, listens_count: 10890, genre: 'Поп' },
        { title: 'Stairway to Heaven', artist: 'Led Zeppelin', favorites_count: 158, listens_count: 10230, genre: 'Рок' },
        { title: 'Smells Like Teen Spirit', artist: 'Nirvana', favorites_count: 149, listens_count: 9870, genre: 'Рок' },
        { title: 'Billie Jean', artist: 'Michael Jackson', favorites_count: 142, listens_count: 9450, genre: 'Поп' },
        { title: 'Lose Yourself', artist: 'Eminem', favorites_count: 138, listens_count: 9120, genre: 'Хип-хоп' },
        { title: 'Hotel California', artist: 'Eagles', favorites_count: 135, listens_count: 8980, genre: 'Рок' },
        { title: 'Rolling in the Deep', artist: 'Adele', favorites_count: 128, listens_count: 8450, genre: 'Поп' },
        { title: 'Sweet Child O\' Mine', artist: 'Guns N\' Roses', favorites_count: 125, listens_count: 8230, genre: 'Рок' },
        { title: 'Someone Like You', artist: 'Adele', favorites_count: 122, listens_count: 8010, genre: 'Поп' },
        { title: 'Wonderwall', artist: 'Oasis', favorites_count: 119, listens_count: 7840, genre: 'Рок' },
        { title: 'Uptown Funk', artist: 'Mark Ronson ft. Bruno Mars', favorites_count: 116, listens_count: 7650, genre: 'Фанк' },
        { title: 'Thinking Out Loud', artist: 'Ed Sheeran', favorites_count: 114, listens_count: 7480, genre: 'Поп' },
        { title: 'Back in Black', artist: 'AC/DC', favorites_count: 112, listens_count: 7320, genre: 'Рок' }
    ],
    
    // Топ треков по возрастным группам
    topTracksByAge: {
        '18-24': [
            { title: 'Bad Guy', artist: 'Billie Eilish', favorites_count: 89 },
            { title: 'Sicko Mode', artist: 'Travis Scott', favorites_count: 82 },
            { title: 'Good 4 U', artist: 'Olivia Rodrigo', favorites_count: 78 },
            { title: 'Industry Baby', artist: 'Lil Nas X', favorites_count: 75 },
            { title: 'Stay', artist: 'The Kid LAROI', favorites_count: 72 }
        ],
        '25-34': [
            { title: 'Blinding Lights', artist: 'The Weeknd', favorites_count: 95 },
            { title: 'Shape of You', artist: 'Ed Sheeran', favorites_count: 91 },
            { title: 'Uptown Funk', artist: 'Mark Ronson', favorites_count: 87 },
            { title: 'Rolling in the Deep', artist: 'Adele', favorites_count: 84 },
            { title: 'Get Lucky', artist: 'Daft Punk', favorites_count: 80 }
        ],
        '35-44': [
            { title: 'Smells Like Teen Spirit', artist: 'Nirvana', favorites_count: 78 },
            { title: 'Wonderwall', artist: 'Oasis', favorites_count: 74 },
            { title: 'Lose Yourself', artist: 'Eminem', favorites_count: 71 },
            { title: 'Billie Jean', artist: 'Michael Jackson', favorites_count: 68 },
            { title: 'Sweet Child O\' Mine', artist: 'Guns N\' Roses', favorites_count: 65 }
        ],
        '45-54': [
            { title: 'Bohemian Rhapsody', artist: 'Queen', favorites_count: 62 },
            { title: 'Stairway to Heaven', artist: 'Led Zeppelin', favorites_count: 58 },
            { title: 'Hotel California', artist: 'Eagles', favorites_count: 55 },
            { title: 'Back in Black', artist: 'AC/DC', favorites_count: 52 },
            { title: 'Comfortably Numb', artist: 'Pink Floyd', favorites_count: 48 }
        ],
        '55+': [
            { title: 'Imagine', artist: 'John Lennon', favorites_count: 45 },
            { title: 'Like a Rolling Stone', artist: 'Bob Dylan', favorites_count: 42 },
            { title: 'What a Wonderful World', artist: 'Louis Armstrong', favorites_count: 40 },
            { title: 'Yesterday', artist: 'The Beatles', favorites_count: 38 },
            { title: 'Bridge Over Troubled Water', artist: 'Simon & Garfunkel', favorites_count: 35 }
        ]
    },
    
    // Детальная статистика по базе
    databaseStats: {
        total_users: 347,
        active_users_week: 289,
        active_users_month: 312,
        total_tracks: 612847,
        total_artists: 89432,
        total_albums: 124567,
        total_listens: 1847230,
        total_favorites: 45680,
        avg_session_minutes: 47,
        new_users_week: 23,
        new_users_month: 78
    },
    
    // Статистика по странам (если нужно)
    countriesData: [
        { country: 'Россия', users: 234, percentage: 67.4 },
        { country: 'Казахстан', users: 34, percentage: 9.8 },
        { country: 'Беларусь', users: 28, percentage: 8.1 },
        { country: 'Украина', users: 21, percentage: 6.1 },
        { country: 'Другие', users: 30, percentage: 8.6 }
    ],
    
    // Почасовая активность
    hourlyActivity: {
        '00:00': 1200, '01:00': 850, '02:00': 620, '03:00': 480,
        '04:00': 520, '05:00': 890, '06:00': 2100, '07:00': 4500,
        '08:00': 6800, '09:00': 5200, '10:00': 4800, '11:00': 5100,
        '12:00': 6200, '13:00': 5800, '14:00': 5600, '15:00': 5900,
        '16:00': 7200, '17:00': 8900, '18:00': 11200, '19:00': 13500,
        '20:00': 14800, '21:00': 15200, '22:00': 12800, '23:00': 7800
    },
    
    // Топ исполнителей
    topArtists: [
        { name: 'Queen', listeners: 234, favorites: 1250, genre: 'Рок' },
        { name: 'The Beatles', listeners: 218, favorites: 1180, genre: 'Рок' },
        { name: 'Michael Jackson', listeners: 205, favorites: 1050, genre: 'Поп' },
        { name: 'Led Zeppelin', listeners: 189, favorites: 980, genre: 'Рок' },
        { name: 'Pink Floyd', listeners: 176, favorites: 920, genre: 'Рок' },
        { name: 'Eminem', listeners: 168, favorites: 890, genre: 'Хип-хоп' },
        { name: 'Adele', listeners: 159, favorites: 850, genre: 'Поп' },
        { name: 'Nirvana', listeners: 152, favorites: 820, genre: 'Рок' },
        { name: 'The Weeknd', listeners: 148, favorites: 790, genre: 'Поп' },
        { name: 'Ed Sheeran', listeners: 142, favorites: 760, genre: 'Поп' }
    ]
};
// Флаг использования демо-данных
let useDemoData = false;

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
            if (data.success && data.stats) {
                document.getElementById('totalUsers').textContent = data.stats.total_users || DEMO_DATA.databaseStats.total_users;
                document.getElementById('activeUsers').textContent = data.stats.active_users || DEMO_DATA.databaseStats.active_users_week;
                document.getElementById('totalTracks').textContent = formatNumber(data.stats.total_tracks || DEMO_DATA.databaseStats.total_tracks);
                document.getElementById('totalListens').textContent = formatNumber(data.stats.total_listens || DEMO_DATA.databaseStats.total_listens);
                useDemoData = false;
            } else {
                loadDemoStats();
            }
        } else {
            loadDemoStats();
        }
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
        loadDemoStats();
    }
    
    // Небольшая задержка перед созданием графика
    setTimeout(() => {
        createActivityChart();
    }, 100);
}

function loadDemoStats() {
    useDemoData = true;
    document.getElementById('totalUsers').textContent = DEMO_DATA.databaseStats.total_users;
    document.getElementById('activeUsers').textContent = DEMO_DATA.databaseStats.active_users_week;
    document.getElementById('totalTracks').textContent = formatNumber(DEMO_DATA.databaseStats.total_tracks);
    document.getElementById('totalListens').textContent = formatNumber(DEMO_DATA.databaseStats.total_listens);
}

// Добавьте обработчик изменения размера окна
window.addEventListener('resize', () => {
    // Перерисовываем график при изменении размера с небольшой задержкой
    if (charts.activity) {
        clearTimeout(window.resizeTimer);
        window.resizeTimer = setTimeout(() => {
            if (document.getElementById('activityChart')) {
                createActivityChart();
            }
        }, 250);
    }
});
// Создание графика активности по дням
function createActivityChart() {
    const canvas = document.getElementById('activityChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (charts.activity) charts.activity.destroy();
    
    // Устанавливаем фиксированные размеры canvas
    canvas.style.width = '100%';
    canvas.style.height = '300px';
    canvas.width = canvas.offsetWidth;
    canvas.height = 300;
    
    const days = Object.keys(DEMO_DATA.activityByDay);
    const values = Object.values(DEMO_DATA.activityByDay);
    
    charts.activity = new Chart(ctx, {
        type: 'line',
        data: {
            labels: days,
            datasets: [{
                label: 'Количество прослушиваний',
                data: values,
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.15)',
                borderWidth: 3,
                tension: 0.4,
                fill: true,
                pointBackgroundColor: '#667eea',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 5,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false, // Важно! Позволяет управлять высотой через CSS
            layout: {
                padding: {
                    top: 20,
                    bottom: 10
                }
            },
            plugins: {
                legend: { 
                    display: false 
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    callbacks: {
                        label: (context) => {
                            const value = context.parsed.y;
                            return ` ${formatNumber(value)} прослушиваний`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { 
                        color: 'rgba(0, 0, 0, 0.05)' 
                    },
                    ticks: {
                        callback: (value) => formatNumber(value),
                        stepSize: 1000
                    },
                    title: {
                        display: true,
                        text: 'Прослушивания',
                        color: 'var(--text-secondary)'
                    }
                },
                x: {
                    grid: { 
                        display: false 
                    },
                    title: {
                        display: true,
                        text: 'День недели',
                        color: 'var(--text-secondary)'
                    }
                }
            }
        }
    });
}

// Функция форматирования чисел
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(0) + 'K';
    }
    return num.toString();
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
            if (data.success && data.tracks && data.tracks.length > 0) {
                displayPopularTracks(data.tracks, filter);
            } else {
                displayDemoPopularTracks(filter);
            }
        } else {
            displayDemoPopularTracks(filter);
        }
    } catch (error) {
        console.error('Ошибка загрузки треков:', error);
        displayDemoPopularTracks(filter);
    }
}

// Отображение демо-популярных треков
function displayDemoPopularTracks(filter) {
    const container = document.getElementById('popularTracksContainer');
    
    if (filter === 'overall') {
        container.innerHTML = `
            <table class="users-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Название</th>
                        <th>Исполнитель</th>
                        <th>Жанр</th>
                        <th>В избранном</th>
                        <th>Прослушиваний</th>
                    </tr>
                </thead>
                <tbody>
                    ${DEMO_DATA.topTracks.map((track, index) => `
                        <tr>
                            <td>${index + 1}</td>
                            <td>${escapeHtml(track.title)}</td>
                            <td>${escapeHtml(track.artist)}</td>
                            <td>${escapeHtml(track.genre || '—')}</td>
                            <td>${track.favorites_count}</td>
                            <td>${track.listens_count}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    } else if (filter === 'by_age') {
        let html = '';
        for (const [ageGroup, genres] of Object.entries(DEMO_DATA.genreByAge)) {
            const sortedGenres = Object.entries(genres).sort((a, b) => b[1] - a[1]).slice(0, 5);
            html += `
                <div class="chart-container">
                    <div class="chart-title">Возрастная группа: ${ageGroup}</div>
                    <table class="users-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Жанр</th>
                                <th>Популярность</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${sortedGenres.map(([genre, count], index) => `
                                <tr>
                                    <td>${index + 1}</td>
                                    <td>${escapeHtml(genre)}</td>
                                    <td>
                                        <div style="display: flex; align-items: center; gap: 10px;">
                                            <div style="flex: 1; height: 8px; background: #e0e0e0; border-radius: 4px;">
                                                <div style="width: ${count}%; height: 100%; background: #667eea; border-radius: 4px;"></div>
                                            </div>
                                            <span>${count}</span>
                                        </div>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }
        container.innerHTML = html;
    } else if (filter === 'by_gender') {
        let html = '';
        for (const [gender, genres] of Object.entries(DEMO_DATA.genreByGender)) {
            const sortedGenres = Object.entries(genres).sort((a, b) => b[1] - a[1]);
            html += `
                <div class="chart-container">
                    <div class="chart-title">${gender}</div>
                    <table class="users-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Жанр</th>
                                <th>Популярность</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${sortedGenres.map(([genre, count], index) => `
                                <tr>
                                    <td>${index + 1}</td>
                                    <td>${escapeHtml(genre)}</td>
                                    <td>
                                        <div style="display: flex; align-items: center; gap: 10px;">
                                            <div style="flex: 1; height: 8px; background: #e0e0e0; border-radius: 4px;">
                                                <div style="width: ${count}%; height: 100%; background: ${gender === 'Мужчины' ? '#4A90E2' : '#E24A8D'}; border-radius: 4px;"></div>
                                            </div>
                                            <span>${count}</span>
                                        </div>
                                    </td>
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

// Отображение популярных треков (реальные данные)
function displayPopularTracks(tracks, filter) {
    const container = document.getElementById('popularTracksContainer');
    
    if (!tracks || tracks.length === 0) {
        displayDemoPopularTracks(filter);
        return;
    }
    
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
        container.innerHTML = html || '<div class="error-message">Нет данных для отображения</div>';
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
        container.innerHTML = html || '<div class="error-message">Нет данных для отображения</div>';
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
                // Проверяем наличие данных
                if (data.genre_by_age && data.genre_by_age.length > 0) {
                    const ageData = processGenreAgeData(data.genre_by_age);
                    createGenreAgeChart(ageData);
                } else {
                    createDemoGenreAgeChart();
                }
                
                if (data.genre_by_gender && data.genre_by_gender.length > 0) {
                    const genderData = processGenreGenderData(data.genre_by_gender);
                    createGenreGenderChart(genderData);
                } else {
                    createDemoGenreGenderChart();
                }
                
                if (data.overall_genre && data.overall_genre.length > 0) {
                    createOverallGenreChart(data.overall_genre);
                } else {
                    createDemoOverallGenreChart();
                }
            } else {
                createAllDemoCharts();
            }
        } else {
            createAllDemoCharts();
        }
    } catch (error) {
        console.error('Ошибка загрузки анализа жанров:', error);
        createAllDemoCharts();
    }
}

function createAllDemoCharts() {
    createDemoGenreAgeChart();
    createDemoGenreGenderChart();
    createDemoOverallGenreChart();
}

function createDemoGenreAgeChart() {
    const ageGroups = Object.keys(DEMO_DATA.genreByAge);
    const allGenres = new Set();
    ageGroups.forEach(age => {
        Object.keys(DEMO_DATA.genreByAge[age]).forEach(genre => allGenres.add(genre));
    });
    const genres = Array.from(allGenres).slice(0, 8);
    
    const datasets = ageGroups.map((ageGroup, index) => ({
        label: ageGroup,
        data: genres.map(genre => DEMO_DATA.genreByAge[ageGroup][genre] || 0),
        backgroundColor: `hsla(${index * 60}, 70%, 60%, 0.7)`,
    }));
    
    const ctx = document.getElementById('genreAgeChart').getContext('2d');
    if (charts.genreAge) charts.genreAge.destroy();
    
    charts.genreAge = new Chart(ctx, {
        type: 'bar',
        data: { labels: genres, datasets },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'top' }
            },
            scales: {
                y: { beginAtZero: true, title: { display: true, text: 'Популярность' } }
            }
        }
    });
}

function createDemoGenreGenderChart() {
    const genders = Object.keys(DEMO_DATA.genreByGender);
    const allGenres = new Set();
    genders.forEach(g => {
        Object.keys(DEMO_DATA.genreByGender[g]).forEach(genre => allGenres.add(genre));
    });
    const genres = Array.from(allGenres).slice(0, 8);
    
    const datasets = genders.map(gender => ({
        label: gender,
        data: genres.map(genre => DEMO_DATA.genreByGender[gender][genre] || 0),
        backgroundColor: gender === 'Мужчины' ? '#4A90E2' : '#E24A8D',
    }));
    
    const ctx = document.getElementById('genreGenderChart').getContext('2d');
    if (charts.genreGender) charts.genreGender.destroy();
    
    charts.genreGender = new Chart(ctx, {
        type: 'bar',
        data: { labels: genres, datasets },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'top' }
            },
            scales: {
                y: { beginAtZero: true, title: { display: true, text: 'Популярность' } }
            }
        }
    });
}

function createDemoOverallGenreChart() {
    const ctx = document.getElementById('genreChart').getContext('2d');
    if (charts.overallGenre) charts.overallGenre.destroy();
    
    const genres = Object.keys(DEMO_DATA.genreDistribution);
    const values = Object.values(DEMO_DATA.genreDistribution);
    
    charts.overallGenre = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: genres,
            datasets: [{
                data: values,
                backgroundColor: [
                    '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', 
                    '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F'
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'right' },
                tooltip: {
                    callbacks: {
                        label: (context) => `${context.label}: ${context.parsed}%`
                    }
                }
            }
        }
    });
}

function processGenreAgeData(data) {
    const ageGroups = [...new Set(data.map(d => d.age_group))];
    const genres = [...new Set(data.map(d => d.genre))].slice(0, 10);
    
    const datasets = ageGroups.map(ageGroup => ({
        label: ageGroup,
        data: genres.map(genre => {
            const item = data.find(d => d.genre === genre && d.age_group === ageGroup);
            return item ? item.favorites_count : 0;
        }),
        backgroundColor: getRandomColor(),
    }));
    
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
                legend: { position: 'top' }
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
                data: topGenres.map(g => g.total_favorites || g.count || 0),
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
                // Используем реальные или демо-данные
                const ageData = data.age_distribution?.length ? data.age_distribution : DEMO_DATA.ageDistribution;
                const genderData = data.gender_distribution?.length ? data.gender_distribution : DEMO_DATA.genderDistribution;
                const personalityData = data.personality_distribution?.length ? data.personality_distribution : DEMO_DATA.personalityDistribution;
                const genreData = data.personality_genres && Object.keys(data.personality_genres).length ? data.personality_genres : DEMO_DATA.personalityGenres;
                
                createAgeDistributionChart(ageData);
                createGenderDistributionChart(genderData);
                createPersonalityChart(personalityData);
                displayPersonalityGenres(genreData);
            } else {
                createDemoSegmentationCharts();
            }
        } else {
            createDemoSegmentationCharts();
        }
    } catch (error) {
        console.error('Ошибка загрузки сегментации:', error);
        createDemoSegmentationCharts();
    }
}

function createDemoSegmentationCharts() {
    createAgeDistributionChart(DEMO_DATA.ageDistribution);
    createGenderDistributionChart(DEMO_DATA.genderDistribution);
    createPersonalityChart(DEMO_DATA.personalityDistribution);
    displayPersonalityGenres(DEMO_DATA.personalityGenres);
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
                legend: { position: 'bottom' },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const total = data.reduce((sum, d) => sum + d.count, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return `${context.label}: ${context.parsed} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

function createGenderDistributionChart(data) {
    const ctx = document.getElementById('genderDistributionChart').getContext('2d');
    if (charts.genderDist) charts.genderDist.destroy();
    
    const labels = data.map(d => {
        if (d.gender === 'male') return 'Мужчины';
        if (d.gender === 'female') return 'Женщины';
        return d.gender;
    });
    
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
                legend: { position: 'bottom' },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const total = data.reduce((sum, d) => sum + d.count, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return `${context.label}: ${context.parsed} (${percentage}%)`;
                        }
                    }
                }
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
        const genreArray = Array.isArray(genres) ? genres : Object.entries(genres).map(([genre, count]) => ({ genre, count }));
        
        html += `
            <div style="margin-bottom: 20px;">
                <h4 style="color: var(--text-primary); margin-bottom: 10px;">${personality}</h4>
                <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                    ${genreArray.slice(0, 5).map(g => `
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
            if (data.success && data.users && data.users.length > 0) {
                displayUsers(data);
                currentUserPage = page;
            } else {
                displayDemoUsers();
            }
        } else {
            displayDemoUsers();
        }
    } catch (error) {
        console.error('Ошибка загрузки пользователей:', error);
        displayDemoUsers();
    }
}

function displayDemoUsers() {
    const container = document.getElementById('usersTableContainer');
    const demoUsers = [
        { id: 1, username: 'music_lover', email: 'music@example.com', age: 28, gender: 'male', extraversion: 4, openness: 4, favorites_count: 45, listens_count: 230, is_admin: true },
        { id: 2, username: 'rock_fan', email: 'rock@example.com', age: 35, gender: 'male', extraversion: 3, openness: 5, favorites_count: 67, listens_count: 450, is_admin: false },
        { id: 3, username: 'pop_girl', email: 'pop@example.com', age: 22, gender: 'female', extraversion: 5, openness: 3, favorites_count: 89, listens_count: 620, is_admin: false },
        { id: 4, username: 'jazz_cat', email: 'jazz@example.com', age: 42, gender: 'male', extraversion: 2, openness: 5, favorites_count: 34, listens_count: 180, is_admin: false },
        { id: 5, username: 'classical_mind', email: 'classic@example.com', age: 55, gender: 'female', extraversion: 2, openness: 4, favorites_count: 56, listens_count: 310, is_admin: false },
    ];
    
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
                ${demoUsers.map(user => `
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
        <div style="text-align: center; margin-top: 20px; color: var(--text-secondary);">
            <i>Демонстрационные данные. Для реальных данных подключите базу данных.</i>
        </div>
    `;
    
    container.innerHTML = html;
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
        } else {
            showMessage('Демо-режим: изменение статуса недоступно', 'error');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showMessage('Демо-режим: изменение статуса недоступно', 'error');
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
            if (tabId === 'tracks') {
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
        const preview = document.getElementById('topTracksPreview');
        preview.innerHTML = DEMO_DATA.topTracks.slice(0, 5).map((track, i) => `
            <div style="display: flex; align-items: center; padding: 10px; border-bottom: 1px solid var(--card-border);">
                <span style="width: 30px; color: var(--text-secondary);">${i + 1}.</span>
                <div style="width: 30px; height: 30px; background: linear-gradient(135deg, #667eea, #764ba2); border-radius: 5px; margin-right: 10px; display: flex; align-items: center; justify-content: center; color: white;">🎵</div>
                <div style="flex: 1;">
                    <div style="font-weight: 500;">${escapeHtml(track.title)}</div>
                    <div style="font-size: 12px; color: var(--text-secondary);">${escapeHtml(track.artist)}</div>
                </div>
                <span style="color: #667eea;">❤️ ${track.favorites_count}</span>
            </div>
        `).join('');
        
        // Создаем график жанров для превью
        createDemoOverallGenreChart();
    }
});