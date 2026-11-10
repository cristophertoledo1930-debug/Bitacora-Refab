document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('form[data-submit-state]');
  if (!form) return;
  const originalText = form.querySelector('.button-text').textContent;
  form.addEventListener('submit', (event) => {
    if (form.dataset.sending === 'true') { event.preventDefault(); return; }
    if (!form.checkValidity()) return;
    form.dataset.sending = 'true';
    form.setAttribute('aria-busy', 'true');
    const button = form.querySelector('button[type=submit]');
    button.disabled = true;
    button.querySelector('.button-text').textContent = 'Guardando…';
  });
  // Browser history may restore a disabled submit button from the page cache.
  window.addEventListener('pageshow', () => {
    form.dataset.sending = 'false'; form.removeAttribute('aria-busy');
    const button = form.querySelector('button[type=submit]');
    button.disabled = false; button.querySelector('.button-text').textContent = originalText;
  });
});
