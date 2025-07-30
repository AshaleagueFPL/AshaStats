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
    
    // Load live table when switching to home tab
    if (tabName === 'home' && window.AppState.isDataLoaded) {
        loadLiveTable();
    }
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
                // Load live table after league is loaded
                await loadLiveTable();
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

// Live Table Loading
async function loadLiveTable() {
    console.log('Loading live table...');
    const tableContainer = document.getElementById('live-table-container');
    
    if (!tableContainer) {
        console.log('Live table container not found');
        return;
    }
    
    if (!window.AppState.isDataLoaded) {
        tableContainer.innerHTML = `
            <div class="live-table-placeholder">
                <p><i class="fas fa-cog"></i> Configure your league in Settings to view the live table</p>
            </div>
        `;
        return;
    }
    
    // Show loading state
    tableContainer.innerHTML = '<div class="loading-spinner"></div> Loading live table...';
    
    try {
        const response = await fetch('/api/live_table');
        const data = await response.json();
        
        console.log('Live table response:', data); // Debug log
        
        if (data.error) {
            tableContainer.innerHTML = `<div class="error-message">❌ ${data.error}</div>`;
            return;
        }
        
        if (data.is_pre_season) {
            displayPreSeasonTeams(data, tableContainer);
        } else {
            displayLiveTable(data, tableContainer);
        }
        
    } catch (error) {
        console.error('Live table error:', error);
        tableContainer.innerHTML = '<div class="error-message">❌ Failed to load live table</div>';
    }
}

function displayLiveTable(data, container) {
    let html = `
        <div class="live-table">
            <div class="live-table-header">
                <h3><i class="fas fa-trophy"></i> ${data.league_name}</h3>
                <p>Live Table - GW${data.current_gameweek} | ${data.total_teams} teams</p>
            </div>
            <div class="table-wrapper">
                <table class="live-table-grid">
                    <thead>
                        <tr>
                            <th>Pos</th>
                            <th>Team Name</th>
                            <th>Manager</th>
                            <th>Total</th>
                            <th>GW${data.current_gameweek}</th>
                        </tr>
                    </thead>
                    <tbody>
    `;
    
    data.table.forEach((team, index) => {
        const isTopThree = index < 3;
        const rowClass = isTopThree ? 'top-three' : '';
        
        let positionIcon = '';
        if (index === 0) positionIcon = '<i class="fas fa-crown" style="color: #ffd700;"></i>';
        else if (index === 1) positionIcon = '<i class="fas fa-medal" style="color: #c0c0c0;"></i>';
        else if (index === 2) positionIcon = '<i class="fas fa-medal" style="color: #cd7f32;"></i>';
        
        html += `
            <tr class="${rowClass}">
                <td class="position">${positionIcon} ${team.rank}</td>
                <td class="team-name">${team.team_name}</td>
                <td class="manager-name">${team.manager_name}</td>
                <td class="total-points">${team.total_points}</td>
                <td class="gw-points">${team.gameweek_points}</td>
            </tr>
        `;
    });
    
    html += `
                    </tbody>
                </table>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

function displayPreSeasonTeams(data, container) {
    console.log('Displaying pre-season teams:', data.teams); // Debug log
    
    let html = `
        <div class="teams-list">
            <div class="teams-list-header">
                <h3><i class="fas fa-users"></i> ${data.league_name}</h3>
                <p>Pre-Season - ${data.total_teams} teams ready</p>
            </div>
            <div class="teams-grid">
    `;
    
    // Display each team
    if (data.teams && data.teams.length > 0) {
        data.teams.forEach((team, index) => {
            console.log(`Team ${index + 1}:`, team); // Debug each team
            
            const teamName = team.team_name || 'Unknown Team';
            const managerName = team.manager_name || 'Unknown Manager';
            
            html += `
                <div class="team-card">
                    <div class="team-info">
                        <div class="team-name">${teamName}</div>
                        <div class="team-manager-name">${managerName}</div>
                    </div>
                </div>
            `;
        });
    } else {
        html += `
            <div class="no-teams">
                <p><i class="fas fa-exclamation-triangle"></i> No teams found in this league.</p>
                <p>Please check the league ID or try again.</p>
            </div>
        `;
    }
    
    html += `
            </div>
            <div class="pre-season-note">
                <p><i class="fas fa-info-circle"></i> Season hasn't started yet. The live table will appear once gameweek 1 begins.</p>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
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