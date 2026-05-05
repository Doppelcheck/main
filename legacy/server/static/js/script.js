function openAdminModal() {
    const adminModal = document.getElementById('admin-modal');
    adminModal.style.display = 'block';
}

function closeAdminModal() {
    const adminModal = document.getElementById('admin-modal');
    adminModal.style.display = 'none';
}

function main() {
    document.addEventListener('DOMContentLoaded', function() {
        const video = document.getElementById('user-video');
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    video.play();
                } else {
                    video.pause();
                }
            });
        });

        observer.observe(video);
    });

    document.addEventListener('DOMContentLoaded', function() {
        const video = document.getElementById('installation-video');
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    video.play();
                } else {
                    video.pause();
                }
            });
        });

        observer.observe(video);
    });

    document.addEventListener('DOMContentLoaded', function() {
        const adminLink = document.querySelector('a[href="#admin"]');
        const adminModal = document.getElementById('admin-modal');
        const togglePassword = document.querySelector('.toggle-password');
        const passwordInput = document.getElementById('password');
    
        // Open modal when clicking ADMIN link
        adminLink.addEventListener('click', function(e) {
            e.preventDefault();
            openAdminModal();
        });
    
        // Close modal when clicking outside the form container
        adminModal.addEventListener('click', function(e) {
            if (e.target === adminModal) {
                closeAdminModal();
            }
        });
    
        // Toggle password visibility
        togglePassword.addEventListener('click', function() {
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);
        });
    
        // Handle form submission
        document.querySelector('.admin-form').addEventListener('submit', function(e) {
            e.preventDefault();
            // Add your authentication logic here
            console.log('Login attempted');
        });
    });
    
    
}

main();