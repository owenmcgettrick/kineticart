document.addEventListener('DOMContentLoaded', () => {
    const carousels = document.querySelectorAll('.carousel-wrapper');
    
    carousels.forEach(wrapper => {
        const items = wrapper.querySelectorAll('.carousel-item');
        const nextBtn = wrapper.querySelector('.next-btn');
        const prevBtn = wrapper.querySelector('.prev-btn');
        let currentIndex = 0;
        
        // Find if there is any active item (in case of initial load)
        items.forEach((item, index) => {
            if (item.classList.contains('active')) {
                currentIndex = index;
                // auto-play initial video if exists
                const video = item.querySelector('video');
                if (video) {
                    video.play().catch(e => console.log('Autoplay blocked or issue:', e));
                }
            }
        });

        // If there's only 1 image or 0 images/videos, hide controls
        if (items.length <= 1) {
            const controls = wrapper.querySelector('.carousel-controls');
            if (controls) controls.style.display = 'none';
        }

        const showItem = (index) => {
            items.forEach((item, i) => {
                const video = item.querySelector('video');
                
                if (i === index) {
                    item.classList.add('active');
                    if (video) {
                        video.currentTime = 0; // Restart video
                        video.play().catch(e => console.log('Playback issue:', e));
                    }
                } else {
                    item.classList.remove('active');
                    if (video) {
                        video.pause();
                    }
                }
            });
        };

        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                currentIndex = (currentIndex + 1) % items.length;
                showItem(currentIndex);
            });
        }

        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                currentIndex = (currentIndex - 1 + items.length) % items.length;
                showItem(currentIndex);
            });
        }
    });
});
