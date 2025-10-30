// ===== AGNES HOTSPOT DETECTION SYSTEM - Main JavaScript =====

// Mobile Menu Toggle
document.addEventListener('DOMContentLoaded', function() {
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const navbarMenu = document.querySelector('.navbar-menu');
    
    if (mobileMenuToggle) {
        mobileMenuToggle.addEventListener('click', function() {
            navbarMenu.classList.toggle('active');
            this.classList.toggle('active');
        });
    }
    
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
});

// ===== UTILITY FUNCTIONS =====

/**
 * Format date to readable string
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

/**
 * Format time to readable string
 */
function formatTime(timeString) {
    const time = new Date(`2000-01-01 ${timeString}`);
    return time.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Calculate distance between two coordinates (Haversine formula)
 */
function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371; // Earth's radius in kilometers
    const dLat = toRadians(lat2 - lat1);
    const dLon = toRadians(lon2 - lon1);
    
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(toRadians(lat1)) * Math.cos(toRadians(lat2)) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
    
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

function toRadians(degrees) {
    return degrees * (Math.PI / 180);
}

/**
 * Show loading spinner
 */
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '<div class="loading-spinner"></div>';
    }
}

/**
 * Hide loading spinner
 */
function hideLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '';
    }
}

/**
 * Display notification
 */
function showNotification(message, type = 'info') {
    const messagesContainer = document.querySelector('.messages-container') || 
                             createMessagesContainer();
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    
    const icons = {
        'success': '✓',
        'error': '✕',
        'warning': '⚠',
        'info': 'ℹ'
    };
    
    alert.innerHTML = `
        <span class="alert-icon">${icons[type]}</span>
        <span class="alert-message">${message}</span>
        <button class="alert-close" onclick="this.parentElement.remove()">×</button>
    `;
    
    messagesContainer.appendChild(alert);
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 300);
    }, 5000);
}

function createMessagesContainer() {
    const container = document.createElement('div');
    container.className = 'messages-container';
    const mainContent = document.querySelector('.main-content');
    mainContent.insertBefore(container, mainContent.firstChild);
    return container;
}

// ===== FORM VALIDATION =====

/**
 * Validate form inputs
 */
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('error');
            isValid = false;
        } else {
            field.classList.remove('error');
        }
    });
    
    return isValid;
}

/**
 * Validate coordinates
 */
function validateCoordinates(lat, lng) {
    const latitude = parseFloat(lat);
    const longitude = parseFloat(lng);
    
    if (isNaN(latitude) || isNaN(longitude)) {
        return { valid: false, message: 'Coordinates must be numbers' };
    }
    
    // Caraga Region bounds (approximate)
    if (latitude < 7.5 || latitude > 10.5 || longitude < 124.5 || longitude > 127.0) {
        return { 
            valid: false, 
            message: 'Coordinates outside Caraga Region bounds' 
        };
    }
    
    return { valid: true };
}

// ===== API CALLS =====

/**
 * Fetch accidents data from API
 */
