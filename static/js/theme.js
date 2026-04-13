// theme.js - Управление темами
(function() {
    const THEME_KEY = 'music_app_theme';
    
    // Получение сохранённой темы
    function getSavedTheme() {
        return localStorage.getItem(THEME_KEY) || 'light';
    }
    
    // Применение темы
    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem(THEME_KEY, theme);
        updateThemeIcon(theme);
    }
    
    // Обновление иконки кнопки
    function updateThemeIcon(theme) {
        const toggleBtn = document.querySelector('.theme-toggle');
        if (toggleBtn) {
            toggleBtn.innerHTML = theme === 'dark' ? '☀️' : '🌙';
            toggleBtn.title = theme === 'dark' ? 'Светлая тема' : 'Тёмная тема';
        }
    }
    
    // Переключение темы
    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        applyTheme(newTheme);
    }
    
    // Создание кнопки переключения темы
    function createThemeToggle() {
        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'theme-toggle';
        toggleBtn.onclick = toggleTheme;
        
        // Находим место для вставки кнопки
        const userInfo = document.querySelector('.user-info');
        if (userInfo) {
            userInfo.insertBefore(toggleBtn, userInfo.firstChild);
        } else {
            // Если нет user-info, добавляем в header
            const header = document.querySelector('.header');
            if (header) {
                const navLinks = header.querySelector('.nav-links');
                if (navLinks) {
                    navLinks.appendChild(toggleBtn);
                } else {
                    header.appendChild(toggleBtn);
                }
            }
        }
        
        updateThemeIcon(getSavedTheme());
    }
    
    // Инициализация темы при загрузке
    function initTheme() {
        const savedTheme = getSavedTheme();
        applyTheme(savedTheme);
        createThemeToggle();
    }
    
    // Запускаем при загрузке DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTheme);
    } else {
        initTheme();
    }
    
    // Экспортируем функцию для внешнего использования
    window.toggleTheme = toggleTheme;
})();