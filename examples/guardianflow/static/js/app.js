(() => {
  const toast = (message) => { let node = document.querySelector('.toast'); if (!node) { node = document.createElement('div'); node.className = 'toast'; document.body.append(node); } node.textContent = message; setTimeout(() => node.remove(), 2600); };
  document.querySelectorAll('[data-demo]').forEach((button) => button.addEventListener('click', async () => {
    button.disabled = true; button.textContent = 'Running...';
    try { const response = await fetch(`/api/demo/${button.dataset.demo}`, {method:'POST'}); if (!response.ok) throw new Error('Demo failed'); await response.json(); location.reload(); }
    catch (error) { toast(error.message); button.disabled = false; }
  }));
  document.querySelectorAll('[data-alert]').forEach((button) => button.addEventListener('click', async () => {
    const response = await fetch(`/api/alerts/${button.dataset.alert}/${button.dataset.action}`, {method:'POST'});
    if (response.ok) location.reload();
  }));
  if (location.pathname === '/' || location.pathname === '/dashboard') {
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    try { const socket = new WebSocket(`${protocol}://${location.host}/ws/live`); socket.onmessage = () => { if (!document.hidden) location.reload(); }; }
    catch (_) { /* The dashboard remains usable without a live socket. */ }
  }
})();
