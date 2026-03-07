document.addEventListener('DOMContentLoaded', function () {
    const urlParams = new URLSearchParams(window.location.search);
    const pathKey = 'sortState_' + window.location.pathname;

    let currentSortField = urlParams.get('sort');
    let currentSortDir = urlParams.get('dir');

    // Load from sessionStorage if not in URL but exists in storage
    if (!currentSortField) {
        const savedStateString = sessionStorage.getItem(pathKey);
        if (savedStateString) {
            try {
                const savedState = JSON.parse(savedStateString);
                if (savedState && savedState.sort && savedState.dir) {
                    urlParams.set('sort', savedState.sort);
                    urlParams.set('dir', savedState.dir);
                    window.location.search = urlParams.toString();
                    return; // Stop execution as page will reload
                }
            } catch (e) {
                console.error("Error reading saved sort state", e);
            }
        }
    } else {
        // Save current URL state to sessionStorage
        sessionStorage.setItem(pathKey, JSON.stringify({ sort: currentSortField, dir: currentSortDir || 'asc' }));
    }

    currentSortDir = currentSortDir || 'asc';
    const sortableTables = document.querySelectorAll('table.table-sortable');

    sortableTables.forEach(table => {
        const ths = table.querySelectorAll('th');

        ths.forEach(th => {
            if (th.classList.contains('no-sort')) return;
            const field = th.dataset.sortField;
            if (!field) return;

            th.style.cursor = 'pointer';

            // Create icon span
            const iconSpan = document.createElement('span');
            iconSpan.classList.add('ms-1', 'fas');

            if (field === currentSortField) {
                iconSpan.classList.add(currentSortDir === 'asc' ? 'fa-sort-up' : 'fa-sort-down', 'text-primary');
            } else {
                iconSpan.classList.add('fa-sort', 'text-muted');
                iconSpan.style.opacity = '0.3';
            }
            th.appendChild(iconSpan);

            th.addEventListener('click', () => {
                const newDir = (field === currentSortField && currentSortDir === 'asc') ? 'desc' : 'asc';
                const url = new URL(window.location.href);
                url.searchParams.set('sort', field);
                url.searchParams.set('dir', newDir);
                url.searchParams.delete('page');

                // Save before redirect
                sessionStorage.setItem(pathKey, JSON.stringify({ sort: field, dir: newDir }));
                window.location.href = url.toString();
            });
        });
    });
});
