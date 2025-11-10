/**
 * PM Document Intelligence - Main Application JavaScript
 * Handles PubNub real-time updates, notifications, and UI interactions
 */

// Global PubNub client instance
let pubnubClient = null;

/**
 * Initialize PubNub client with authentication
 */
async function initializePubNub() {
    try {
        const token = localStorage.getItem('auth_token');
        if (!token) {
            console.log('No auth token found, skipping PubNub initialization');
            return;
        }

        // Get PubNub credentials from server
        const response = await fetch('/api/realtime/status', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            console.error('Failed to get PubNub credentials');
            return;
        }

        const data = await response.json();

        if (!data.publish_key || !data.subscribe_key) {
            console.error('Missing PubNub keys');
            return;
        }

        // Initialize PubNub
        pubnubClient = new PubNub({
            publishKey: data.publish_key,
            subscribeKey: data.subscribe_key,
            uuid: data.user_id || 'anonymous',
            ssl: true,
            presenceTimeout: 120,
            heartbeatInterval: 60
        });

        // Subscribe to user's personal channel
        if (data.user_id) {
            pubnubClient.subscribe({
                channels: [`user-${data.user_id}`, 'all-users'],
                withPresence: true
            });

            console.log(`✓ PubNub initialized and subscribed to user-${data.user_id}`);
        }

        // Set up message listener
        pubnubClient.addListener({
            message: handlePubNubMessage,
            presence: handlePubNubPresence,
            status: handlePubNubStatus
        });

        // Make available globally
        window.pubnubClient = pubnubClient;

    } catch (error) {
        console.error('Error initializing PubNub:', error);
    }
}

/**
 * Handle incoming PubNub messages
 */
function handlePubNubMessage(event) {
    console.log('PubNub message received:', event);

    const message = event.message;
    const messageType = message.type;

    // Route message based on type
    switch (messageType) {
        case 'document_processing_started':
            handleProcessingStarted(message);
            break;
        case 'document_processing_progress':
            handleProcessingProgress(message);
            break;
        case 'document_processing_completed':
            handleProcessingCompleted(message);
            break;
        case 'document_processing_failed':
            handleProcessingFailed(message);
            break;
        case 'notification':
            handleNotification(message);
            break;
        case 'action_item_assigned':
            handleActionItemAssigned(message);
            break;
        default:
            console.log('Unknown message type:', messageType);
    }
}

/**
 * Handle PubNub presence events
 */
function handlePubNubPresence(event) {
    console.log('Presence event:', event);

    if (event.action === 'join') {
        console.log(`User ${event.uuid} joined ${event.channel}`);
    } else if (event.action === 'leave' || event.action === 'timeout') {
        console.log(`User ${event.uuid} left ${event.channel}`);
    }
}

/**
 * Handle PubNub status events
 */
function handlePubNubStatus(event) {
    if (event.category === 'PNConnectedCategory') {
        console.log('✓ Connected to PubNub');
    } else if (event.category === 'PNNetworkDownCategory') {
        console.warn('⚠ Network connection lost');
        showToast('Connection lost. Reconnecting...', 'warning');
    } else if (event.category === 'PNReconnectedCategory') {
        console.log('✓ Reconnected to PubNub');
        showToast('Connection restored', 'success');
    }
}

/**
 * Handle document processing started
 */
function handleProcessingStarted(message) {
    showToast(`Processing started: ${message.filename}`, 'info');

    // Trigger refresh of processing status
    const statusElement = document.getElementById('processing-status');
    if (statusElement) {
        htmx.trigger(statusElement, 'load');
    }
}

/**
 * Handle document processing progress
 */
function handleProcessingProgress(message) {
    const percentage = message.percentage || 0;
    const step = message.current_step || 'Processing';

    // Update progress bar if present
    const progressBar = document.querySelector(`[data-document-id="${message.document_id}"] .progress-bar`);
    if (progressBar) {
        progressBar.style.width = `${percentage}%`;
        progressBar.textContent = `${percentage}%`;
    }

    // Update progress text
    const progressText = document.querySelector(`[data-document-id="${message.document_id}"] .progress-text`);
    if (progressText) {
        progressText.textContent = step;
    }
}

/**
 * Handle document processing completed
 */
function handleProcessingCompleted(message) {
    showToast(`Document processed: ${message.filename}`, 'success');

    // Trigger refresh of document list
    document.body.dispatchEvent(new CustomEvent('documentUploaded'));

    // Refresh processing status
    const statusElement = document.getElementById('processing-status');
    if (statusElement) {
        htmx.trigger(statusElement, 'load');
    }

    // If on document page, refresh analysis
    if (window.location.pathname.includes('/document/')) {
        const analysisContent = document.getElementById('analysis-content');
        if (analysisContent) {
            htmx.trigger(analysisContent.closest('[hx-get]'), 'load');
        }
    }
}

