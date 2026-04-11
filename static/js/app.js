// ===== SIDEBAR =====
function toggleSidebar() {
  const sb = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  if (!sb) return;
  const open = sb.classList.toggle('open');
  overlay.classList.toggle('open', open);
  document.body.style.overflow = open ? 'hidden' : '';
}

// Close sidebar on ESC
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    const sb = document.getElementById('sidebar');
    if (sb && sb.classList.contains('open')) toggleSidebar();
  }
});

// ===== MODAL =====
function openModal(content) {
  document.getElementById('modal-content').innerHTML = content;
  document.getElementById('modal-overlay').classList.add('active');
  document.getElementById('modal-box').classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('active');
  document.getElementById('modal-box').classList.remove('active');
  document.body.style.overflow = '';
}

// ===== FLASH AUTO HIDE =====
setTimeout(() => {
  document.querySelectorAll('.flash').forEach(el => {
    el.style.opacity = '0';
    el.style.transition = 'opacity 0.5s';
    setTimeout(() => el.remove(), 500);
  });
}, 3000);

// ===== ACTIVE TOUCH FEEDBACK =====
document.addEventListener('touchstart', () => {}, { passive: true });
