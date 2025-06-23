// Global App State - Shared across all files
window.AppState = {
    currentGameweek: 1,
    maxGameweek: 38,
    isDataLoaded: false,
    availableStats: []
};

// Initialize App - Wait for all scripts to load
document.addEventListener('DOMContentLoaded', function() {
    // Wait a moment to ensure all scripts are loaded
    setTimeout(() => {
        console.log('DOM loaded, initializing app...');
        loadSettings();
        initializeApp();
    }, 100);
});

// Tab Management
function switchTab(tabName) {
    // Update navigation
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    document.querySelector(`[onclick="switchTab('${tabName}')"]`).classList.add('active');
    
    // Update content
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    document.getElementById(`${tabName}-tab`).classList.add('active');
}

// Theme Management
function toggleTheme() {
    const isDark = document.getElementById('dark-mode').checked;
    document.body.setAttribute('data-theme', isDark ? 'dark' : 'light');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
}

function loadSettings() {
    // Load theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.body.setAttribute('data-theme', savedTheme);
    
    // Set dark mode toggle
    const darkModeToggle = document.getElementById('dark-mode');
    if (darkModeToggle) {
        darkModeToggle.checked = savedTheme === 'dark';
    }
    
    // Load league ID
    const savedLeagueId = localStorage.getItem('leagueId');
    const leagueInput = document.getElementById('league-id');
    if (leagueInput && savedLeagueId) {
        leagueInput.value = savedLeagueId;
    }
}

// App Initialization
async function initializeApp() {
    console.log('Initializing app...');
    try {
        const response = await fetch('/api/initialize');
        const data = await response.json();
        
        console.log('Initialize response:', data);
        
        if (data.success) {
            window.AppState.currentGameweek = data.current_gameweek;
            window.AppState.maxGameweek = data.total_gameweeks;
            
            // Call stats functions if they're available
            if (typeof updateGameweekDisplay === 'function') {
                updateGameweekDisplay();
            }
            
            if (typeof loadAvailableStats === 'function') {
                await loadAvailableStats();
            }
            
            // Load league if saved
            const savedLeagueId = localStorage.getItem('leagueId');
            if (savedLeagueId && typeof loadLeague === 'function') {
                await loadLeague(savedLeagueId);
            }
            
            updateAppInfo();
        } else {
            showError('Failed to initialize app: ' + data.error);
        }
    } catch (error) {
        console.error('Initialization error:', error);
        showError('Failed to connect to server');
    }
}

// Utility Functions
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    errorDiv.style.position = 'fixed';
    errorDiv.style.top = '20px';
    errorDiv.style.left = '20px';
    errorDiv.style.right = '20px';
    errorDiv.style.zIndex = '1000';
    
    document.body.appendChild(errorDiv);
    
    setTimeout(() => {
        if (errorDiv.parentNode) {
            errorDiv.parentNode.removeChild(errorDiv);
        }
    }, 5000);
}

function refreshData() {
    initializeApp();
}

function updateAppInfo() {
    const currentGwEl = document.getElementById('info-current-gw');
    const teamCountEl = document.getElementById('info-team-count');
    
    if (currentGwEl) currentGwEl.textContent = window.AppState.currentGameweek;
    if (teamCountEl) teamCountEl.textContent = window.AppState.isDataLoaded ? 'Loaded' : 'Not loaded';
}

// Service Worker Registration for PWA
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/sw.js')
            .then(function(registration) {
                console.log('SW registered: ', registration);
            })
            .catch(function(registrationError) {
                console.log('SW registration failed: ', registrationError);
            });
    });
}