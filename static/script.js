document.addEventListener('DOMContentLoaded', () => {
    const currentPath = window.location.pathname;

    document.querySelectorAll('.nav-link').forEach(link => {
        const linkPath = new URL(link.href).pathname;

        if (linkPath === currentPath) {
            link.classList.add('active');
        }
    });
});


const style = document.createElement('style');
style.textContent = `
    .nav-link.active {
        background: #f0f0ff;
        color: #667eea;
        font-weight: 600;
    }
`;
document.head.appendChild(style);