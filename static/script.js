document.addEventListener('DOMContentLoaded', () => {
    // ---- Loader ----
    const loader = document.getElementById('loader-wrapper');
    if (loader) {
        setTimeout(() => {
            loader.classList.add('hidden');
        }, 500); // Fades out loader
    }

    // ---- Mobile Nav Toggle ----
    const navToggle = document.getElementById('navToggle');
    const navMenu = document.getElementById('navMenu');
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', () => {
            navMenu.classList.toggle('active');
        });
    }

    // ---- Dark/Light Mode Toggle ----
    const themeToggle = document.getElementById('themeToggle');
    const body = document.body;
    
    // Check local storage for preference
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        body.className = savedTheme;
        updateThemeIcon(savedTheme);
    } else {
        // Check system preference
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            body.className = 'dark-mode';
            updateThemeIcon('dark-mode');
        }
    }

    if(themeToggle) {
        themeToggle.addEventListener('click', () => {
            if (body.classList.contains('light-mode')) {
                body.className = 'dark-mode';
                localStorage.setItem('theme', 'dark-mode');
                updateThemeIcon('dark-mode');
            } else {
                body.className = 'light-mode';
                localStorage.setItem('theme', 'light-mode');
                updateThemeIcon('light-mode');
            }
        });
    }

    function updateThemeIcon(theme) {
        if (!themeToggle) return;
        if (theme === 'dark-mode') {
            themeToggle.innerHTML = '<i class="fa-solid fa-sun"></i>';
        } else {
            themeToggle.innerHTML = '<i class="fa-solid fa-moon"></i>';
        }
    }

    // ---- Scroll Animations (Intersection Observer) ----
    const observerOptions = {
        threshold: 0.1,
        rootMargin: "0px 0px -50px 0px"
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target); 
            }
        });
    }, observerOptions);

    const fadeSections = document.querySelectorAll('.fade-section');
    fadeSections.forEach(section => {
        observer.observe(section);
    });

    // Auto-hide flash messages after 5 seconds
    const flashes = document.querySelectorAll('.alert');
    if (flashes.length > 0) {
        setTimeout(() => {
            flashes.forEach(flash => {
                flash.style.opacity = '0';
                setTimeout(() => flash.remove(), 500); // wait for fade out
            });
        }, 5000);
    }
});
