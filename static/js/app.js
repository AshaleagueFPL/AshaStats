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
        
        // Check if we should switch to a specific tab (from search page navigation)
        const storedTab = sessionStorage.getItem('activeTab');
        if (storedTab && ['stats', 'settings'].includes(storedTab)) {
            switchTab(storedTab);
            sessionStorage.removeItem('activeTab'); // Clean up
        }
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
    
    // Clear any stored active tab
    sessionStorage.removeItem('activeTab');
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
        if (index === 0) positionIcon = '🏆';
        else if (index === 1) positionIcon = '🥈';
        else if (index === 2) positionIcon = '🥉';
        
        const displayRank = currentView === 'gameweek' ? (team.gameweek_rank || index + 1) : team.rank;
        const displayPoints = currentView === 'gameweek' ? team.gameweek_points : team.total_points;
        
        html += `
            <div class="mobile-team-card ${cardClass}">
                <div class="mobile-team-header">
                    <div class="position-badge">${positionIcon} ${displayRank}</div>
                    <div class="team-details">
                        <div class="team-name clickable-team" onclick="openTeamSquad(${team.team_id}, '${team.team_name.replace(/'/g, "\\'")}', ${currentView === 'gameweek' ? window.AppState.currentGameweek : 'null'})">${team.team_name}</div>
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
        if (index === 0) positionIcon = '🏆';
        else if (index === 1) positionIcon = '🥈';
        else if (index === 2) positionIcon = '🥉';
        
        const displayRank = currentView === 'gameweek' ? (team.gameweek_rank || index + 1) : team.rank;
        const primaryPoints = currentView === 'gameweek' ? team.gameweek_points : team.total_points;
        
        html += `
            <tr class="${rowClass}">
                <td class="position">${positionIcon} ${displayRank}</td>
                <td class="team-name clickable-team" onclick="openTeamSquad(${team.team_id}, '${team.team_name.replace(/'/g, "\\'")}', ${currentView === 'gameweek' ? window.AppState.currentGameweek : 'null'})">${team.team_name}</td>
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
            const teamId = team.team_id || 0;
            
            html += `
                <div class="team-card">
                    <div class="team-info">
                        <div class="team-name clickable-team" onclick="openTeamSquad(${teamId}, '${teamName.replace(/'/g, "\\'")}', ${window.AppState.currentGameweek})">${teamName}</div>
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
        
        // Set canvas size for Instagram landscape format
        canvas.width = 1080;
        canvas.height = 566;
        
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
        
        // Define column positions for 4-column layout
        const padding = 30;
        const posCol = padding + 20;          // Position column
        const teamCol = posCol + 80;          // Team name column  
        const managerCol = teamCol + 300;     // Manager name column
        const pointsCol = managerCol + 300;   // Points column
        
        if (isPreSeason) {
            // Pre-season layout
            const teams = dataForExport.teams || [];
            
            // Set compact styling for landscape format
            const headerHeight = 80;
            const topMargin = 15;
            const availableHeight = canvas.height - headerHeight - topMargin - padding;
            const lineHeight = Math.min(35, Math.max(25, availableHeight / teams.length));
            const borderRadius = 15;
            
            // Background
            ctx.fillStyle = '#2d3748';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            // Header
            ctx.fillStyle = '#38003c';
            ctx.fillRect(0, 0, canvas.width, headerHeight);
            
            // League name
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 28px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(leagueName, canvas.width / 2, 35);
            
            // Subtitle
            ctx.font = '18px Arial';
            ctx.fillText(`${viewTitle} - ${teams.length} teams ready`, canvas.width / 2, 60);
            
            // Draw the entire table as one rounded rectangle
            const tableY = headerHeight + topMargin;
            const tableHeight = 40 + (teams.length * lineHeight); // Header height + all team rows
            const tableWidth = canvas.width - (padding * 2);
            
            drawRoundedRect(ctx, padding, tableY, tableWidth, tableHeight, borderRadius, '#4a5568', '#718096');
            
            // Table header for pre-season
            ctx.fillStyle = '#38003c';
            ctx.fillRect(padding + 2, tableY + 2, tableWidth - 4, 35);
            
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 16px Arial';
            ctx.textAlign = 'left';
            ctx.fillText('Pos', posCol, tableY + 22);
            ctx.fillText('Team', teamCol, tableY + 22);
            ctx.fillText('Manager', managerCol, tableY + 22);
            ctx.fillText('Status', pointsCol, tableY + 22);
            
            // Draw teams
            teams.forEach((team, index) => {
                const y = tableY + 35 + (index * lineHeight);
                const textY = y + (lineHeight / 2) + 5; // Center text vertically in the row
                
                if (index % 2 === 1) {
                    ctx.fillStyle = 'rgba(45, 55, 72, 0.5)';
                    ctx.fillRect(padding + 2, y, tableWidth - 4, lineHeight);
                }
                
                ctx.fillStyle = '#ffffff';
                ctx.font = 'bold 16px Arial';
                ctx.textAlign = 'left';
                
                // Position
                ctx.fillText((index + 1).toString(), posCol, textY);
                
                // Team name
                ctx.fillText(team.team_name, teamCol, textY);
                
                // Manager name
                ctx.fillStyle = '#cbd5e0';
                ctx.font = '16px Arial';
                ctx.fillText(team.manager_name, managerCol, textY);
                
                // Status
                ctx.fillStyle = '#9ae6b4';
                ctx.font = '14px Arial';
                ctx.fillText('Ready', pointsCol, textY);
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
            
            // Set compact styling for landscape format
            const headerHeight = 80;
            const topMargin = 15;
            const availableHeight = canvas.height - headerHeight - topMargin - padding;
            const lineHeight = Math.min(35, Math.max(25, (availableHeight - 35) / teams.length)); // Reserve space for header row
            const borderRadius = 15;
            
            // Background
            ctx.fillStyle = '#2d3748';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            // Header
            ctx.fillStyle = '#38003c';
            ctx.fillRect(0, 0, canvas.width, headerHeight);
            
            // League name
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 28px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(leagueName, canvas.width / 2, 35);
            
            // Subtitle
            ctx.font = '18px Arial';
            const subtitleText = exportType === 'season' ? 
                `Season Table | ${teams.length} teams` : 
                `GW${window.AppState.currentGameweek} Table | ${teams.length} teams`;
            ctx.fillText(subtitleText, canvas.width / 2, 60);
            
            const tableY = headerHeight + topMargin;
            const tableHeight = 40 + (teams.length * lineHeight); // Header height + all team rows
            const tableWidth = canvas.width - (padding * 2);
            
            drawRoundedRect(ctx, padding, tableY, tableWidth, tableHeight, borderRadius, '#4a5568', '#718096');
            
            // Table header
            ctx.fillStyle = '#38003c';
            ctx.fillRect(padding + 2, tableY + 2, tableWidth - 4, 35);
            
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 16px Arial';
            ctx.textAlign = 'left';
            
            // Header labels
            const primaryLabel = exportType === 'gameweek' ? 
                `GW${window.AppState.currentGameweek}` : 'Total';
            
            ctx.fillText('Pos', posCol, tableY + 22);
            ctx.fillText('Team', teamCol, tableY + 22);
            ctx.fillText('Manager', managerCol, tableY + 22);
            ctx.fillText(primaryLabel, pointsCol, tableY + 22);
            
            // Table rows
            teams.forEach((team, index) => {
                const y = tableY + 35 + (index * lineHeight);
                const textY = y + (lineHeight / 2) + 5; // Center text vertically in the row
                const isTopThree = index < 3;
                
                if (index % 2 === 1) {
                    ctx.fillStyle = 'rgba(45, 55, 72, 0.5)';
                    ctx.fillRect(padding + 2, y, tableWidth - 4, lineHeight);
                }
                
                if (isTopThree) {
                    ctx.fillStyle = 'rgba(34, 84, 61, 0.7)';
                    ctx.fillRect(padding + 2, y, tableWidth - 4, lineHeight);
                }
                
                // Position
                ctx.fillStyle = isTopThree ? '#9ae6b4' : '#ffffff';
                ctx.font = 'bold 16px Arial';
                ctx.textAlign = 'left';
                let positionText = (index + 1).toString();
                if (index === 0) positionText = '🏆 ' + positionText;
                else if (index === 1) positionText = '🥈 ' + positionText;
                else if (index === 2) positionText = '🥉 ' + positionText;
                
                ctx.fillText(positionText, posCol, textY);
                
                // Team name
                ctx.fillText(team.team_name, teamCol, textY);
                
                // Manager name
                ctx.fillStyle = isTopThree ? '#9ae6b4' : '#cbd5e0';
                ctx.font = '16px Arial';
                ctx.fillText(team.manager_name, managerCol, textY);
                
                // Points
                ctx.fillStyle = isTopThree ? '#9ae6b4' : '#ffffff';
                ctx.font = 'bold 16px Arial';
                
                const primaryPoints = exportType === 'gameweek' ? team.gameweek_points : team.total_points;
                ctx.fillText(primaryPoints.toString(), pointsCol, textY);
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

function openTeamSquad(teamId, teamName, gameweek) {
    console.log(`Opening squad for team ${teamId} (${teamName}) - GW${gameweek}`);
    
    // Create modal if it doesn't exist
    let modal = document.getElementById('team-squad-modal');
    if (!modal) {
        modal = createTeamSquadModal();
        document.body.appendChild(modal);
    }
    
    // Show loading state
    const modalContent = modal.querySelector('.team-squad-content');
    modalContent.innerHTML = `
        <div class="squad-header">
            <h3>${teamName}</h3>
            <button class="close-modal-btn" onclick="closeTeamSquad()">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="loading-container">
            <div class="loading-spinner"></div>
            <p>Loading squad...</p>
        </div>
    `;
    
    // Show modal
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden'; // Prevent background scrolling
    
    // Load squad data
    loadTeamSquadData(teamId, gameweek || window.AppState.currentGameweek);
}

function createTeamSquadModal() {
    const modal = document.createElement('div');
    modal.id = 'team-squad-modal';
    modal.className = 'team-squad-modal';
    modal.innerHTML = `
        <div class="team-squad-overlay" onclick="closeTeamSquad()"></div>
        <div class="team-squad-content">
            <!-- Content will be loaded here -->
        </div>
    `;
    return modal;
}

async function loadTeamSquadData(teamId, gameweek) {
    const modal = document.getElementById('team-squad-modal');
    const modalContent = modal.querySelector('.team-squad-content');
    
    try {
        const response = await fetch(`/api/team_squad/${teamId}/${gameweek}`);
        const data = await response.json();
        
        if (data.error) {
            modalContent.innerHTML = `
                <div class="squad-header">
                    <h3>Error</h3>
                    <button class="close-modal-btn" onclick="closeTeamSquad()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="error-message">
                    <i class="fas fa-exclamation-triangle"></i>
                    ${data.error}
                </div>
            `;
            return;
        }
        
        // Render squad data
        modalContent.innerHTML = renderTeamSquad(data);
        
        // Apply saved formation view preference
        setTimeout(() => {
            loadFormationViewPreference();
        }, 100);
        
    } catch (error) {
        console.error('Failed to load squad data:', error);
        modalContent.innerHTML = `
            <div class="squad-header">
                <h3>Error</h3>
                <button class="close-modal-btn" onclick="closeTeamSquad()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="error-message">
                <i class="fas fa-exclamation-triangle"></i>
                Failed to load squad data
            </div>
        `;
    }
}
function renderBenchPlayer(player, gameweek) {
    const initials = player.web_name.substring(0, 2).toUpperCase();
    
    // Create detailed stats breakdown for bench players too
    let statsBreakdown = '';
    const stats = [];
    if (player.minutes > 0) stats.push(`${player.minutes}min`);
    if (player.goals_scored > 0) stats.push(`${player.goals_scored}G`);
    if (player.assists > 0) stats.push(`${player.assists}A`);
    if (player.clean_sheets > 0) stats.push(`${player.clean_sheets}CS`);
    if (player.yellow_cards > 0) stats.push(`${player.yellow_cards}YC`);
    if (player.red_cards > 0) stats.push(`${player.red_cards}RC`);
    if (player.saves > 0) stats.push(`${player.saves}S`);
    if (player.bonus > 0) stats.push(`${player.bonus}B`);
    
    if (stats.length > 0) {
        statsBreakdown = `<div class="player-stats">${stats.join(', ')}</div>`;
    }
    
    return `
        <div class="player-card bench-player">
            <div class="bench-indicator">
                <i class="fas fa-chair"></i>
                <span class="bench-position">${player.squad_position}</span>
            </div>
            <div class="player-photo">
                ${player.photo ? 
                    `<img src="${player.photo}" alt="${player.full_name}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                    <div class="player-initials" style="display: none;">${initials}</div>` 
                    : 
                    `<div class="player-initials">${initials}</div>`
                }
            </div>
            <div class="player-info">
                <div class="player-name">${player.web_name}</div>
                <div class="player-team">${player.team_name}</div>
                <div class="player-position">${player.position}</div>
                <div class="player-price">£${player.now_cost}m</div>
                <div class="player-points bench-points">
                    <strong>${player.gameweek_points} pts</strong>
                    <small>(Bench)</small>
                </div>
                ${statsBreakdown}
            </div>
        </div>
    `;
}

function renderTeamSquad(data) {
    const chipBadge = data.active_chip ? `<span class="chip-badge">${data.active_chip.toUpperCase()} CHIP</span>` : '';
    
    // Organize starting XI by position
    const positions = {
        1: { name: 'Goalkeeper', players: [], icon: 'fas fa-hand-paper' },
        2: { name: 'Defenders', players: [], icon: 'fas fa-shield-alt' },
        3: { name: 'Midfielders', players: [], icon: 'fas fa-running' },
        4: { name: 'Forwards', players: [], icon: 'fas fa-bullseye' }
    };
    
    // Group starting XI by position
    data.starting_xi.forEach(player => {
        const positionId = player.position_id;
        if (positions[positionId]) {
            positions[positionId].players.push(player);
        }
    });
    
    // Calculate formation display
    const formationCounts = Object.values(positions)
        .filter(pos => pos.players.length > 0)
        .map(pos => pos.players.length);
    
    // Remove goalkeeper count for formation display (first position)
    const formationDisplay = formationCounts.slice(1).join('-');
    
    return `
        <div class="squad-header">
            <div class="squad-header-info">
                <h3>${data.team.name}</h3>
                <p class="manager-name">${data.team.manager}</p>
                <div class="squad-stats">
                    <span class="gw-points">GW${data.gameweek}: ${data.gameweek_points} pts</span>
                    ${data.transfers_cost > 0 ? `<span class="transfer-cost">(-${data.transfers_cost} cost)</span>` : ''}
                    <span class="formation-display">${formationDisplay}</span>
                    ${chipBadge}
                </div>
            </div>
            <button class="close-modal-btn" onclick="closeTeamSquad()">
                <i class="fas fa-times"></i>
            </button>
        </div>
        
        <div class="squad-content">
            <!-- Formation View Toggle -->
            <div class="formation-toggle-container">
                <div class="formation-toggle-buttons">
                    <button class="formation-toggle-btn active" onclick="toggleFormationView('list', ${data.team.id})">
                        <i class="fas fa-list"></i> Position List
                    </button>
                    <button class="formation-toggle-btn" onclick="toggleFormationView('formation', ${data.team.id})">
                        <i class="fas fa-futbol"></i> Formation View
                    </button>
                </div>
            </div>
            
            <div class="starting-xi-section">
                <h4><i class="fas fa-users"></i> Starting XI</h4>
                
                <!-- Position List View (Default) -->
                <div id="position-list-view" class="formation-view active">
                    ${Object.entries(positions).map(([positionId, positionData]) => {
                        if (positionData.players.length === 0) return '';
                        
                        return `
                            <div class="position-section">
                                <h5 class="position-title">
                                    <i class="${positionData.icon}"></i>
                                    ${positionData.name} (${positionData.players.length})
                                </h5>
                                <div class="position-players-grid">
                                    ${positionData.players.map(player => renderPlayer(player, data.gameweek)).join('')}
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
                
                <!-- Formation View -->
                <div id="formation-grid-view" class="formation-view">
                    ${renderFormationView(positions, data.gameweek, data.bench)}
                </div>
            </div>
            
            <!-- Bench Section (Only shown in Position List View) -->
            <div id="bench-list-section" class="bench-section">
                <h4><i class="fas fa-chair"></i> Bench (${data.bench.length})</h4>
                <div class="bench-grid">
                    ${data.bench.map(player => renderBenchPlayer(player, data.gameweek)).join('')}
                </div>
            </div>
            
            <div class="squad-summary">
                <div class="summary-stat">
                    <span class="stat-label">Team Value:</span>
                    <span class="stat-value">£${data.team_value}m</span>
                </div>
                <div class="summary-stat">
                    <span class="stat-label">In Bank:</span>
                    <span class="stat-value">£${data.bank}m</span>
                </div>
                <div class="summary-stat">
                    <span class="stat-label">Overall Rank:</span>
                    <span class="stat-value">#${data.team.rank}</span>
                </div>
            </div>
        </div>
    `;
}

function renderFormationView(positions, gameweek, benchPlayers) {
    const goalkeeper = positions[1].players[0]; // Should only be 1 GK
    const defenders = positions[2].players;
    const midfielders = positions[3].players;
    const forwards = positions[4].players;
    
    return `
        <div class="formation-pitch">
            <!-- Goalkeeper Row (First/Top) -->
            ${goalkeeper ? `
                <div class="formation-row goalkeeper-row">
                    <div class="formation-line-players">
                        ${renderFormationPlayer(goalkeeper, gameweek)}
                    </div>
                </div>
            ` : ''}
            
            <!-- Defenders Row -->
            ${defenders.length > 0 ? `
                <div class="formation-row defenders-row">
                    <div class="formation-line-players">
                        ${defenders.map(player => renderFormationPlayer(player, gameweek)).join('')}
                    </div>
                </div>
            ` : ''}
            
            <!-- Midfielders Row -->
            ${midfielders.length > 0 ? `
                <div class="formation-row midfielders-row">
                    <div class="formation-line-players">
                        ${midfielders.map(player => renderFormationPlayer(player, gameweek)).join('')}
                    </div>
                </div>
            ` : ''}
            
            <!-- Forwards Row (Last/Bottom) -->
            ${forwards.length > 0 ? `
                <div class="formation-row forwards-row">
                    <div class="formation-line-players">
                        ${forwards.map(player => renderFormationPlayer(player, gameweek)).join('')}
                    </div>
                </div>
            ` : ''}
        </div>
        
        <!-- Bench in Formation View -->
        <div class="formation-bench">
            <h5 class="formation-bench-title">
                <i class="fas fa-chair"></i> Bench (${benchPlayers.length})
            </h5>
            <div class="formation-bench-row">
                ${benchPlayers.map(player => renderFormationBenchPlayer(player, gameweek)).join('')}
            </div>
        </div>
    `;
}

function renderFormationBenchPlayer(player, gameweek) {
    const initials = player.web_name.substring(0, 2).toUpperCase();
    
    return `
        <div class="formation-bench-player">
            <div class="bench-position-indicator">${player.squad_position}</div>
            <div class="formation-player-photo">
                ${player.photo ? 
                    `<img src="${player.photo}" alt="${player.full_name}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                    <div class="formation-player-initials" style="display: none;">${initials}</div>` 
                    : 
                    `<div class="formation-player-initials">${initials}</div>`
                }
            </div>
            <div class="formation-player-info">
                <div class="formation-player-name">${player.web_name}</div>
                <div class="formation-player-points">
                    <strong>${player.gameweek_points} pts</strong>
                    <small>(Bench)</small>
                </div>
            </div>
        </div>
    `;
}

function renderFormationPlayer(player, gameweek) {
    const initials = player.web_name.substring(0, 2).toUpperCase();
    let captainBadge = '';
    
    if (player.is_captain) {
        captainBadge = '<div class="captain-badge captain">C</div>';
    } else if (player.is_vice_captain) {
        captainBadge = '<div class="captain-badge vice-captain">V</div>';
    }
    
    const multiplierText = player.multiplier > 1 ? ` (×${player.multiplier})` : '';
    
    return `
        <div class="formation-player ${player.multiplier === 0 ? 'not-playing' : ''}">
            ${captainBadge}
            <div class="formation-player-photo">
                ${player.photo ? 
                    `<img src="${player.photo}" alt="${player.full_name}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                    <div class="formation-player-initials" style="display: none;">${initials}</div>` 
                    : 
                    `<div class="formation-player-initials">${initials}</div>`
                }
            </div>
            <div class="formation-player-info">
                <div class="formation-player-name">${player.web_name}</div>
                <div class="formation-player-points">
                    ${player.multiplier === 0 ? 
                        '<span class="not-playing-text">DNP</span>' : 
                        `<strong>${player.final_points}${multiplierText}</strong>`
                    }
                </div>
            </div>
        </div>
    `;
}

function toggleFormationView(viewType, teamId) {
    // Update toggle buttons
    document.querySelectorAll('.formation-toggle-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`[onclick="toggleFormationView('${viewType}', ${teamId})"]`).classList.add('active');
    
    // Update views
    document.querySelectorAll('.formation-view').forEach(view => view.classList.remove('active'));
    
    const benchListSection = document.getElementById('bench-list-section');
    
    if (viewType === 'formation') {
        document.getElementById('formation-grid-view').classList.add('active');
        // Hide the separate bench section since it's now part of formation view
        if (benchListSection) {
            benchListSection.style.display = 'none';
        }
    } else {
        document.getElementById('position-list-view').classList.add('active');
        // Show the separate bench section for list view
        if (benchListSection) {
            benchListSection.style.display = 'block';
        }
    }
    
    // Store preference
    localStorage.setItem('formationViewPreference', viewType);
}

// Load formation view preference on modal open
function loadFormationViewPreference() {
    const preference = localStorage.getItem('formationViewPreference') || 'list';
    
    // Find the team ID from the modal (you might need to store this when opening)
    const modal = document.getElementById('team-squad-modal');
    if (modal && modal.style.display === 'block') {
        // Get team ID from the first toggle button
        const toggleBtn = modal.querySelector('.formation-toggle-btn');
        if (toggleBtn) {
            const onclickAttr = toggleBtn.getAttribute('onclick');
            const teamIdMatch = onclickAttr.match(/toggleFormationView\('[^']+',\s*(\d+)\)/);
            if (teamIdMatch) {
                toggleFormationView(preference, parseInt(teamIdMatch[1]));
            }
        }
    }
}

function renderPlayer(player, gameweek) {
    const initials = player.web_name.substring(0, 2).toUpperCase();
    let captainBadge = '';
    
    if (player.is_captain) {
        captainBadge = '<div class="captain-badge captain">C</div>';
    } else if (player.is_vice_captain) {
        captainBadge = '<div class="captain-badge vice-captain">V</div>';
    }
    
    const multiplierText = player.multiplier > 1 ? ` (×${player.multiplier})` : '';
    
    // Create detailed stats breakdown
    let statsBreakdown = '';
    if (player.multiplier > 0) {
        const stats = [];
        if (player.minutes > 0) stats.push(`${player.minutes}min`);
        if (player.goals_scored > 0) stats.push(`${player.goals_scored}G`);
        if (player.assists > 0) stats.push(`${player.assists}A`);
        if (player.clean_sheets > 0) stats.push(`${player.clean_sheets}CS`);
        if (player.yellow_cards > 0) stats.push(`${player.yellow_cards}YC`);
        if (player.red_cards > 0) stats.push(`${player.red_cards}RC`);
        if (player.saves > 0) stats.push(`${player.saves}S`);
        if (player.bonus > 0) stats.push(`${player.bonus}B`);
        
        if (stats.length > 0) {
            statsBreakdown = `<div class="player-stats">${stats.join(', ')}</div>`;
        }
    }
    
    return `
        <div class="player-card ${player.multiplier === 0 ? 'not-playing' : ''}">
            ${captainBadge}
            <div class="player-photo">
                ${player.photo ? 
                    `<img src="${player.photo}" alt="${player.full_name}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                    <div class="player-initials" style="display: none;">${initials}</div>` 
                    : 
                    `<div class="player-initials">${initials}</div>`
                }
            </div>
            <div class="player-info">
                <div class="player-name">${player.web_name}</div>
                <div class="player-team">${player.team_name}</div>
                <div class="player-position">${player.position}</div>
                <div class="player-price">£${player.now_cost}m</div>
                ${player.multiplier === 0 ? 
                    '<div class="not-playing-text">Not Playing</div>' : 
                    `<div class="player-points">
                        <strong>${player.final_points} pts${multiplierText}</strong>
                        ${player.gameweek_points !== player.final_points ? `<br><small>(${player.gameweek_points} base points)</small>` : ''}
                    </div>`
                }
                ${statsBreakdown}
            </div>
        </div>
    `;
}

function closeTeamSquad() {
    const modal = document.getElementById('team-squad-modal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = ''; // Restore scrolling
    }
}

// Close modal when clicking outside or pressing Escape
document.addEventListener('click', function(event) {
    const modal = document.getElementById('team-squad-modal');
    if (modal && modal.style.display === 'block') {
        if (event.target.classList.contains('team-squad-overlay')) {
            closeTeamSquad();
        }
    }
});

document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const modal = document.getElementById('team-squad-modal');
        if (modal && modal.style.display === 'block') {
            closeTeamSquad();
        }
    }
});
