/* Keyboard navigation for individual status pages */
(function () {
  'use strict';
  var prev = document.getElementById('status-prev');
  var next = document.getElementById('status-next');
  var touchStartX = 0;
  var touchStartY = 0;
  document.addEventListener('touchstart', function (e) {
    touchStartX = e.changedTouches[0].clientX;
    touchStartY = e.changedTouches[0].clientY;
  }, { passive: true });
  document.addEventListener('touchend', function (e) {
    var dx = e.changedTouches[0].clientX - touchStartX;
    var dy = e.changedTouches[0].clientY - touchStartY;
    if (Math.abs(dx) < 40 || Math.abs(dx) < Math.abs(dy)) return;
    if (dx > 0) {
      if (prev) window.location = prev.href;
    } else {
      if (next) window.location = next.href;
    }
  }, { passive: true });
  document.addEventListener('keydown', function (e) {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.key === 'ArrowLeft' || e.key === 'ArrowUp' || e.key === 'h' || e.key === 'k' || e.key === 'a' || e.key === 'w' || e.key === 'p') {
      if (prev) window.location = prev.href;
    } else if (e.key === 'ArrowRight' || e.key === 'ArrowDown' || e.key === 'j' || e.key === 'l' || e.key === 's' || e.key === 'd' || e.key === 'n') {
      if (next) window.location = next.href;
    }
  });
}());
