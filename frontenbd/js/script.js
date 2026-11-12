/**
 * OmniPilot – Remote Delivery Engineer's OneStop Solution
 * Frontend Navigation & Interaction Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const sidebar = document.getElementById('sidebar');
  const mainWrapper = document.getElementById('mainWrapper');
  const toggleBtn = document.getElementById('sidebarToggle');
  const sidebarOverlay = document.getElementById('sidebarOverlay');
  const navItems = document.querySelectorAll('.nav-item, .sub-nav-item');
  const moduleViews = document.querySelectorAll('.module-view');
  const clickableCards = document.querySelectorAll('[data-target]');
  const backToOverviewBtns = document.querySelectorAll('.btn-back-overview');

  // Switch Active Module View
  function switchModule(targetId) {
    if (!targetId) return;

    // Check if target belongs to a sub-menu group, open its parent nav-group
    const targetElement = document.querySelector(`[data-target="${targetId}"]`);
    if (targetElement && targetElement.classList.contains('sub-nav-item')) {
      const parentGroup = targetElement.closest('.nav-group');
      if (parentGroup) {
        parentGroup.classList.add('open');
      }
    }

    // Update navigation active states
    navItems.forEach(item => {
      if (item.getAttribute('data-target') === targetId) {
        item.classList.add('active');
        // Ensure parent group is open
        const group = item.closest('.nav-group');
        if (group) group.classList.add('open');
      } else {
        item.classList.remove('active');
      }
    });

    // Update views
    moduleViews.forEach(view => {
      if (view.id === targetId) {
        view.classList.add('active-view');
      } else {
        view.classList.remove('active-view');
      }
    });

    // On mobile, close sidebar after navigation
    if (window.innerWidth <= 768) {
      sidebar.classList.remove('mobile-open');
      sidebarOverlay.classList.remove('active');
    }

    // Scroll to top of content
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // Handle accordion toggle for nav groups with submenu
  const navGroupHeaders = document.querySelectorAll('.nav-group > .nav-item');
  navGroupHeaders.forEach(header => {
    header.addEventListener('click', (e) => {
      const parentGroup = header.closest('.nav-group');
      if (parentGroup) {
        // Toggle open/close of accordion
        parentGroup.classList.toggle('open');
      }
    });
  });

  // Nav Item Clicks (Sidebar)
  navItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const target = item.getAttribute('data-target');
      if (target) {
        switchModule(target);
      }
    });
  });

  // Overview Page & Sub-service clickable cards
  clickableCards.forEach(card => {
    // Skip if it's already a nav item to avoid double binding
    if (card.classList.contains('nav-item') || card.classList.contains('sub-nav-item')) {
      return;
    }
    card.addEventListener('click', (e) => {
      e.preventDefault();
      const target = card.getAttribute('data-target');
      if (target) {
        switchModule(target);
      }
    });
  });

  // Back to overview buttons inside placeholders
  backToOverviewBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      switchModule('view-overview');
    });
  });

  // Toggle Sidebar collapse / mobile slide
  toggleBtn.addEventListener('click', () => {
    if (window.innerWidth <= 768) {
      const isOpen = sidebar.classList.toggle('mobile-open');
      sidebarOverlay.classList.toggle('active', isOpen);
    } else {
      sidebar.classList.toggle('collapsed');
      mainWrapper.classList.toggle('expanded');
    }
  });

  // Close mobile sidebar on backdrop click
  sidebarOverlay.addEventListener('click', () => {
    sidebar.classList.remove('mobile-open');
    sidebarOverlay.classList.remove('active');
  });

  // Handle window resizing gracefully
  window.addEventListener('resize', () => {
    if (window.innerWidth > 768) {
      sidebar.classList.remove('mobile-open');
      sidebarOverlay.classList.remove('active');
    }
  });
});