/**
 * Handle document processing failed
 */
function handleProcessingFailed(message) {
    const errorMsg = message.error || 'Unknown error';
    showToast(`Processing failed: ${errorMsg}`, 'error');

    // Refresh processing status
    const statusElement = document.getElementById('processing-status');
    if (statusElement) {
        htmx.trigger(statusElement, 'load');
    }
}

/**
 * Handle general notification
 */
function handleNotification(message) {
    const priority = message.priority || 'info';
    const title = message.title || 'Notification';
    const body = message.message || '';

    // Show toast
    showToast(`${title}: ${body}`, priority);

    // Add to notifications panel
    addToNotificationsPanel(message);
}

/**
 * Handle action item assigned
 */
function handleActionItemAssigned(message) {
    showToast(`New action item assigned: ${message.title}`, 'info');

    // Update notifications count
    updateNotificationCount(1);
}

/**
 * Add notification to notifications panel
 */
function addToNotificationsPanel(notification) {
    const notificationList = document.getElementById('notification-list');
    if (!notificationList) return;

    // Remove "no notifications" message if present
    const emptyMessage = notificationList.querySelector('p');
    if (emptyMessage && emptyMessage.textContent.includes('No new notifications')) {
        emptyMessage.remove();
    }

    // Create notification element
    const notificationEl = document.createElement('div');
    notificationEl.className = 'p-4 border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer';
    notificationEl.innerHTML = `
        <div class="flex items-start space-x-3">
            <i class="fas ${getNotificationIcon(notification.priority)} ${getNotificationColor(notification.priority)} mt-1"></i>
            <div class="flex-1">
                <p class="text-sm font-medium text-gray-900 dark:text-white">${notification.title || 'Notification'}</p>
                <p class="text-xs text-gray-600 dark:text-gray-400 mt-1">${notification.message || ''}</p>
                <p class="text-xs text-gray-500 dark:text-gray-500 mt-1">${new Date().toLocaleTimeString()}</p>
            </div>
        </div>
    `;

    // Add to top of list
    notificationList.insertBefore(notificationEl, notificationList.firstChild);

    // Update unread count
    updateNotificationCount(1);
}

/**
 * Get icon for notification priority
 */
function getNotificationIcon(priority) {
    const icons = {
        'high': 'fa-exclamation-circle',
        'medium': 'fa-info-circle',
        'low': 'fa-bell',
        'info': 'fa-info-circle',
        'success': 'fa-check-circle',
        'warning': 'fa-exclamation-triangle',
        'error': 'fa-times-circle'
    };
    return icons[priority] || 'fa-bell';
}

/**
 * Get color for notification priority
 */
function getNotificationColor(priority) {
    const colors = {
        'high': 'text-red-500',
        'medium': 'text-yellow-500',
        'low': 'text-gray-500',
        'info': 'text-blue-500',
        'success': 'text-green-500',
        'warning': 'text-yellow-500',
        'error': 'text-red-500'
    };
    return colors[priority] || 'text-gray-500';
}

/**
 * Update notification count badge
 */
