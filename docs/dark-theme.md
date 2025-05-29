# JumpServer Dark Theme

This document describes the dark theme implementation for JumpServer's web interface.

## Overview

The dark theme provides a modern, eye-friendly interface that reduces eye strain during extended use, especially in low-light environments. The implementation includes:

- **Comprehensive CSS coverage** for all UI components
- **Automatic theme detection** based on system preferences
- **User preference persistence** in the database
- **Smooth transitions** between themes
- **API endpoints** for theme management

## Features

### 🌙 **Theme Options**

- **Auto (System)**: Follows system dark/light mode preference
- **Light Theme**: Traditional light interface (default)
- **Dark Theme**: Modern dark interface with high contrast
- **Classic Green**: Original JumpServer theme with green accents

### 🎨 **Design Principles**

- **High Contrast**: Ensures readability with proper color contrast ratios
- **Consistent Colors**: Uses CSS variables for maintainable color schemes
- **Smooth Transitions**: 0.3s ease transitions for theme switching
- **Accessibility**: Maintains WCAG compliance for color contrast

### 🔧 **Technical Implementation**

- **CSS Variables**: Modern approach using CSS custom properties
- **Data Attributes**: Theme switching via `data-theme="dark"` attribute
- **Local Storage**: Client-side theme preference caching
- **Database Persistence**: Server-side user preference storage

## Usage

### For End Users

#### **Theme Toggle Button**

A floating theme toggle button appears in the top-right corner:
- **Moon icon** (🌙): Click to switch to dark theme
- **Sun icon** (☀️): Click to switch to light theme
- **Keyboard shortcut**: `Ctrl/Cmd + Shift + T`

#### **Automatic Detection**

The theme automatically detects your system preference:
- If your OS is set to dark mode, JumpServer will start in dark theme
- If your OS is set to light mode, JumpServer will start in light theme
- Your manual selection overrides automatic detection

### For Administrators

#### **Enable Dark Theme for All Users**

```bash
# Enable dark theme for all existing users
python manage.py enable_dark_theme --all-users

# Enable dark theme for specific user
python manage.py enable_dark_theme --username admin

# Set different theme
python manage.py enable_dark_theme --all-users --theme classic_green
```

#### **API Endpoints**

**Get User Theme Preference:**
```bash
GET /api/v1/users/theme/
Authorization: Bearer <token>
```

**Update User Theme Preference:**
```bash
POST /api/v1/users/theme/
Content-Type: application/json
Authorization: Bearer <token>

{
    "theme": "dark"
}
```

**Simple Theme Toggle:**
```bash
POST /api/theme/toggle/
Content-Type: application/json
X-CSRFToken: <csrf_token>

{
    "theme": "dark"
}
```

## Installation

### 1. **Database Migration**

Add theme preference field to user model:

```bash
python manage.py makemigrations users
python manage.py migrate
```

### 2. **URL Configuration**

Add theme API endpoints to your `urls.py`:

```python
from apps.users.api.theme import theme_urlpatterns

urlpatterns = [
    # ... existing patterns
] + theme_urlpatterns
```

### 3. **Template Integration**

The dark theme is automatically included in `_head_css_js.html`:

```html
<!-- Dark theme CSS -->
<link href="{% static 'css/themes/dark.css' %}" rel="stylesheet">

<!-- Theme toggle functionality -->
<script src="{% static 'js/theme-toggle.js' %}"></script>
```

## Customization

### **CSS Variables**

Customize dark theme colors by modifying CSS variables:

```css
:root[data-theme="dark"] {
    /* Primary Colors */
    --primary-color: #1ab394;
    --primary-color-dark: #158f7a;
    
    /* Background Colors */
    --bg-primary: #1a1a1a;
    --bg-secondary: #2d2d2d;
    --bg-tertiary: #3a3a3a;
    
    /* Text Colors */
    --text-primary: #ffffff;
    --text-secondary: #e0e0e0;
    --text-muted: #b0b0b0;
}
```

### **Adding New Components**

To add dark theme support for new components:

```css
[data-theme="dark"] .your-component {
    background-color: var(--bg-secondary);
    color: var(--text-primary);
    border: 1px solid var(--border-primary);
}

[data-theme="dark"] .your-component:hover {
    background-color: var(--bg-hover);
}
```

### **JavaScript Integration**

Access theme manager in your JavaScript:

```javascript
// Get current theme
const currentTheme = window.jumpserverTheme.getCurrentTheme();

// Set theme programmatically
window.jumpserverTheme.setTheme('dark');

// Listen for theme changes
window.addEventListener('themeChanged', (event) => {
    console.log('Theme changed to:', event.detail.theme);
});
```

## Browser Support

- **Modern Browsers**: Full support with CSS variables
- **IE 11**: Graceful degradation (no dark theme)
- **Mobile Browsers**: Full responsive support

## Performance

- **CSS Size**: ~15KB additional CSS for dark theme
- **JavaScript**: ~8KB for theme management
- **Runtime Impact**: Minimal - uses CSS variables for instant switching

## Troubleshooting

### **Theme Not Persisting**

1. Check database migration: `python manage.py showmigrations users`
2. Verify API endpoints are accessible
3. Check browser console for JavaScript errors

### **Incomplete Dark Theme**

1. Clear browser cache and reload
2. Check if custom CSS overrides dark theme variables
3. Verify all CSS files are loading correctly

### **Toggle Button Not Appearing**

1. Check if JavaScript is enabled
2. Verify `theme-toggle.js` is loading
3. Check for JavaScript console errors

## Contributing

To contribute to the dark theme:

1. **Test thoroughly** across different browsers
2. **Maintain contrast ratios** for accessibility
3. **Use CSS variables** for consistency
4. **Add transitions** for smooth user experience

### **Testing Checklist**

- [ ] All form elements are properly styled
- [ ] Tables and data grids are readable
- [ ] Modals and dropdowns work correctly
- [ ] Navigation elements are accessible
- [ ] Print styles maintain readability
- [ ] Mobile responsive design works

## Future Enhancements

- **Additional Themes**: Blue, purple, high-contrast themes
- **Theme Scheduling**: Automatic switching based on time of day
- **Component Themes**: Per-component theme customization
- **Theme Import/Export**: Share custom themes between instances
