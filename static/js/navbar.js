/**
 * Smart Responsive Navbar (Priority Navigation) - "Cloning & Isolation" Version
 * Solves the missing "More" button and "Profile" cutting issues once and for all.
 */

(function ($) {
    'use strict';

    let isProcessing = false;
    let cachedItemWidths = null;

    function cleanupOffcanvas() {
        if (window.innerWidth >= 768) {
            const offcanvasEl = document.getElementById('mobileMenu');
            if (offcanvasEl) {
                const bsOffcanvas = bootstrap.Offcanvas.getInstance(offcanvasEl);
                if (bsOffcanvas && offcanvasEl.classList.contains('show')) {
                    bsOffcanvas.hide();
                    $('.offcanvas-backdrop').remove();
                    $('body').css({ overflow: '', paddingRight: '' }).removeClass('offcanvas-open');
                }
            }
        }
    }

    function initMeasurement() {
        // Measure everything once in a safe state and cache it
        const $navItems = $('#dynamicNavItems');
        const $allOriginalItems = $navItems.find('.nav-item').not('#dynamicMoreDropdown');

        cachedItemWidths = [];
        $allOriginalItems.each(function () {
            // Force visible temporarily to measure
            const $item = $(this);
            const wasHidden = $item.hasClass('d-none');
            $item.removeClass('d-none');
            const width = this.getBoundingClientRect().width + 8; // Including small gap
            cachedItemWidths.push({
                el: $item,
                width: width,
                priority: parseInt($item.data('priority') || 0),
                urlName: $item.data('url-name'),
                id: $item.index() // Stable identifier
            });
            if (wasHidden) $item.addClass('d-none');
        });
    }

    function handleNavbarResponsiveness() {
        if (isProcessing) return;
        isProcessing = true;

        const $navItems = $('#dynamicNavItems');
        const $moreDropdown = $('#dynamicMoreDropdown');
        const $moreItemsList = $('#moreDropdownItems');
        const collapseContainer = document.getElementById('mainNavbar');

        if (!$navItems.length || !collapseContainer) {
            isProcessing = false;
            return;
        }

        // 1. Mobile Check
        if (window.innerWidth < 768) {
            $navItems.find('.nav-item').removeClass('d-none');
            $moreDropdown.addClass('d-none');
            isProcessing = false;
            return;
        }

        // 2. Refresh measurements if needed
        if (!cachedItemWidths) initMeasurement();

        // 3. Calculate Available Space
        // We account for 'User Profile' specifically as it has a known ID now
        const userDropdown = document.getElementById('userProfileDropdown');
        const userWidth = userDropdown ? userDropdown.getBoundingClientRect().width : 0;

        const totalWidth = collapseContainer.clientWidth;
        const moreBtnWidth = 110; // Comfortable width for "More" button
        const safetyBuffer = 50; // Slightly increased for the new divider spacing
        const availableSpace = totalWidth - userWidth - safetyBuffer;

        // 4. Determine Visibility
        // Reset state in memory first
        const items = [...cachedItemWidths].sort((a, b) => b.priority - a.priority); // High priority first
        let currentWidth = 0;
        let visibleCount = 0;
        let needsMore = false;

        // First pass: Calculate how many fit
        for (let i = 0; i < items.length; i++) {
            if (currentWidth + items[i].width <= availableSpace) {
                currentWidth += items[i].width;
                visibleCount++;
            } else {
                needsMore = true;
                break;
            }
        }

        // If we need 'More', we must account for the 'More' button width and re-evaluate
        if (needsMore) {
            currentWidth = 0;
            visibleCount = 0;
            const spaceWithMore = availableSpace - moreBtnWidth;
            for (let i = 0; i < items.length; i++) {
                if (currentWidth + items[i].width <= spaceWithMore) {
                    currentWidth += items[i].width;
                    visibleCount++;
                } else {
                    break;
                }
            }
        }

        // 5. Apply to DOM
        // Sort back to original visual order (by index) to apply display states
        const visibleItems = items.slice(0, visibleCount);
        const hiddenItems = items.slice(visibleCount);

        // Update Nav Bar
        $navItems.find('.nav-item').not('#dynamicMoreDropdown').addClass('d-none');
        visibleItems.forEach(item => item.el.removeClass('d-none'));

        // Update "More" Dropdown
        $moreItemsList.empty();
        if (hiddenItems.length > 0) {
            $moreDropdown.removeClass('d-none');
            let hasActiveChild = false;

            // Hidden items should be in their priority order or original order?
            // User usually expects original order in dropdown.
            hiddenItems.sort((a, b) => a.id - b.id);

            hiddenItems.forEach(item => {
                const link = item.el.find('a');
                const isActive = link.hasClass('active');
                if (isActive) hasActiveChild = true;

                const $li = $('<li>');
                const $dropdownLink = $('<a>')
                    .addClass('dropdown-item d-flex align-items-center gap-2 py-2 px-3')
                    .attr('href', link.attr('href'))
                    .html(link.html());

                if (isActive) $dropdownLink.addClass('active');
                $moreItemsList.append($li.append($dropdownLink));
            });

            if (hasActiveChild) {
                $moreDropdown.find('.nav-link').addClass('active');
            } else {
                $moreDropdown.find('.nav-link').removeClass('active');
            }
        } else {
            $moreDropdown.addClass('d-none');
        }

        isProcessing = false;
    }

    // 6. Initialization
    $(document).ready(function () {
        initMeasurement();
        handleNavbarResponsiveness();

        const navContainer = document.getElementById('mainNavbar');
        if (navContainer) {
            const observer = new ResizeObserver(() => {
                cleanupOffcanvas();
                handleNavbarResponsiveness();
            });
            observer.observe(navContainer);
        }
    });

    // Handle orientation change and extreme resize
    $(window).on('resize orientationchange', function () {
        cachedItemWidths = null; // Re-measure on window/layout level changes
        handleNavbarResponsiveness();
    });

})(jQuery);