async function fetchAccidents(filters = {}) {
    try {
        const queryParams = new URLSearchParams(filters).toString();
        const response = await fetch(`/api/accidents/?${queryParams}`);
        
        if (!response.ok) {
            throw new Error('Failed to fetch accidents');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error fetching accidents:', error);
        showNotification('Error loading accidents data', 'error');
        return null;
    }
}

/**
 * Fetch hotspots data from API
 */
async function fetchHotspots() {
    try {
        const response = await fetch('/api/hotspots/');
        
        if (!response.ok) {
            throw new Error('Failed to fetch hotspots');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error fetching hotspots:', error);
        showNotification('Error loading hotspots data', 'error');
        return null;
    }
}

/**
 * Submit accident report
 */
async function submitAccidentReport(formData) {
    try {
        const response = await fetch('/api/reports/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to submit report');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error submitting report:', error);
        showNotification('Error submitting accident report', 'error');
        return null;
    }
}

/**
 * Get CSRF token from cookies
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// ===== DATA EXPORT =====

/**
 * Export data to CSV
 */
function exportToCSV(data, filename) {
    const csv = convertToCSV(data);
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
}

function convertToCSV(data) {
    if (!data || data.length === 0) return '';
    
    const headers = Object.keys(data[0]);
    const csvRows = [];
    
    // Add headers
    csvRows.push(headers.join(','));
    
    // Add data rows
    for (const row of data) {
        const values = headers.map(header => {
            const value = row[header];
            return `"${value}"`;
        });
        csvRows.push(values.join(','));
    }
    
    return csvRows.join('\n');
}

// ===== CHART UTILITIES =====

/**
 * Create a bar chart
 */
function createBarChart(canvasId, labels, data, label, backgroundColor) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                backgroundColor: backgroundColor || 'rgba(0, 48, 135, 0.7)',
                borderColor: 'rgba(0, 48, 135, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

/**
 * Create a line chart
 */
function createLineChart(canvasId, labels, data, label) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                borderColor: 'rgba(0, 48, 135, 1)',
                backgroundColor: 'rgba(0, 48, 135, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

/**
 * Create a pie chart
 */
function createPieChart(canvasId, labels, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    
    const colors = [
        'rgba(220, 20, 60, 0.8)',   // Red
        'rgba(0, 48, 135, 0.8)',    // Blue
        'rgba(255, 165, 0, 0.8)',   // Orange
        'rgba(40, 167, 69, 0.8)',   // Green
        'rgba(108, 117, 125, 0.8)'  // Gray
    ];
    
    return new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}

// ===== MAP UTILITIES =====

/**
 * Initialize Leaflet map
 */
function initializeMap(mapId, center = [9.0, 125.5], zoom = 9) {
    const map = L.map(mapId).setView(center, zoom);
    
    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(map);
    
    return map;
}

/**
 * Add accident marker to map
 */
function addAccidentMarker(map, accident) {
    const marker = L.marker([accident.latitude, accident.longitude]);
    
    const popupContent = `
        <div class="map-popup">
            <h4>${accident.incident_type}</h4>
            <p><strong>Location:</strong> ${accident.barangay}, ${accident.municipal}</p>
            <p><strong>Date:</strong> ${formatDate(accident.date_committed)}</p>
            <p><strong>Time:</strong> ${formatTime(accident.time_committed)}</p>
            <p><strong>Casualties:</strong> ${accident.victim_count}</p>
        </div>
    `;
    
    marker.bindPopup(popupContent);
    marker.addTo(map);
    
    return marker;
}

/**
 * Add hotspot circle to map
 */
function addHotspotCircle(map, hotspot) {
    const circle = L.circle([hotspot.center_latitude, hotspot.center_longitude], {
        color: '#DC143C',
        fillColor: '#DC143C',
        fillOpacity: 0.3,
        radius: hotspot.accident_count * 100 // Radius based on accident count
    });
    
    const popupContent = `
        <div class="map-popup hotspot">
            <h4>🔴 Hotspot Cluster ${hotspot.cluster_id}</h4>
            <p><strong>Location:</strong> ${hotspot.primary_location}</p>
            <p><strong>Accidents:</strong> ${hotspot.accident_count}</p>
            <p><strong>Total Casualties:</strong> ${hotspot.total_casualties}</p>
            <p><strong>Severity Score:</strong> ${hotspot.severity_score.toFixed(2)}</p>
        </div>
    `;
    
    circle.bindPopup(popupContent);
    circle.addTo(map);
    
    return circle;
}

// ===== PRINT FUNCTIONALITY =====

/**
 * Print current page
 */
function printPage() {
    window.print();
}

/**
 * Print specific element
 */
function printElement(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const printWindow = window.open('', '', 'height=600,width=800');
    printWindow.document.write('<html><head><title>Print</title>');
    printWindow.document.write('<link rel="stylesheet" href="/static/css/main.css">');
    printWindow.document.write('</head><body>');
    printWindow.document.write(element.innerHTML);
    printWindow.document.write('</body></html>');
    printWindow.document.close();
    printWindow.print();
}

// ===== LOADING SPINNER CSS (Add to page dynamically) =====
const spinnerStyles = `
    .loading-spinner {
        border: 4px solid rgba(0, 48, 135, 0.1);
        border-top: 4px solid rgba(0, 48, 135, 1);
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
        margin: 2rem auto;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
`;

// Add spinner styles to document
const styleSheet = document.createElement('style');
styleSheet.textContent = spinnerStyles;
document.head.appendChild(styleSheet);

// ===== EXPORT FUNCTIONS TO GLOBAL SCOPE =====
window.AGNESSystem = {
    formatDate,
    formatTime,
    calculateDistance,
    showLoading,
    hideLoading,
    showNotification,
    validateForm,
    validateCoordinates,
    fetchAccidents,
    fetchHotspots,
    submitAccidentReport,
    exportToCSV,
    createBarChart,
    createLineChart,
    createPieChart,
    initializeMap,
    addAccidentMarker,
    addHotspotCircle,
    printPage,
    printElement
};

console.log('AGNES Hotspot Detection System - JavaScript Loaded');