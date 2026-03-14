// Main JavaScript file for WealthWise
// General utilities and initialization

// DOM utility functions
function getEl(id) {
  return document.getElementById(id);
}

function getAllEl(selector, parent = document) {
  return parent.querySelectorAll(selector);
}

function getOneEl(selector, parent = document) {
  return parent.querySelector(selector);
}

function addClass(el, className) {
  if (el) el.classList.add(className);
}

function removeClass(el, className) {
  if (el) el.classList.remove(className);
}

function toggleClass(el, className) {
  if (el) el.classList.toggle(className);
}

function show(el) {
  if (el) el.style.display = '';
}

function hide(el) {
  if (el) el.style.display = 'none';
}

function setText(el, text) {
  if (el) el.textContent = text;
}

function getValue(el) {
  return el ? el.value : '';
}

function setValue(el, value) {
  if (el) el.value = value;
}

// Currency formatting
function formatCurrency(amount) {
  if (!amount) return '₹0';

  const absAmount = Math.abs(amount);

  if (absAmount >= 10000000) {
    return '₹' + (Math.round(amount / 10000000 * 100) / 100) + 'Cr';
  } else if (absAmount >= 100000) {
    return '₹' + (Math.round(amount / 100000 * 100) / 100) + 'L';
  } else if (absAmount >= 1000) {
    return '₹' + (Math.round(amount / 1000 * 100) / 100) + 'K';
  } else {
    return '₹' + Math.round(amount);
  }
}

// Number formatting
function formatNumber(num) {
  if (!num) return '0';
  return Math.round(num).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// Debounce function
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Toast notification
function showToast(message, type = 'info', duration = 3000) {
  // Remove existing toasts
  const existingToasts = document.querySelectorAll('.toast');
  existingToasts.forEach(toast => toast.remove());

  // Create new toast
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;

  // Add styles if not present
  if (!document.getElementById('toast-styles')) {
    const style = document.createElement('style');
    style.id = 'toast-styles';
    style.textContent = `
      .toast {
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        border-radius: 0.5rem;
        color: white;
        z-index: 10000;
        animation: slideInUp 0.3s ease-out;
        font-weight: 500;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
      }
      .toast-success { background: #00C9B1; }
      .toast-error { background: #FF6B6B; }
      .toast-info { background: #008B9E; }
      .toast-warning { background: #F5A623; }
      @keyframes slideInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
      }
    `;
    document.head.appendChild(style);
  }

  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), duration);
}

// Tab switching functionality
function initTabs() {
  const tabButtons = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');

  tabButtons.forEach(button => {
    button.addEventListener('click', () => {
      const tabId = button.dataset.tab;

      // Remove active class from all buttons and contents
      tabButtons.forEach(btn => btn.classList.remove('active'));
      tabContents.forEach(content => content.classList.remove('active'));

      // Add active class to clicked button and corresponding content
      button.classList.add('active');
      const targetContent = document.getElementById(tabId);
      if (targetContent) {
        targetContent.classList.add('active');
      }
    });
  });
}

// Form validation
function validateEmail(email) {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
}

function validateRequired(value) {
  return value && value.trim().length > 0;
}

function validateNumber(value, min = 0, max = Infinity) {
  const num = parseFloat(value);
  return !isNaN(num) && num >= min && num <= max;
}

// API error handling
function handleApiError(error, defaultMessage = 'An error occurred') {
  console.error('API Error:', error);
  const message = error.message || defaultMessage;
  showToast(message, 'error');
  return message;
}

// Loading states
function setLoading(element, loading = true) {
  if (!element) return;

  if (loading) {
    element.disabled = true;
    element.dataset.originalText = element.textContent;
    element.textContent = 'Loading...';
  } else {
    element.disabled = false;
    if (element.dataset.originalText) {
      element.textContent = element.dataset.originalText;
    }
  }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  console.log('🚀 WealthWise initialized');

  // Initialize tabs if they exist
  initTabs();

  // Add any global event listeners here
  document.addEventListener('keydown', function(e) {
    // Global keyboard shortcuts can be added here
  });
});
