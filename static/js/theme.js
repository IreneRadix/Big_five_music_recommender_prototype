(function() {
    const THEME_KEY = 'music_app_theme';
    
    function getSavedTheme() {
        return localStorage.getItem(THEME_KEY) || 'light';
    }
    
    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem(THEME_KEY, theme);
        updateThemeIcon(theme);
    }
    
    function updateThemeIcon(theme) {
        const toggleBtn = document.querySelector('.theme-toggle');
        if (toggleBtn) {
            toggleBtn.innerHTML = theme === 'dark' ? '☀️' : '🌙';
            toggleBtn.title = theme === 'dark' ? 'Светлая тема' : 'Тёмная тема';
        }
    }
    
    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        applyTheme(newTheme);
    }
    
    function createThemeToggle() {
        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'theme-toggle';
        toggleBtn.onclick = toggleTheme;
        
        const userInfo = document.querySelector('.user-info');
        if (userInfo) {
            userInfo.insertBefore(toggleBtn, userInfo.firstChild);
        } else {
            
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
    
    function initTheme() {
        const savedTheme = getSavedTheme();
        applyTheme(savedTheme);
        createThemeToggle();
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTheme);
    } else {
        initTheme();
    }
    
    window.toggleTheme = toggleTheme;
})();