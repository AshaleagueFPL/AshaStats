// League Management
async function saveLeagueId() {
    const leagueInput = document.getElementById('league-id');
    if (!leagueInput) {
        showError('League input not found');
        return;
    }
    
    const leagueId = leagueInput.value.trim();
    if (!leagueId) {
        showError('Please enter a League ID');
        return;
    }
    
    await loadLeague(leagueId);
}

async function loadLeague(leagueId) {
    const statusDiv = document.getElementById('league-status');
    if (!statusDiv) {
        console.error('League status div not found');
        return;
    }
    
    statusDiv.innerHTML = '<div class="loading-spinner"></div> Loading league...';
    
    try {
        const response = await fetch('/api/set_league', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ league_id: leagueId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            localStorage.setItem('leagueId', leagueId);
            statusDiv.innerHTML = `<div class="success-message">✅ League loaded! ${data.team_count} teams found.</div>`;
            window.AppState.isDataLoaded = true;
            
            // Load stats for current gameweek if on stats tab
            const statsTab = document.getElementById('stats-tab');
            if (statsTab && statsTab.classList.contains('active')) {
                if (typeof loadStatsForGameweek === 'function') {
                    await loadStatsForGameweek(window.AppState.currentGameweek);
                }
            }
            
            if (typeof updateAppInfo === 'function') {
                updateAppInfo();
            }
        } else {
            statusDiv.innerHTML = `<div class="error-message">❌ Failed to load league: ${data.error}</div>`;
        }
    } catch (error) {
        statusDiv.innerHTML = `<div class="error-message">❌ Connection error</div>`;
        console.error('League loading error:', error);
    }
}