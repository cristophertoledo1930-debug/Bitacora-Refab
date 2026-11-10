(() => {
  const media = window.matchMedia('(max-width: 767px)');
  const apply = () => { const panel = document.getElementById('navigation-panel'); if (panel) panel.open = !media.matches; };
  const observer = new MutationObserver(() => {
    if (document.getElementById('navigation-panel')) { apply(); observer.disconnect(); }
  });
  observer.observe(document.documentElement, {childList:true, subtree:true});
  media.addEventListener('change', apply);
})();
