document.addEventListener('DOMContentLoaded', () => {
    // Navbar Scroll Effect
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.add('scrolled'); // keep blur
                if(window.scrollY < 10) navbar.classList.remove('scrolled');
            }
        });
    }

    // Smooth Scroll
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const href = this.getAttribute('href');
            if (href && href !== '#') {
                const target = document.querySelector(href);
                if(target) target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });

    // Horizontal Scrolling
    const horizontalScrolls = document.querySelectorAll('.horizontal-scroll');
    horizontalScrolls.forEach(row => {
        const id = row.getAttribute('id');
        const prevBtn = document.querySelector(`[data-target="${id}"].prev-btn`);
        const nextBtn = document.querySelector(`[data-target="${id}"].next-btn`);

        if (prevBtn && nextBtn) {
            prevBtn.addEventListener('click', () => {
                row.scrollBy({ left: -350, behavior: 'smooth' });
            });

            nextBtn.addEventListener('click', () => {
                row.scrollBy({ left: 350, behavior: 'smooth' });
            });
        }
    });

    // Hamburger Menu Toggle
    const hamburger = document.getElementById('hamburger');
    const navLinks = document.getElementById('nav-links');
    if (hamburger && navLinks) {
        hamburger.addEventListener('click', () => {
            hamburger.classList.toggle('active');
            navLinks.classList.toggle('active');
        });
    }

    // Auto-hide flash messages
    const flashes = document.querySelectorAll('.flash');
    if (flashes.length > 0) {
        setTimeout(() => {
            flashes.forEach(f => {
                f.style.opacity = '0';
                setTimeout(() => f.remove(), 500);
            });
        }, 3000);
    }
});
