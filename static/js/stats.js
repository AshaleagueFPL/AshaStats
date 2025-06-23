// Gameweek Management
function changeGameweek(direction) {
    const newGw = window.AppState.currentGameweek + direction;
    const maxGw = window.AppState.maxGameweek || 38;
    
    if (newGw >= 1 && newGw <= maxGw) {
        window.AppState.currentGameweek = newGw;
        updateGameweekDisplay();
        
        // Only reload data for expanded cards
        if (window.AppState.isDataLoaded) {
            loadStatsForGameweek(window.AppState.currentGameweek);
        }
    }
}

function updateGameweekDisplay() {
    const currentGwEl = document.getElementById('current-gw');
    const prevBtn = document.getElementById('prev-gw');
    const nextBtn = document.getElementById('next-gw');
    
    if (currentGwEl) currentGwEl.textContent = `GW ${window.AppState.currentGameweek}`;
    if (prevBtn) prevBtn.disabled = window.AppState.currentGameweek <= 1;
    if (nextBtn) nextBtn.disabled = window.AppState.currentGameweek >= window.AppState.maxGameweek;
}

// Stats Management
async function loadAvailableStats() {
    try {
        console.log('Loading available stats...');
        const response = await fetch('/api/available_stats');
        const data = await response.json();
        console.log('Available stats response:', data);
        window.AppState.availableStats = data.stats;
        createStatsCards();
    } catch (error) {
        console.error('Failed to load available stats:', error);
        showError('Failed to load available stats');
    }
}

function createStatsCards() {
    const grid = document.getElementById('stats-grid');
    if (!grid) {
        console.log('Stats grid not found');
        return;
    }
    
    console.log('Creating stats cards...');
    grid.innerHTML = '';
    
    window.AppState.availableStats.forEach(stat => {
        const card = document.createElement('div');
        card.className = 'stat-card';
        card.setAttribute('data-stat-type', stat.id);
        card.setAttribute('data-loaded', 'false');
        
        card.innerHTML = `
            <div class="stat-header" onclick="toggleStatCard('${stat.id}')">
                <div class="stat-header-left">
                    <span class="stat-icon">${stat.icon}</span>
                    <span class="stat-title">${stat.name}</span>
                </div>
                <span class="expand-icon">▼</span>
            </div>
            <div class="stat-content" id="stat-${stat.id}">
                <div class="stat-placeholder">Click to expand and load ${stat.name.toLowerCase()} data</div>
            </div>
        `;
        
        grid.appendChild(card);
    });
    
    console.log('Stats cards created successfully');
}

async function loadStatsForGameweek(gameweek) {
    // Only load stats for expanded cards
    const expandedCards = document.querySelectorAll('.stat-card.expanded');
    expandedCards.forEach(card => {
        const statType = card.getAttribute('data-stat-type');
        if (statType) {
            loadStatData(statType, gameweek);
        }
    });
}

async function loadStatData(statType, gameweek = window.AppState.currentGameweek) {
    console.log(`Loading stat data for: ${statType}, GW: ${gameweek}`);
    
    if (!window.AppState.isDataLoaded) {
        console.log('Data not loaded, showing error');
        showError('Please configure a league first in Settings');
        return;
    }
    
    const card = document.querySelector(`[data-stat-type="${statType}"]`);
    const content = document.getElementById(`stat-${statType}`);
    
    if (!card || !content) {
        console.error('Card or content element not found');
        return;
    }
    
    // Mark as loading
    card.classList.add('loading');
    card.setAttribute('data-loaded', 'true');
    content.innerHTML = '<div class="loading-spinner"></div> Loading data...';
    
    try {
        const url = `/api/stats/${statType}/${gameweek}`;
        console.log(`Fetching: ${url}`);
        
        const response = await fetch(url);
        const data = await response.json();
        
        console.log('API Response:', data);
        
        if (data.error) {
            content.innerHTML = `<div class="error-message">❌ ${data.error}</div>`;
            card.setAttribute('data-loaded', 'false');
        } else {
            content.innerHTML = formatStatData(data, statType);
        }
    } catch (error) {
        console.error('Fetch error:', error);
        content.innerHTML = `<div class="error-message">❌ Failed to load ${statType} data. Please check your connection.</div>`;
        card.setAttribute('data-loaded', 'false');
    } finally {
        card.classList.remove('loading');
    }
}

function toggleStatCard(statType) {
    const card = document.querySelector(`[data-stat-type="${statType}"]`);
    if (!card) return;
    
    const isExpanded = card.classList.contains('expanded');
    
    if (isExpanded) {
        // Collapse the card
        card.classList.remove('expanded');
    } else {
        // Expand the card
        card.classList.add('expanded');
        
        // Load data if not already loaded
        const isLoaded = card.getAttribute('data-loaded') === 'true';
        if (!isLoaded && window.AppState.isDataLoaded) {
            loadStatData(statType);
        } else if (!window.AppState.isDataLoaded) {
            const content = document.getElementById(`stat-${statType}`);
            content.innerHTML = '<div class="error-message">⚙️ Please configure a league first in Settings</div>';
        }
    }
}

