// ─────────────────────────────────────────
// THEME TOGGLE
// ─────────────────────────────────────────

function toggleTheme() {
    var current = document.documentElement.getAttribute('data-theme');
    var next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    var btn = document.getElementById('theme-toggle');
    if (btn) btn.textContent = next === 'dark' ? '☀️' : '🌙';
}

// apply saved theme immediately before page renders
(function () {
    var saved = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', saved);
    document.addEventListener('DOMContentLoaded', function () {
        var btn = document.getElementById('theme-toggle');
        if (btn) btn.textContent = saved === 'dark' ? '☀️' : '🌙';
    });
})();

// ─────────────────────────────────────────
// ACTIVE NAV LINK
// ─────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function () {
    var currentPath = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(function (link) {
        try {
            var linkPath = new URL(link.href).pathname;
            if (linkPath === currentPath) {
                link.classList.add('active');
            }
        } catch (e) {}
    });
});