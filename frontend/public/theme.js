// Apply the saved theme before styles or React load, avoiding a theme flash.
(() => {
  let theme = 'dark';
  try {
    if (localStorage.getItem('scriptstudio-theme') === 'light') theme = 'light';
  } catch { /* Storage may be unavailable; keep the default theme. */ }
  document.documentElement.dataset.theme = theme;
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'light' ? '#f4f6f3' : '#101419');
})();