function updateNotificationCount(delta) {
    // Find all notification count elements
    const countElements = document.querySelectorAll('[x-data*="unread"]');

    countElements.forEach(el => {
        const alpineData = Alpine.$data(el);
        if (alpineData && typeof alpineData.unread !== 'undefined') {
            alpineData.unread += delta;
            if (alpineData.unread < 0) alpineData.unread = 0;
        }
    });
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const container = document.getElementById('flash-messages');
    if (!container) {
        console.warn('Toast container not found');
        return;
    }

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `flash-message flash-${type}`;
    toast.setAttribute('x-data', '{ show: true }');
    toast.setAttribute('x-show', 'show');
    toast.setAttribute('x-transition', '');

    const iconMap = {
        'success': 'check-circle',
        'error': 'exclamation-circle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle'
    };

    toast.innerHTML = `
        <div class="flex items-start">
            <i class="fas fa-${iconMap[type] || 'info-circle'} mr-2 mt-0.5"></i>
            <div class="flex-1">${message}</div>
            <button onclick="this.closest('.flash-message').remove()" class="ml-4 text-gray-400 hover:text-gray-600">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;

    container.appendChild(toast);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.remove();
    }, 5000);
}

/**
 * Subscribe to document channel for real-time updates
 */
function subscribeToDocument(documentId) {
    if (!pubnubClient) {
        console.warn('PubNub not initialized');
        return;
    }

    const channel = `doc-${documentId}`;
    pubnubClient.subscribe({
        channels: [channel],
        withPresence: true
    });

    console.log(`Subscribed to ${channel}`);
}

/**
 * Unsubscribe from document channel
 */
function unsubscribeFromDocument(documentId) {
    if (!pubnubClient) return;

    const channel = `doc-${documentId}`;
    pubnubClient.unsubscribe({
        channels: [channel]
    });

    console.log(`Unsubscribed from ${channel}`);
}

/**
 * Format file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Format date
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;

    return date.toLocaleDateString();
}

/**
 * Validate form
 */
function validateForm(formElement) {
    const requiredFields = formElement.querySelectorAll('[required]');
    let isValid = true;

    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            isValid = false;
            field.classList.add('border-red-500');

            // Remove error styling after user starts typing
            field.addEventListener('input', () => {
                field.classList.remove('border-red-500');
            }, { once: true });
        }
    });

    if (!isValid) {
        showToast('Please fill in all required fields', 'error');
    }

    return isValid;
}

/**
 * Copy to clipboard
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Copied to clipboard', 'success');
    } catch (error) {
        console.error('Failed to copy:', error);
        showToast('Failed to copy to clipboard', 'error');
    }
}

/**
 * Download file
 */
function downloadFile(url, filename) {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * Debounce function
 */
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

/**
 * Throttle function
 */
function throttle(func, limit) {
    let inThrottle;
    return function executedFunction(...args) {
        if (!inThrottle) {
            func(...args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Check if user is authenticated
 */
function isAuthenticated() {
    return !!localStorage.getItem('auth_token');
}

/**
 * Redirect to login if not authenticated
 */
function requireAuth() {
    if (!isAuthenticated()) {
        window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
    }
}

/**
 * Handle file upload with progress
 */
async function uploadFileWithProgress(file, onProgress) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        const formData = new FormData();
        formData.append('file', file);

        // Progress tracking
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                if (onProgress) onProgress(percentComplete);
            }
        });

        // Handle completion
        xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                resolve(JSON.parse(xhr.responseText));
            } else {
                reject(new Error(`Upload failed: ${xhr.statusText}`));
            }
        });

        // Handle errors
        xhr.addEventListener('error', () => {
            reject(new Error('Upload failed'));
        });

        // Send request
        xhr.open('POST', '/api/v1/documents/upload');
        xhr.setRequestHeader('Authorization', `Bearer ${localStorage.getItem('auth_token')}`);
        xhr.send(formData);
    });
}

/**
 * Initialize keyboard shortcuts
 */
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + K: Focus search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('input[type="text"][placeholder*="Search"]');
            if (searchInput) searchInput.focus();
        }

        // Ctrl/Cmd + U: Go to upload
        if ((e.ctrlKey || e.metaKey) && e.key === 'u') {
            e.preventDefault();
            window.location.href = '/upload';
        }

        // Escape: Close modals/dropdowns
        if (e.key === 'Escape') {
            document.querySelectorAll('[x-data*="open"]').forEach(el => {
                const alpineData = Alpine.$data(el);
                if (alpineData && alpineData.open) {
                    alpineData.open = false;
                }
            });
        }
    });
}

/**
 * Initialize accessibility features
 */
function initializeAccessibility() {
    // Add skip to main content link
    const skipLink = document.createElement('a');
    skipLink.href = '#main-content';
    skipLink.className = 'sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-joy-teal focus:text-white focus:rounded';
    skipLink.textContent = 'Skip to main content';
    document.body.insertBefore(skipLink, document.body.firstChild);

    // Add main content ID if not present
    const main = document.querySelector('main');
    if (main && !main.id) {
        main.id = 'main-content';
    }

    // Ensure all images have alt text
    document.querySelectorAll('img:not([alt])').forEach(img => {
        console.warn('Image missing alt text:', img.src);
    });
}

/**
 * Initialize on page load
 */
document.addEventListener('DOMContentLoaded', () => {
    console.log('PM Document Intelligence - Initializing...');

    // Initialize PubNub for real-time updates
    initializePubNub();

    // Initialize keyboard shortcuts
    initializeKeyboardShortcuts();

    // Initialize accessibility features
    initializeAccessibility();

    // Set up global error handler
    window.addEventListener('unhandledrejection', (event) => {
        console.error('Unhandled promise rejection:', event.reason);
        showToast('An error occurred. Please try again.', 'error');
    });

    // Make utility functions globally available
    window.showToast = showToast;
    window.formatFileSize = formatFileSize;
    window.formatDate = formatDate;
    window.copyToClipboard = copyToClipboard;
    window.downloadFile = downloadFile;
    window.subscribeToDocument = subscribeToDocument;
    window.unsubscribeFromDocument = unsubscribeFromDocument;

    console.log('✓ Application initialized');
});

// Handle page visibility changes (pause/resume PubNub)
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        console.log('Page hidden - maintaining PubNub connection');
    } else {
        console.log('Page visible - resuming');
        // Refresh any stale data
        htmx.trigger(document.body, 'load');
    }
});

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (pubnubClient) {
        pubnubClient.unsubscribeAll();
    }
});
