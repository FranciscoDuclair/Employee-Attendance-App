/**
 * Responsive JavaScript for Employee Attendance System
 * Handles device-specific functionality and responsive behavior
 */

(function() {
    'use strict';

    // Device detection and responsive utilities
    const ResponsiveUtils = {
        // Device type detection
        isMobile: function() {
            return window.innerWidth <= 768;
        },
        
        isTablet: function() {
            return window.innerWidth > 768 && window.innerWidth <= 1024;
        },
        
        isDesktop: function() {
            return window.innerWidth > 1024;
        },
        
        // Touch device detection
        isTouchDevice: function() {
            return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
        },
        
        // Get current breakpoint
        getCurrentBreakpoint: function() {
            const width = window.innerWidth;
            if (width <= 480) return 'xs';
            if (width <= 767) return 'sm';
            if (width <= 991) return 'md';
            if (width <= 1199) return 'lg';
            if (width <= 1399) return 'xl';
            return 'xxl';
        },
        
        // Orientation detection
        isLandscape: function() {
            return window.innerWidth > window.innerHeight;
        },
        
        isPortrait: function() {
            return window.innerWidth <= window.innerHeight;
        }
    };

    // Responsive behavior manager
    const ResponsiveBehavior = {
        init: function() {
            this.setupEventListeners();
            this.handleInitialLoad();
            this.setupTouchOptimizations();
            this.setupKeyboardOptimizations();
            this.setupAccessibilityFeatures();
        },
        
        setupEventListeners: function() {
            // Window resize handler with debouncing
            let resizeTimeout;
            window.addEventListener('resize', function() {
                clearTimeout(resizeTimeout);
                resizeTimeout = setTimeout(function() {
                    ResponsiveBehavior.handleResize();
                }, 250);
            });
            
            // Orientation change handler
            window.addEventListener('orientationchange', function() {
                setTimeout(function() {
                    ResponsiveBehavior.handleOrientationChange();
                }, 100);
            });
            
            // Scroll handler for mobile navigation
            let lastScrollTop = 0;
            window.addEventListener('scroll', function() {
                ResponsiveBehavior.handleScroll(lastScrollTop);
                lastScrollTop = window.pageYOffset;
            });
        },
        
        handleInitialLoad: function() {
            this.optimizeForDevice();
            this.setupMobileNavigation();
            this.setupResponsiveTables();
            this.setupResponsiveModals();
            this.setupResponsiveForms();
            this.setupResponsiveCharts();
        },
        
        handleResize: function() {
            this.optimizeForDevice();
            this.adjustTableDisplay();
            this.adjustModalSizes();
            this.adjustChartSizes();
            this.handleNavigationCollapse();
        },
        
        handleOrientationChange: function() {
            // Force recalculation of viewport height for mobile browsers
            if (ResponsiveUtils.isMobile()) {
                document.documentElement.style.setProperty('--vh', window.innerHeight * 0.01 + 'px');
            }
            
            this.adjustForOrientation();
            this.optimizeForDevice();
        },
        
        handleScroll: function(lastScrollTop) {
            const currentScrollTop = window.pageYOffset;
            
            // Hide/show navigation on mobile when scrolling
            if (ResponsiveUtils.isMobile()) {
                const navbar = document.querySelector('.navbar');
                if (navbar) {
                    if (currentScrollTop > lastScrollTop && currentScrollTop > 100) {
                        // Scrolling down
                        navbar.style.transform = 'translateY(-100%)';
                    } else {
                        // Scrolling up
                        navbar.style.transform = 'translateY(0)';
                    }
                }
            }
        },
        
        optimizeForDevice: function() {
            const breakpoint = ResponsiveUtils.getCurrentBreakpoint();
            document.body.setAttribute('data-breakpoint', breakpoint);
            
            // Add device-specific classes
            document.body.classList.toggle('is-mobile', ResponsiveUtils.isMobile());
            document.body.classList.toggle('is-tablet', ResponsiveUtils.isTablet());
            document.body.classList.toggle('is-desktop', ResponsiveUtils.isDesktop());
            document.body.classList.toggle('is-touch', ResponsiveUtils.isTouchDevice());
            document.body.classList.toggle('is-landscape', ResponsiveUtils.isLandscape());
            document.body.classList.toggle('is-portrait', ResponsiveUtils.isPortrait());
        },
        
        setupMobileNavigation: function() {
            // Auto-close mobile navigation when clicking outside
            document.addEventListener('click', function(e) {
                if (ResponsiveUtils.isMobile()) {
                    const navbar = document.querySelector('.navbar-collapse');
                    const toggler = document.querySelector('.navbar-toggler');
                    
                    if (navbar && navbar.classList.contains('show') && 
                        !navbar.contains(e.target) && !toggler.contains(e.target)) {
                        const bsCollapse = new bootstrap.Collapse(navbar, {toggle: false});
                        bsCollapse.hide();
                    }
                }
            });
            
            // Close mobile navigation when clicking on nav links
            document.querySelectorAll('.navbar-nav .nav-link').forEach(function(link) {
                link.addEventListener('click', function() {
                    if (ResponsiveUtils.isMobile()) {
                        const navbar = document.querySelector('.navbar-collapse');
                        if (navbar && navbar.classList.contains('show')) {
                            const bsCollapse = new bootstrap.Collapse(navbar, {toggle: false});
                            bsCollapse.hide();
                        }
                    }
                });
            });
        },
        
        setupResponsiveTables: function() {
            const tables = document.querySelectorAll('.table');
            tables.forEach(function(table) {
                if (!table.closest('.table-responsive')) {
                    const wrapper = document.createElement('div');
                    wrapper.className = 'table-responsive';
                    table.parentNode.insertBefore(wrapper, table);
                    wrapper.appendChild(table);
                }
                
                // Add mobile-friendly table behavior
                if (ResponsiveUtils.isMobile()) {
                    table.classList.add('table-sm');
                }
            });
        },
        
        setupResponsiveModals: function() {
            // Adjust modal sizes based on device
            document.querySelectorAll('.modal').forEach(function(modal) {
                modal.addEventListener('show.bs.modal', function() {
                    const dialog = modal.querySelector('.modal-dialog');
                    if (ResponsiveUtils.isMobile()) {
                        dialog.classList.add('modal-fullscreen-sm-down');
                    }
                });
            });
        },
        
        setupResponsiveForms: function() {
            // Optimize form inputs for mobile
            if (ResponsiveUtils.isMobile()) {
                document.querySelectorAll('input[type="email"]').forEach(function(input) {
                    input.setAttribute('autocomplete', 'email');
                    input.setAttribute('autocapitalize', 'none');
                });
                
                document.querySelectorAll('input[type="tel"]').forEach(function(input) {
                    input.setAttribute('autocomplete', 'tel');
                });
                
                document.querySelectorAll('input[type="text"]').forEach(function(input) {
                    if (input.name && input.name.includes('name')) {
                        input.setAttribute('autocomplete', 'name');
                    }
                });
            }
        },
        
        setupResponsiveCharts: function() {
            // Handle chart responsiveness
            if (typeof Chart !== 'undefined') {
                Chart.defaults.responsive = true;
                Chart.defaults.maintainAspectRatio = false;
            }
        },
        
        setupTouchOptimizations: function() {
            if (ResponsiveUtils.isTouchDevice()) {
                // Add touch-friendly classes
                document.body.classList.add('touch-device');
                
                // Optimize button sizes for touch
                document.querySelectorAll('.btn').forEach(function(btn) {
                    if (!btn.classList.contains('btn-sm') && !btn.classList.contains('btn-lg')) {
                        btn.style.minHeight = '44px';
                        btn.style.minWidth = '44px';
                    }
                });
                
                // Add touch feedback
                document.querySelectorAll('.btn, .card, .list-group-item').forEach(function(element) {
                    element.addEventListener('touchstart', function() {
                        this.classList.add('touch-active');
                    });
                    
                    element.addEventListener('touchend', function() {
                        setTimeout(() => {
                            this.classList.remove('touch-active');
                        }, 150);
                    });
                });
            }
        },
        
        setupKeyboardOptimizations: function() {
            // Improve keyboard navigation
            document.addEventListener('keydown', function(e) {
                // ESC key closes modals and dropdowns
                if (e.key === 'Escape') {
                    // Close open modals
                    document.querySelectorAll('.modal.show').forEach(function(modal) {
                        const bsModal = bootstrap.Modal.getInstance(modal);
                        if (bsModal) bsModal.hide();
                    });
                    
                    // Close open dropdowns
                    document.querySelectorAll('.dropdown-menu.show').forEach(function(dropdown) {
                        const toggle = dropdown.previousElementSibling;
                        if (toggle) {
                            const bsDropdown = bootstrap.Dropdown.getInstance(toggle);
                            if (bsDropdown) bsDropdown.hide();
                        }
                    });
                }
            });
        },
        
        setupAccessibilityFeatures: function() {
            // Add skip navigation link
            const skipLink = document.createElement('a');
            skipLink.href = '#main-content';
            skipLink.className = 'sr-only sr-only-focusable btn btn-primary';
            skipLink.textContent = 'Skip to main content';
            skipLink.style.position = 'absolute';
            skipLink.style.top = '10px';
            skipLink.style.left = '10px';
            skipLink.style.zIndex = '9999';
            document.body.insertBefore(skipLink, document.body.firstChild);
            
            // Add main content landmark
            const mainContent = document.querySelector('main') || document.querySelector('[role="main"]');
            if (mainContent && !mainContent.id) {
                mainContent.id = 'main-content';
            }
            
            // Improve focus management
            document.querySelectorAll('.modal').forEach(function(modal) {
                modal.addEventListener('shown.bs.modal', function() {
                    const firstInput = modal.querySelector('input, button, select, textarea');
                    if (firstInput) firstInput.focus();
                });
            });
        },
        
        adjustTableDisplay: function() {
            if (ResponsiveUtils.isMobile()) {
                document.querySelectorAll('.table').forEach(function(table) {
                    // Hide less important columns on mobile
                    const headers = table.querySelectorAll('th');
                    const rows = table.querySelectorAll('tbody tr');
                    
                    headers.forEach(function(header, index) {
                        const headerText = header.textContent.toLowerCase();
                        const shouldHide = headerText.includes('created') || 
                                         headerText.includes('updated') ||
                                         headerText.includes('description') ||
                                         (index > 4); // Hide columns after the 5th
                        
                        if (shouldHide) {
                            header.classList.add('d-none', 'd-md-table-cell');
                            rows.forEach(function(row) {
                                const cell = row.cells[index];
                                if (cell) {
                                    cell.classList.add('d-none', 'd-md-table-cell');
                                }
                            });
                        }
                    });
                });
            }
        },
        
        adjustModalSizes: function() {
            document.querySelectorAll('.modal-dialog').forEach(function(dialog) {
                if (ResponsiveUtils.isMobile()) {
                    dialog.classList.add('modal-fullscreen-sm-down');
                } else {
                    dialog.classList.remove('modal-fullscreen-sm-down');
                }
            });
        },
        
        adjustChartSizes: function() {
            // Trigger chart resize if Chart.js is available
            if (typeof Chart !== 'undefined') {
                Chart.helpers.each(Chart.instances, function(instance) {
                    instance.resize();
                });
            }
        },
        
        adjustForOrientation: function() {
            if (ResponsiveUtils.isMobile()) {
                const isLandscape = ResponsiveUtils.isLandscape();
                
                // Adjust navbar height in landscape mode
                const navbar = document.querySelector('.navbar');
                if (navbar) {
                    if (isLandscape) {
                        navbar.style.minHeight = '50px';
                    } else {
                        navbar.style.minHeight = '';
                    }
                }
                
                // Adjust modal heights in landscape mode
                document.querySelectorAll('.modal-body').forEach(function(modalBody) {
                    if (isLandscape) {
                        modalBody.style.maxHeight = '60vh';
                        modalBody.style.overflowY = 'auto';
                    } else {
                        modalBody.style.maxHeight = '';
                        modalBody.style.overflowY = '';
                    }
                });
            }
        },
        
        handleNavigationCollapse: function() {
            // Auto-collapse navigation on desktop if it was open
            if (ResponsiveUtils.isDesktop()) {
                const navbar = document.querySelector('.navbar-collapse');
                if (navbar && navbar.classList.contains('show')) {
                    const bsCollapse = new bootstrap.Collapse(navbar, {toggle: false});
                    bsCollapse.hide();
                }
            }
        }
    };

    // Performance optimization utilities
    const PerformanceOptimizer = {
        init: function() {
            this.optimizeImages();
            this.setupLazyLoading();
            this.optimizeAnimations();
        },
        
        optimizeImages: function() {
            // Add loading="lazy" to images
            document.querySelectorAll('img').forEach(function(img) {
                if (!img.hasAttribute('loading')) {
                    img.setAttribute('loading', 'lazy');
                }
            });
        },
        
        setupLazyLoading: function() {
            // Implement intersection observer for lazy loading
            if ('IntersectionObserver' in window) {
                const imageObserver = new IntersectionObserver(function(entries, observer) {
                    entries.forEach(function(entry) {
                        if (entry.isIntersecting) {
                            const img = entry.target;
                            if (img.dataset.src) {
                                img.src = img.dataset.src;
                                img.removeAttribute('data-src');
                                observer.unobserve(img);
                            }
                        }
                    });
                });
                
                document.querySelectorAll('img[data-src]').forEach(function(img) {
                    imageObserver.observe(img);
                });
            }
        },
        
        optimizeAnimations: function() {
            // Respect user's motion preferences
            if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
                document.documentElement.style.setProperty('--animation-duration', '0.01ms');
                document.documentElement.style.setProperty('--transition-duration', '0.01ms');
            }
        }
    };

    // Network-aware optimizations
    const NetworkOptimizer = {
        init: function() {
            if ('connection' in navigator) {
                this.handleConnectionChange();
                navigator.connection.addEventListener('change', this.handleConnectionChange.bind(this));
            }
        },
        
        handleConnectionChange: function() {
            const connection = navigator.connection;
            const isSlowConnection = connection.effectiveType === 'slow-2g' || 
                                   connection.effectiveType === '2g' ||
                                   connection.saveData;
            
            document.body.classList.toggle('slow-connection', isSlowConnection);
            
            if (isSlowConnection) {
                // Disable non-essential animations and effects
                document.documentElement.style.setProperty('--animation-duration', '0.01ms');
                
                // Reduce image quality
                document.querySelectorAll('img').forEach(function(img) {
                    if (img.srcset) {
                        img.removeAttribute('srcset');
                    }
                });
            }
        }
    };

    // Initialize everything when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            ResponsiveBehavior.init();
            PerformanceOptimizer.init();
            NetworkOptimizer.init();
        });
    } else {
        ResponsiveBehavior.init();
        PerformanceOptimizer.init();
        NetworkOptimizer.init();
    }

    // Expose utilities globally for use in other scripts
    window.ResponsiveUtils = ResponsiveUtils;
    window.ResponsiveBehavior = ResponsiveBehavior;

})();
