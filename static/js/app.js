// Global App State - Shared across all files
window.AppState = {
    currentGameweek: 1,
    maxGameweek: 38,
    isDataLoaded: false,
    availableStats: [],
    currentView: 'season' // 'season' or 'gameweek'
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

// View Toggle Management
function toggleView(viewType) {
    window.AppState.currentView = viewType;
    
    // Update toggle buttons
    document.querySelectorAll('#view-toggle-section .view-toggle-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`#view-toggle-section [onclick="toggleView('${viewType}')"]`).classList.add('active');
    
    // Reload table with new view
    if (window.AppState.isDataLoaded) {
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
    
    // Load saved view preference
    const savedView = localStorage.getItem('tableView') || 'season';
    window.AppState.currentView = savedView;
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

async function loadLiveTable() {
    console.log(`Loading live table in ${window.AppState.currentView} view...`);
    const tableContainer = document.getElementById('live-table-container');
    
    if (!tableContainer) {
        console.log('Live table container not found');
        return;
    }
    
    if (!window.AppState.isDataLoaded) {
        // Hide toggle section when no league is configured
        const toggleSection = document.getElementById('view-toggle-section');
        if (toggleSection) {
            toggleSection.style.display = 'none';
        }
        
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
        let data;
        
        if (window.AppState.currentView === 'gameweek') {
            // Fetch gameweek-specific data
            const response = await fetch(`/api/gameweek_table/${window.AppState.currentGameweek}`);
            data = await response.json();
        } else {
            // Fetch overall season data
            const response = await fetch('/api/live_table');
            data = await response.json();
        }
        
        console.log('Live table response:', data);
        
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
    const currentView = window.AppState.currentView;
    const viewTitle = currentView === 'season' ? 'Season Table' : `GW${window.AppState.currentGameweek} Table`;
    const pointsLabel = currentView === 'season' ? 'Total' : `GW${window.AppState.currentGameweek}`;
    
    // Show the toggle controls when we have active season data
    const toggleSection = document.getElementById('view-toggle-section');
    if (toggleSection) {
        toggleSection.style.display = 'block';
    }
    
    let html = `
        <div class="live-table">
            <div class="live-table-header">
                <h3><i class="fas fa-trophy"></i> ${data.league_name}</h3>
                <p>${viewTitle} | ${data.total_teams} teams</p>
            </div>
            
            <!-- Mobile Card Layout (visible on mobile) -->
            <div class="mobile-table">
    `;
    
    // Process data based on view
    let tableData;
    if (currentView === 'gameweek') {
        // For gameweek view, sort by gameweek points
        tableData = [...data.table].sort((a, b) => {
            const aPoints = a.gameweek_points - (a.gameweek_transfer_cost || 0);
            const bPoints = b.gameweek_points - (b.gameweek_transfer_cost || 0);
            return bPoints - aPoints;
        });
        // Update ranks for gameweek view
        tableData.forEach((team, index) => {
            team.gameweek_rank = index + 1;
        });
    } else {
        // For season view, use existing total points ranking
        tableData = data.table;
    }
    
    tableData.forEach((team, index) => {
        const isTopThree = index < 3;
        const cardClass = isTopThree ? 'top-three' : '';
        
        let positionIcon = '';
        if (index === 0) positionIcon = '👑';
        else if (index === 1) positionIcon = '🥈';
        else if (index === 2) positionIcon = '🥉';
        
        const displayRank = currentView === 'gameweek' ? (team.gameweek_rank || index + 1) : team.rank;
        const displayPoints = currentView === 'gameweek' ? team.gameweek_points : team.total_points;
        
        html += `
            <div class="mobile-team-card ${cardClass}">
                <div class="mobile-team-header">
                    <div class="position-badge">${positionIcon} ${displayRank}</div>
                    <div class="team-details">
                        <div class="team-name">${team.team_name}</div>
                        <div class="manager-name">${team.manager_name}</div>
                    </div>
                    <div class="points-summary">
                        <div class="total-points">${displayPoints}</div>

                    </div>
                </div>
            </div>
        `;
    });
    
    html += `
            </div>
            
            <!-- Desktop Table Layout (visible on desktop) -->
            <div class="desktop-table">
                <div class="table-wrapper">
                    <table class="live-table-grid">
                        <thead>
                            <tr>
                                <th>Pos</th>
                                <th>Team Name</th>
                                <th>Manager</th>
                                <th>${pointsLabel}</th>
                            </tr>
                        </thead>
                        <tbody>
    `;
    
    tableData.forEach((team, index) => {
        const isTopThree = index < 3;
        const rowClass = isTopThree ? 'top-three' : '';
        
        let positionIcon = '';
        if (index === 0) positionIcon = '👑';
        else if (index === 1) positionIcon = '🥈';
        else if (index === 2) positionIcon = '🥉';
        
        const displayRank = currentView === 'gameweek' ? (team.gameweek_rank || index + 1) : team.rank;
        const primaryPoints = currentView === 'gameweek' ? team.gameweek_points : team.total_points;
        
        html += `
            <tr class="${rowClass}">
                <td class="position">${positionIcon} ${displayRank}</td>
                <td class="team-name">${team.team_name}</td>
                <td class="manager-name">${team.manager_name}</td>
                <td class="total-points">${primaryPoints}</td>
            </tr>
        `;
    });
    
    html += `
                        </tbody>
                    </table>
                </div>
            </div>
            
            <!-- Export Buttons Container -->
            <div class="export-buttons-container">
                <button class="export-button season-export" onclick="exportTableAsImage('${data.league_name}', 'Season Table', false, 'season')">
                    <i class="fas fa-download"></i> Export Season Table
                </button>
                <button class="export-button gameweek-export" onclick="exportTableAsImage('${data.league_name}', 'GW${window.AppState.currentGameweek} Table', false, 'gameweek')">
                    <i class="fas fa-download"></i> Export Gameweek Table
                </button>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
    
    // Save view preference
    localStorage.setItem('tableView', currentView);
}

function displayPreSeasonTeams(data, container) {
    console.log('Displaying pre-season teams:', data.teams);
    
    // Hide the toggle controls during pre-season
    const toggleSection = document.getElementById('view-toggle-section');
    if (toggleSection) {
        toggleSection.style.display = 'none';
    }
    
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
            <button class="export-button" onclick="exportTableAsImage('${data.league_name}', 'Pre-Season', true, 'preseason')">
                <i class="fas fa-download"></i> Export as Image
            </button>
            <div class="pre-season-note">
                <p><i class="fas fa-info-circle"></i> Season hasn't started yet. The live table will appear once gameweek 1 begins.</p>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}


// Export table as image function (updated to handle both views)
async function exportTableAsImage(leagueName, viewTitle, isPreSeason, exportType = 'current') {
    const buttons = document.querySelectorAll('.export-button');
    const activeButton = exportType === 'season' ? 
        document.querySelector('.season-export') : 
        exportType === 'gameweek' ? 
        document.querySelector('.gameweek-export') : 
        document.querySelector('.export-button');
    
    // Disable all export buttons
    buttons.forEach(btn => {
        btn.disabled = true;
        if (btn === activeButton) {
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
        }
    });
    
    try {
        // Get appropriate data based on export type
        let response;
        let dataForExport;
        
        if (isPreSeason) {
            // Pre-season: use current data
            response = await fetch('/api/live_table');
            dataForExport = await response.json();
        } else if (exportType === 'season') {
            // Season table: always get overall season data
            response = await fetch('/api/live_table');
            dataForExport = await response.json();
        } else if (exportType === 'gameweek') {
            // Gameweek table: get gameweek-specific data
            response = await fetch(`/api/gameweek_table/${window.AppState.currentGameweek}`);
            dataForExport = await response.json();
        } else {
            // Default: use current view
            if (window.AppState.currentView === 'gameweek') {
                response = await fetch(`/api/gameweek_table/${window.AppState.currentGameweek}`);
            } else {
                response = await fetch('/api/live_table');
            }
            dataForExport = await response.json();
        }
        
        if (dataForExport.error) {
            throw new Error(dataForExport.error);
        }
        
        // Create canvas
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        // Set canvas size and styling
        const padding = 40;
        const headerHeight = 120;
        const topMargin = 30;
        const lineHeight = 60;
        const borderRadius = 15;
        
        // Helper function to draw rounded rectangle
        function drawRoundedRect(ctx, x, y, width, height, radius, fillColor, strokeColor = null) {
            ctx.beginPath();
            ctx.moveTo(x + radius, y);
            ctx.lineTo(x + width - radius, y);
            ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
            ctx.lineTo(x + width, y + height - radius);
            ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
            ctx.lineTo(x + radius, y + height);
            ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
            ctx.lineTo(x, y + radius);
            ctx.quadraticCurveTo(x, y, x + radius, y);
            ctx.closePath();
            
            if (fillColor) {
                ctx.fillStyle = fillColor;
                ctx.fill();
            }
            
            if (strokeColor) {
                ctx.strokeStyle = strokeColor;
                ctx.stroke();
            }
        }
        
        if (isPreSeason) {
            // Pre-season layout (unchanged)
            const teams = dataForExport.teams || [];
            canvas.width = 800;
            canvas.height = headerHeight + topMargin + (lineHeight * teams.length) + padding;
            
            // Background
            ctx.fillStyle = '#2d3748';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            // Header
            ctx.fillStyle = '#38003c';
            ctx.fillRect(0, 0, canvas.width, headerHeight);
            
            // League name
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 32px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(leagueName, canvas.width / 2, 45);
            
            // Subtitle
            ctx.font = '20px Arial';
            ctx.fillText(`${viewTitle} - ${teams.length} teams ready`, canvas.width / 2, 80);
            
            // Draw the entire table as one rounded rectangle
            const tableY = headerHeight + topMargin;
            const tableHeight = lineHeight * teams.length;
            const tableWidth = canvas.width - (padding * 2);
            
            drawRoundedRect(ctx, padding, tableY, tableWidth, tableHeight, borderRadius, '#4a5568', '#718096');
            
            // Draw teams
            teams.forEach((team, index) => {
                const y = tableY + (index * lineHeight);
                
                if (index % 2 === 1) {
                    ctx.fillStyle = 'rgba(45, 55, 72, 0.5)';
                    ctx.fillRect(padding + 2, y + 1, tableWidth - 4, lineHeight - 2);
                }
                
                ctx.fillStyle = '#ffffff';
                ctx.font = 'bold 22px Arial';
                ctx.textAlign = 'left';
                ctx.fillText(team.team_name, padding + 20, y + 25);
                
                ctx.fillStyle = '#cbd5e0';
                ctx.font = '18px Arial';
                ctx.fillText(team.manager_name, padding + 20, y + 50);
            });
            
        } else {
            // Active season layout
            let teams = dataForExport.table || [];
            
            // Sort teams based on export type
            if (exportType === 'gameweek') {
                teams = [...teams].sort((a, b) => {
                    const aPoints = a.gameweek_points - (a.gameweek_transfer_cost || 0);
                    const bPoints = b.gameweek_points - (b.gameweek_transfer_cost || 0);
                    return bPoints - aPoints;
                });
            }
            // For season export, teams are already sorted by total points
            
            canvas.width = 800;
            canvas.height = headerHeight + topMargin + (lineHeight * (teams.length + 1)) + padding;
            
            // Background
            ctx.fillStyle = '#2d3748';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            // Header
            ctx.fillStyle = '#38003c';
            ctx.fillRect(0, 0, canvas.width, headerHeight);
            
            // League name
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 32px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(leagueName, canvas.width / 2, 45);
            
            // Subtitle
            ctx.font = '20px Arial';
            const subtitleText = exportType === 'season' ? 
                `Season Table | ${teams.length} teams` : 
                `GW${window.AppState.currentGameweek} Table | ${teams.length} teams`;
            ctx.fillText(subtitleText, canvas.width / 2, 80);
            
            const tableY = headerHeight + topMargin;
            const tableHeight = lineHeight * (teams.length + 1);
            const tableWidth = canvas.width - (padding * 2);
            
            drawRoundedRect(ctx, padding, tableY, tableWidth, tableHeight, borderRadius, '#4a5568', '#718096');
            
            // Table header
            ctx.fillStyle = '#38003c';
            ctx.fillRect(padding + 2, tableY + 2, tableWidth - 4, lineHeight - 2);
            
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 18px Arial';
            ctx.textAlign = 'left';
            
            // Header labels
            const primaryLabel = exportType === 'gameweek' ? `GW${window.AppState.currentGameweek}` : 'Total';
            
            ctx.fillText('Pos', padding + 20, tableY + 35);
            ctx.fillText('Team', padding + 80, tableY + 25);
            ctx.fillText('Manager', padding + 80, tableY + 50);
            
            // Points column, right-aligned
            ctx.textAlign = 'center';
            ctx.fillText(primaryLabel, canvas.width - padding - 60, tableY + 35);
            
            // Table rows
            teams.forEach((team, index) => {
                const y = tableY + lineHeight + (index * lineHeight);
                const isTopThree = index < 3;
                
                if (index % 2 === 1) {
                    ctx.fillStyle = 'rgba(45, 55, 72, 0.5)';
                    ctx.fillRect(padding + 2, y + 1, tableWidth - 4, lineHeight - 2);
                }
                
                if (isTopThree) {
                    ctx.fillStyle = 'rgba(34, 84, 61, 0.7)';
                    ctx.fillRect(padding + 2, y + 1, tableWidth - 4, lineHeight - 2);
                }
                
                // Position
                ctx.fillStyle = isTopThree ? '#9ae6b4' : '#ffffff';
                ctx.font = 'bold 20px Arial';
                ctx.textAlign = 'left';
                let positionText = (index + 1).toString();
                if (index === 0) positionText = '👑 ' + positionText;
                else if (index === 1) positionText = '🥈 ' + positionText;
                else if (index === 2) positionText = '🥉 ' + positionText;
                
                ctx.fillText(positionText, padding + 20, y + 37);
                
                // Team name
                ctx.fillText(team.team_name, padding + 80, y + 25);
                
                // Manager name
                ctx.fillStyle = isTopThree ? '#9ae6b4' : '#cbd5e0';
                ctx.font = '16px Arial';
                ctx.fillText(team.manager_name, padding + 80, y + 50);
                
                // Points
                ctx.fillStyle = isTopThree ? '#9ae6b4' : '#ffffff';
                ctx.font = 'bold 20px Arial';
                ctx.textAlign = 'center';
                
                const primaryPoints = exportType === 'gameweek' ? team.gameweek_points : team.total_points;
                ctx.fillText(primaryPoints.toString(), canvas.width - padding - 60, y + 37);
            });
        }
        
        // Convert canvas to blob and download
        canvas.toBlob((blob) => {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            const filename = exportType === 'gameweek' ? 
                `${leagueName.replace(/[^a-zA-Z0-9]/g, '_')}_GW${window.AppState.currentGameweek}_Table.png` :
                exportType === 'season' ?
                `${leagueName.replace(/[^a-zA-Z0-9]/g, '_')}_Season_Table.png` :
                `${leagueName.replace(/[^a-zA-Z0-9]/g, '_')}_${viewTitle.replace(/[^a-zA-Z0-9]/g, '_')}.png`;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }, 'image/png');
        
    } catch (error) {
        console.error('Export error:', error);
        alert('Failed to export image: ' + error.message);
    } finally {
        // Reset all buttons
        buttons.forEach(btn => {
            btn.disabled = false;
        });
        
        const seasonBtn = document.querySelector('.season-export');
        const gameweekBtn = document.querySelector('.gameweek-export');
        const singleBtn = document.querySelector('.export-button:not(.season-export):not(.gameweek-export)');
        
        if (seasonBtn) seasonBtn.innerHTML = '<i class="fas fa-download"></i> Export Season Table';
        if (gameweekBtn) gameweekBtn.innerHTML = '<i class="fas fa-download"></i> Export Gameweek Table';
        if (singleBtn) singleBtn.innerHTML = '<i class="fas fa-download"></i> Export as Image';
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