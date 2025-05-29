/**
 * JumpServer Theme Toggle
 * Handles switching between light and dark themes
 */

(function() {
    'use strict';

    // Theme configuration
    const THEMES = {
        LIGHT: 'light',
        DARK: 'dark'
    };

    const STORAGE_KEY = 'jumpserver-theme';
    const THEME_ATTRIBUTE = 'data-theme';

    /**
     * Theme Manager Class
     */
    class ThemeManager {
        constructor() {
            this.currentTheme = this.getStoredTheme() || this.getSystemTheme();
            this.init();
        }

        /**
         * Initialize theme manager
         */
        init() {
            // Try to load theme from backend first, fallback to stored/system theme
            this.loadThemeFromBackend();
            this.createToggleButton();
            this.bindEvents();
        }

        /**
         * Get theme from localStorage
         */
        getStoredTheme() {
            try {
                return localStorage.getItem(STORAGE_KEY);
            } catch (e) {
                console.warn('localStorage not available for theme storage');
                return null;
            }
        }

        /**
         * Store theme in localStorage
         */
        setStoredTheme(theme) {
            try {
                localStorage.setItem(STORAGE_KEY, theme);
            } catch (e) {
                console.warn('localStorage not available for theme storage');
            }
        }

        /**
         * Get system theme preference
         */
        getSystemTheme() {
            if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                return THEMES.DARK;
            }
            return THEMES.LIGHT;
        }

        /**
         * Apply theme to document
         */
        applyTheme(theme) {
            const root = document.documentElement;

            // Remove existing theme attributes
            root.removeAttribute(THEME_ATTRIBUTE);

            // Apply new theme
            if (theme === THEMES.DARK) {
                root.setAttribute(THEME_ATTRIBUTE, THEMES.DARK);
            }

            this.currentTheme = theme;
            this.setStoredTheme(theme);
            this.updateToggleButton();

            // Save to backend if user is authenticated
            this.saveThemeToBackend(theme);
        }

        /**
         * Save theme preference to backend
         */
        saveThemeToBackend(theme) {
            // Check if user is authenticated (look for CSRF token or user info)
            const csrfToken = this.getCSRFToken();
            if (!csrfToken) {
                return; // Not authenticated or CSRF token not available
            }

            fetch('/api/theme/toggle/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify({ theme: theme }),
                credentials: 'same-origin'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    console.log('Theme preference saved to backend:', theme);
                } else {
                    console.warn('Failed to save theme preference:', data.error);
                }
            })
            .catch(error => {
                console.warn('Error saving theme preference:', error);
            });
        }

        /**
         * Get CSRF token from page
         */
        getCSRFToken() {
            // Try to get CSRF token from various sources
            const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
            if (csrfInput) {
                return csrfInput.value;
            }

            const csrfMeta = document.querySelector('meta[name="csrf-token"]');
            if (csrfMeta) {
                return csrfMeta.getAttribute('content');
            }

            // Try to get from cookie
            const cookies = document.cookie.split(';');
            for (let cookie of cookies) {
                const [name, value] = cookie.trim().split('=');
                if (name === 'csrftoken') {
                    return value;
                }
            }

            return null;
        }

        /**
         * Load theme preference from backend
         */
        loadThemeFromBackend() {
            fetch('/api/theme/toggle/', {
                method: 'GET',
                credentials: 'same-origin'
            })
            .then(response => response.json())
            .then(data => {
                if (data.theme && data.theme !== 'auto') {
                    this.applyTheme(data.theme);
                }
            })
            .catch(error => {
                console.warn('Could not load theme from backend:', error);
                // Fallback to stored theme or system preference
                const fallbackTheme = this.getStoredTheme() || this.getSystemTheme();
                this.applyTheme(fallbackTheme);
            });
        }

        /**
         * Toggle between themes
         */
        toggleTheme() {
            const newTheme = this.currentTheme === THEMES.DARK ? THEMES.LIGHT : THEMES.DARK;
            this.applyTheme(newTheme);

            // Trigger custom event for other components
            window.dispatchEvent(new CustomEvent('themeChanged', {
                detail: { theme: newTheme }
            }));
        }

        /**
         * Create theme toggle button
         */
        createToggleButton() {
            // Check if button already exists
            if (document.getElementById('theme-toggle')) {
                return;
            }

            // Create toggle button
            const toggleButton = document.createElement('button');
            toggleButton.id = 'theme-toggle';
            toggleButton.className = 'btn btn-sm theme-toggle-btn';
            toggleButton.setAttribute('title', 'Toggle Dark/Light Theme');
            toggleButton.innerHTML = this.getToggleIcon();

            // Add styles
            const style = document.createElement('style');
            style.textContent = `
                .theme-toggle-btn {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    z-index: 1050;
                    background: var(--bg-secondary, #f8f9fa);
                    border: 1px solid var(--border-primary, #dee2e6);
                    border-radius: 50%;
                    width: 40px;
                    height: 40px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }

                .theme-toggle-btn:hover {
                    background: var(--bg-hover, #e9ecef);
                    transform: scale(1.05);
                }

                .theme-toggle-btn i {
                    font-size: 16px;
                    color: var(--text-primary, #333);
                }

                /* Responsive positioning */
                @media (max-width: 768px) {
                    .theme-toggle-btn {
                        top: 10px;
                        right: 10px;
                        width: 35px;
                        height: 35px;
                    }

                    .theme-toggle-btn i {
                        font-size: 14px;
                    }
                }

                /* Integration with navbar */
                .navbar-right .theme-toggle-navbar {
                    position: relative;
                    top: auto;
                    right: auto;
                    margin: 8px 10px;
                }
            `;
            document.head.appendChild(style);

            // Try to add to navbar first, fallback to fixed position
            const navbar = document.querySelector('.navbar-right');
            if (navbar) {
                toggleButton.className = 'btn btn-sm theme-toggle-btn theme-toggle-navbar';
                navbar.appendChild(toggleButton);
            } else {
                document.body.appendChild(toggleButton);
            }

            this.toggleButton = toggleButton;
        }

        /**
         * Get appropriate icon for current theme
         */
        getToggleIcon() {
            if (this.currentTheme === THEMES.DARK) {
                return '<i class="fa fa-sun-o" aria-hidden="true"></i>';
            } else {
                return '<i class="fa fa-moon-o" aria-hidden="true"></i>';
            }
        }

        /**
         * Update toggle button icon
         */
        updateToggleButton() {
            if (this.toggleButton) {
                this.toggleButton.innerHTML = this.getToggleIcon();
                this.toggleButton.setAttribute('title',
                    this.currentTheme === THEMES.DARK ?
                    'Switch to Light Theme' :
                    'Switch to Dark Theme'
                );
            }
        }

        /**
         * Bind event listeners
         */
        bindEvents() {
            // Toggle button click
            document.addEventListener('click', (e) => {
                if (e.target.closest('#theme-toggle')) {
                    e.preventDefault();
                    this.toggleTheme();
                }
            });

            // Listen for system theme changes
            if (window.matchMedia) {
                const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
                mediaQuery.addEventListener('change', (e) => {
                    // Only auto-switch if user hasn't manually set a preference
                    if (!this.getStoredTheme()) {
                        this.applyTheme(e.matches ? THEMES.DARK : THEMES.LIGHT);
                    }
                });
            }

            // Keyboard shortcut (Ctrl/Cmd + Shift + T)
            document.addEventListener('keydown', (e) => {
                if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'T') {
                    e.preventDefault();
                    this.toggleTheme();
                }
            });
        }

        /**
         * Get current theme
         */
        getCurrentTheme() {
            return this.currentTheme;
        }

        /**
         * Set theme programmatically
         */
        setTheme(theme) {
            if (Object.values(THEMES).includes(theme)) {
                this.applyTheme(theme);
            }
        }
    }

    /**
     * Initialize theme manager when DOM is ready
     */
    function initThemeManager() {
        // Create global theme manager instance
        window.jumpserverTheme = new ThemeManager();

        // Add to jumpserver namespace if it exists
        if (window.jumpserver) {
            window.jumpserver.theme = window.jumpserverTheme;
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initThemeManager);
    } else {
        initThemeManager();
    }

    // Export for module systems
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = { ThemeManager, THEMES };
    }

})();
