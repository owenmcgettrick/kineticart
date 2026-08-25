document.addEventListener('DOMContentLoaded', () => {
  const artistStatement = document.querySelector('#about');
  const openArtistStatement = () => {
    if (artistStatement) artistStatement.open = true;
  };

  document.querySelectorAll('a[href="#about"]').forEach((link) => {
    link.addEventListener('click', openArtistStatement);
  });

  window.addEventListener('hashchange', () => {
    if (window.location.hash === '#about') openArtistStatement();
  });

  if (window.location.hash === '#about') openArtistStatement();

  const carousels = document.querySelectorAll('.carousel');

  const setSlide = (carousel, requestedIndex) => {
    const slides = [...carousel.querySelectorAll('.carousel-item')];
    if (!slides.length) return;

    const index = (requestedIndex + slides.length) % slides.length;
    carousel.dataset.index = String(index);

    slides.forEach((slide, slideIndex) => {
      const isActive = slideIndex === index;
      slide.classList.toggle('active', isActive);
      slide.setAttribute('aria-hidden', String(!isActive));
      const video = slide.querySelector('video');
      if (!video) return;
      if (isActive && carousel.dataset.visible === 'true') {
        video.currentTime = 0;
        video.play().catch(() => {});
      } else {
        video.pause();
      }
    });

    const count = carousel.querySelector('.carousel-count');
    if (count) count.textContent = `${index + 1} / ${slides.length}`;
  };

  carousels.forEach((carousel) => {
    carousel.dataset.index = '0';
    carousel.dataset.visible = 'false';

    carousel.querySelector('.previous')?.addEventListener('click', () => {
      setSlide(carousel, Number(carousel.dataset.index) - 1);
    });
    carousel.querySelector('.next')?.addEventListener('click', () => {
      setSlide(carousel, Number(carousel.dataset.index) + 1);
    });
    carousel.addEventListener('keydown', (event) => {
      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
      event.preventDefault();
      const direction = event.key === 'ArrowRight' ? 1 : -1;
      setSlide(carousel, Number(carousel.dataset.index) + direction);
    });
  });

  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        const carousel = entry.target;
        carousel.dataset.visible = String(entry.isIntersecting);
        setSlide(carousel, Number(carousel.dataset.index));
      });
    }, { threshold: 0.45 });
    carousels.forEach((carousel) => observer.observe(carousel));
  }

  const artworkSelect = document.querySelector('#contact-artwork');
  const message = document.querySelector('.contact-form textarea');
  document.querySelectorAll('[data-inquire-title]').forEach((button) => {
    button.addEventListener('click', () => {
      if (artworkSelect) artworkSelect.value = button.dataset.inquireTitle;
      window.setTimeout(() => message?.focus(), 350);
    });
  });

  const form = document.querySelector('.contact-form');
  form?.addEventListener('submit', (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;

    const data = new FormData(form);
    const recipient = form.dataset.contactEmail;
    const artwork = data.get('artwork');
    const subject = artwork === 'General inquiry' ? 'Kinetic Creations website inquiry' : `Inquiry about ${artwork}`;
    const body = [
      `Name: ${data.get('name')}`,
      `Email: ${data.get('email')}`,
      `Artwork: ${artwork}`,
      '',
      data.get('message'),
    ].join('\n');

    const status = form.querySelector('.form-status');
    if (status) status.textContent = 'Opening your email application…';
    window.location.href = `mailto:${recipient}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  });

  const year = document.querySelector('#current-year');
  if (year) year.textContent = String(new Date().getFullYear());
});