// Data Formatting Functions (keeping the same formatting functions from before)
function formatStatData(data, statType) {
    switch (statType) {
        case 'ownership':
            return formatOwnershipData(data);
        case 'captaincy':
            return formatCaptaincyData(data);
        case 'transfers':
            return formatTransferData(data);
        case 'rankings':
            return formatRankingsData(data);
        case 'unique':
            return formatUniqueData(data);
        case 'representation':
            return formatRepresentationData(data);
        default:
            return '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
    }
}

function formatOwnershipData(data) {
    if (!data.data || data.data.length === 0) {
        return '<p>No ownership data available</p>';
    }
    
    let html = `<div style="margin-bottom: 1rem; padding: 0.75rem; background: var(--pl-purple); color: white; border-radius: 8px; text-align: center;">
        <strong>GW${data.gameweek} Effective Ownership</strong><br>
        <small>Top ${data.data.length} most owned players</small>
    </div>`;
    
    data.data.forEach((player, index) => {
        const isHighOwnership = player.ownership > 50;
        const bgColor = isHighOwnership ? 'var(--pl-green)' : 'var(--bg-secondary)';
        const textColor = isHighOwnership ? 'var(--pl-purple)' : 'var(--text-primary)';
        
        html += `
            <div style="margin-bottom: 0.75rem; padding: 0.75rem; background: ${bgColor}; color: ${textColor}; border-radius: 8px; border: 1px solid var(--border);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <strong style="font-size: 1.1rem;">${player.player}</strong>
                    <span style="background: ${isHighOwnership ? 'rgba(56, 0, 60, 0.2)' : 'var(--pl-purple)'}; color: ${isHighOwnership ? 'var(--pl-purple)' : 'white'}; padding: 0.25rem 0.5rem; border-radius: 12px; font-size: 0.8rem; font-weight: bold;">
                        ${player.ownership}% EO
                    </span>
                </div>
                <div style="font-size: 0.9rem; opacity: 0.9;">
                    ${player.teams.length === data.total_teams ? 
                        '🔥 <strong>ALL TEAMS</strong>' : 
                        `Teams: ${player.teams.join(', ')}`
                    }
                    ${player.captains.length > 0 ? `<br>⚡ Captains: ${player.captains.join(', ')}` : ''}
                </div>
            </div>
        `;
    });
    
    return html;
}

function formatCaptaincyData(data) {
    if (!data.data || data.data.length === 0) {
        return '<p>No captaincy data available for this gameweek</p>';
    }
    
    let html = `<div style="margin-bottom: 1rem; padding: 0.75rem; background: var(--pl-purple); color: white; border-radius: 8px; text-align: center;">
        <strong>GW${data.gameweek} Captaincy Summary</strong><br>
        <small>${data.total_teams} teams in league</small>
    </div>`;
    
    data.data.forEach((captain, index) => {
        const percentage = ((captain.count / data.total_teams) * 100).toFixed(1);
        const isPopular = captain.count > data.total_teams / 2;
        const bgColor = isPopular ? 'var(--pl-green)' : 'var(--bg-secondary)';
        const textColor = isPopular ? 'var(--pl-purple)' : 'var(--text-primary)';
        
        html += `
            <div style="margin-bottom: 0.75rem; padding: 0.75rem; background: ${bgColor}; color: ${textColor}; border-radius: 8px; border: 1px solid var(--border);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <strong style="font-size: 1.1rem;">${captain.player}</strong>
                    <span style="background: ${isPopular ? 'rgba(56, 0, 60, 0.2)' : 'var(--pl-purple)'}; color: ${isPopular ? 'var(--pl-purple)' : 'white'}; padding: 0.25rem 0.5rem; border-radius: 12px; font-size: 0.8rem; font-weight: bold;">
                        ${captain.count}/${data.total_teams} (${percentage}%)
                    </span>
                </div>
                <div style="font-size: 0.9rem; opacity: 0.9;">
                    ${captain.count === data.total_teams ? 
                        '🔥 <strong>ALL TEAMS</strong>' : 
                        captain.teams.join(', ')
                    }
                </div>
            </div>
        `;
    });
    
    return html;
}

