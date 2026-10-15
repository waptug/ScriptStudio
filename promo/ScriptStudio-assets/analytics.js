'use strict';
(() => {
  const measurementId = window.SCRIPTSTUDIO_ANALYTICS?.measurementId || '';
  // No property is guessed and no Google script or request is made before setup.
  if (!/^G-[A-Z0-9]+$/.test(measurementId)) return;
  const debug = new URLSearchParams(location.search).get('ss_debug') === '1';
  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };
  window.gtag('js', new Date());
  const settings = { allow_google_signals: false, allow_ad_personalization_signals: false };
  if (debug) settings.debug_mode = true;
  window.gtag('config', measurementId, settings);
  const tag = document.createElement('script');
  tag.async = true;
  tag.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(measurementId);
  document.head.appendChild(tag);
  function track(name, values) {
    const params = { ...values, page_name: 'scriptstudio_promo', transport_type: 'beacon' };
    if (debug) params.debug_mode = true;
    window.gtag('event', name, params);
  }
  document.addEventListener('click', event => {
    const link = event.target.closest?.('a');
    if (!link) return;
    if (link.matches('.social-actions a')) {
      const method = link.matches('.facebook') ? 'facebook' : link.matches('.x-share') ? 'x' : 'linkedin';
      track('share_open', { method, content_type: 'promo_page', item_id: 'scriptstudio' });
      return;
    }
    const destination = new URL(link.href);
    const locationName = link.closest('header') ? 'header' : link.closest('.hero') ? 'hero' : link.closest('#start') ? 'closing_cta' : link.closest('.network') ? 'promo_card' : 'footer';
    if (destination.hostname === 'github.com' && destination.pathname === '/waptug/ScriptStudio') {
      track('github_click', { link_url: destination.origin + destination.pathname, placement: locationName });
    } else if (link.matches('.network-card')) {
      track('promo_site_click', { destination: destination.hostname === 'protube.geekstreaming.com' ? 'protube' : 'geekstreaming', link_url: destination.origin + destination.pathname });
    }
  });
  document.addEventListener('scriptstudio:link-copied', () => track('share_copy', { method: 'copy_link', content_type: 'promo_page', item_id: 'scriptstudio' }));
})();
