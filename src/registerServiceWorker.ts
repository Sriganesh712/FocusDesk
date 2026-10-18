export function registerServiceWorker(): void {
  if ('serviceWorker' in navigator && (import.meta.env.PROD || !import.meta.env.DEV)) {
    window.addEventListener('load', () => {
      navigator.serviceWorker
        .register('/sw.js')
        .then((reg) => {
          console.log('[FocusDesk] Service Worker registered:', reg.scope);
        })
        .catch((err) => {
          console.warn('[FocusDesk] Service Worker registration failed:', err);
        });
    });
  }
}