function formatTransferData(data) {
    let html = '<div>';
    
    if (data.transfers_in && data.transfers_in.length > 0) {
        html += '<h4 style="color: var(--pl-green); margin-bottom: 0.5rem;">⬆️ Transfers In</h4>';
        data.transfers_in.forEach(transfer => {
            html += `
                <div style="margin-bottom: 0.5rem; padding: 0.5rem; background: var(--bg-secondary); border-radius: 6px;">
                    <strong>${transfer.player}</strong> (${transfer.count})
                    <br><small>${transfer.teams.join(', ')}</small>
                </div>
            `;
        });
    }
    
    if (data.transfers_out && data.transfers_out.length > 0) {
        html += '<h4 style="color: #ff4757; margin: 1rem 0 0.5rem 0;">⬇️ Transfers Out</h4>';
        data.transfers_out.forEach(transfer => {
            html += `
                <div style="margin-bottom: 0.5rem; padding: 0.5rem; background: var(--bg-secondary); border-radius: 6px;">
                    <strong>${transfer.player}</strong> (${transfer.count})
                    <br><small>${transfer.teams.join(', ')}</small>
                </div>
            `;
        });
    }
    
    html += '</div>';
    return html || '<p>No transfer data available</p>';
}

function formatRankingsData(data) {
    if (!data.data || data.data.length === 0) {
        return '<p>No rankings data available</p>';
    }
    
    let html = `<div style="margin-bottom: 1rem; padding: 0.75rem; background: var(--pl-purple); color: white; border-radius: 8px; text-align: center;">
        <strong>GW${data.gameweek} Manager Rankings</strong><br>
        <small>${data.total_teams} teams</small>
    </div>`;
    
    data.data.forEach((manager, index) => {
        const medal = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `${index + 1}.`;
        const isTopThree = index < 3;
        const bgColor = isTopThree ? 'var(--pl-green)' : 'var(--bg-secondary)';
        const textColor = isTopThree ? 'var(--pl-purple)' : 'var(--text-primary)';
        
        html += `
            <div style="margin-bottom: 0.5rem; padding: 0.75rem; background: ${bgColor}; color: ${textColor}; border-radius: 8px; border: 1px solid var(--border);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span><strong>${medal} ${manager.manager}</strong></span>
                    <span style="font-weight: bold;">${manager.points} pts</span>
                </div>
                ${manager.transfer_cost > 0 ? `<div style="font-size: 0.9rem; opacity: 0.8;">Net: ${manager.net_points} (${manager.transfer_cost} hit)</div>` : ''}
            </div>
        `;
    });
    
    return html;
}

function formatUniqueData(data) {
    if (!data.data || data.data.length === 0) {
        return '<p>No unique players this gameweek</p>';
    }
    
    let html = `<div style="margin-bottom: 1rem; padding: 0.75rem; background: var(--pl-purple); color: white; border-radius: 8px; text-align: center;">
        <strong>GW${data.gameweek} Unique Players</strong><br>
        <small>Players owned by only one team</small>
    </div>`;
    
    data.data.forEach(manager => {
        html += `
            <div style="margin-bottom: 0.75rem; padding: 0.75rem; background: var(--bg-secondary); border-radius: 8px; border: 1px solid var(--border);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <strong style="color: var(--text-primary);">${manager.manager}</strong>
                    <span style="background: var(--pl-green); color: var(--pl-purple); padding: 0.25rem 0.5rem; border-radius: 12px; font-size: 0.8rem; font-weight: bold;">
                        ${manager.count} unique
                    </span>
                </div>
                <div style="font-size: 0.9rem; color: var(--text-secondary);">
                    ${manager.unique_players.join(', ')}
                </div>
            </div>
        `;
    });
    
    return html;
}

function formatRepresentationData(data) {
    if (!data.data || data.data.length === 0) {
        return '<p>No team representation data available</p>';
    }
    
    let html = `<div style="margin-bottom: 1rem; padding: 0.75rem; background: var(--pl-purple); color: white; border-radius: 8px; text-align: center;">
        <strong>GW${data.gameweek} Team Representation</strong><br>
        <small>${data.total_players} total players selected</small>
    </div>`;
    
    data.data.forEach(team => {
        const isPopular = team.percentage > 10;
        const bgColor = isPopular ? 'var(--pl-green)' : 'var(--bg-secondary)';
        const textColor = isPopular ? 'var(--pl-purple)' : 'var(--text-primary)';
        
        html += `
            <div style="margin-bottom: 0.5rem; padding: 0.75rem; background: ${bgColor}; color: ${textColor}; border-radius: 8px; border: 1px solid var(--border);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong>${team.team}</strong>
                    <span style="background: ${isPopular ? 'rgba(56, 0, 60, 0.2)' : 'var(--pl-purple)'}; color: ${isPopular ? 'var(--pl-purple)' : 'white'}; padding: 0.25rem 0.5rem; border-radius: 12px; font-size: 0.8rem; font-weight: bold;">
                        ${team.count} (${team.percentage}%)
                    </span>
                </div>
            </div>
        `;
    });
    
    return html;
}