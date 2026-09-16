/* static/admin/js/admin.js */

(function() {
    'use strict';

    // ============================================================
    // TOAST NOTIFICATIONS
    // ============================================================
    function showToast(message, type) {
        const toast = document.createElement('div');
        const colors = {
            success: 'toast-success',
            error: 'toast-error',
            warning: 'toast-warning',
            info: 'toast-info'
        };

        toast.className = 'toast ' + (colors[type] || colors.info);
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(function() {
            toast.classList.add('show');
        }, 100);

        setTimeout(function() {
            toast.classList.remove('show');
            setTimeout(function() {
                toast.remove();
            }, 400);
        }, 4000);
    }

    window.showToast = showToast;

    // ============================================================
    // CONFIRM DELETE
    // ============================================================
    document.addEventListener('click', function(e) {
        const deleteBtn = e.target.closest('[data-delete]');
        if (deleteBtn) {
            e.preventDefault();
            const message = deleteBtn.dataset.message || 'Are you sure you want to delete this item?';
            if (confirm(message)) {
                const form = deleteBtn.closest('form') || document.getElementById('delete-form');
                if (form) {
                    form.submit();
                } else {
                    window.location.href = deleteBtn.href;
                }
            }
        }
    });

    // ============================================================
    // SEARCH INPUT
    // ============================================================
    document.addEventListener('input', function(e) {
        const searchInput = e.target.closest('input[type="search"], input[placeholder*="Search"]');
        if (searchInput) {
            const query = searchInput.value.toLowerCase().trim();
            const table = searchInput.closest('.overflow-x-auto')?.querySelector('table tbody');
            if (table) {
                const rows = table.querySelectorAll('tr');
                rows.forEach(function(row) {
                    const text = row.textContent.toLowerCase();
                    row.style.display = query === '' || text.includes(query) ? '' : 'none';
                });
            }
        }
    });

    // ============================================================
    // BULK SELECT
    // ============================================================
    document.addEventListener('change', function(e) {
        const selectAll = e.target.closest('[data-select-all]');
        if (selectAll) {
            const checked = selectAll.checked;
            const container = selectAll.closest('table') || selectAll.closest('.overflow-x-auto');
            if (container) {
                const checkboxes = container.querySelectorAll('input[type="checkbox"][data-select]');
                checkboxes.forEach(function(cb) {
                    cb.checked = checked;
                });
            }
        }
    });

    // ============================================================
    // MOBILE MENU TOGGLE
    // ============================================================
    document.addEventListener('click', function(e) {
        const toggle = e.target.closest('[data-mobile-toggle]');
        if (toggle) {
            const targetId = toggle.dataset.target || 'mobile-menu';
            const target = document.getElementById(targetId);
            if (target) {
                target.classList.toggle('hidden');
                target.classList.toggle('flex');
            }
        }
    });

    // ============================================================
    // DARK MODE TOGGLE (Global)
    // ============================================================
    function applyAdminTheme(isDark) {
        document.documentElement.classList.toggle('dark', isDark);
        document.documentElement.classList.toggle('light', !isDark);
        document.documentElement.dataset.theme = isDark ? 'dark' : 'light';
        document.body.classList.toggle('theme-dark', isDark);
        document.body.classList.toggle('theme-light', !isDark);
        document.body.dataset.theme = isDark ? 'dark' : 'light';
        document.documentElement.style.colorScheme = isDark ? 'dark' : 'light';
        localStorage.setItem('admin-dark-mode', String(isDark));
        window.dispatchEvent(new CustomEvent('flaxon-theme-change', { detail: { dark: isDark } }));
        return isDark;
    }

    function toggleDarkMode() {
        return applyAdminTheme(!document.documentElement.classList.contains('dark'));
    }

    window.applyAdminTheme = applyAdminTheme;
    window.toggleDarkMode = toggleDarkMode;

    // ============================================================
    // KEYBOARD SHORTCUTS
    // ============================================================
    document.addEventListener('keydown', function(e) {
        // Ctrl+Shift+/ to open search
        if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === '/') {
            e.preventDefault();
            const searchInput = document.querySelector('input[placeholder*="Search"]');
            if (searchInput) {
                searchInput.focus();
            }
        }

        // Escape to close modals
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal:not(.hidden)');
            modals.forEach(function(modal) {
                modal.classList.add('hidden');
            });
        }
    });

    // ============================================================
    // INITIALIZATION
    // ============================================================
})();
