from flask import Flask, render_template, jsonify, request, send_from_directory
from fpl_analyzer import FPLAnalyzer
import requests

app = Flask(__name__)

# Global analyzer instance
analyzer = FPLAnalyzer()

@app.route('/')
def index():
    """Main app page"""
    return render_template('index.html')

@app.route('/api/initialize')
def initialize():
    """Initialize FPL data"""
    if analyzer.initialize_data():
        return jsonify({
            "success": True,
            "current_gameweek": analyzer.current_gw,
            "total_gameweeks": len(analyzer.gdata['events'])
        })
    return jsonify({"success": False, "error": "Failed to load FPL data"})

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

@app.route('/api/set_league', methods=['POST'])
def set_league():
    """Set league ID"""
    data = request.get_json()
    league_id = data.get('league_id')
    
    if not league_id:
        return jsonify({"success": False, "error": "League ID required"})
    
    try:
        # Test the league by making direct API call
        url = f"https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/"
        response = requests.get(url)
        
        if response.status_code != 200:
            return jsonify({"success": False, "error": f"League {league_id} not found"})
        
        league_data = response.json()
        league_info = league_data.get('league', {})
        
        # Count teams
        active_teams = len(league_data.get('standings', {}).get('results', []))
        new_entries = league_data.get('new_entries', {})
        pending_teams = len(new_entries.get('results', [])) if isinstance(new_entries, dict) else 0
        total_teams = active_teams + pending_teams
        
        if total_teams == 0:
            return jsonify({"success": False, "error": "League has no teams"})
        
        # Set in analyzer for stats compatibility
        analyzer.league_id = league_id
        analyzer.load_league_data()
        
        return jsonify({
            "success": True,
            "team_count": total_teams,
            "league_name": league_info.get('name', 'Unknown League')
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to load league: {str(e)}"})

@app.route('/api/live_table')
def get_live_table():
    """Get live league table with proper manager names (Season view)"""
    if not analyzer.league_id:
        return jsonify({"error": "No league configured"})
    
    try:
        # Make direct API call
        url = f"https://fantasy.premierleague.com/api/leagues-classic/{analyzer.league_id}/standings/"
        response = requests.get(url)
        
        if response.status_code != 200:
            return jsonify({"error": "Failed to fetch league data"})
        
        league_data = response.json()
        league_info = league_data.get('league', {})
        standings = league_data.get('standings', {}).get('results', [])
        
        # Get new entries (pre-season teams)
        new_entries = league_data.get('new_entries', {})
        if isinstance(new_entries, dict):
            pending_teams_raw = new_entries.get('results', [])
        else:
            pending_teams_raw = []
        
        # Pre-season: no active standings but have new entries
        if len(standings) == 0 and len(pending_teams_raw) > 0:
            teams_list = []
            
            for team_raw in pending_teams_raw:
                # Extract names carefully - FIX HERE
                first_name = team_raw.get('player_first_name', '').strip()
                last_name = team_raw.get('player_last_name', '').strip()
                
                # Better name combination logic
                if first_name and last_name:
                    manager_name = f"{first_name} {last_name}"
                elif first_name:
                    manager_name = first_name
                elif last_name:
                    manager_name = last_name
                else:
                    # Fallback: try alternative field names
                    manager_name = team_raw.get('entry_name', team_raw.get('team_name', 'Unknown Manager'))
                
                team_name = team_raw.get('entry_name', 'Unknown Team').strip()
                
                teams_list.append({
                    'team_name': team_name,
                    'manager_name': manager_name,
                    'team_id': team_raw.get('entry', 0),
                    'total_points': 0
                })
            
            return jsonify({
                "success": True,
                "is_pre_season": True,
                "teams": teams_list,
                "league_name": league_info.get('name', 'FPL League'),
                "total_teams": len(teams_list)
            })
        
        # Active season: format standings
        elif len(standings) > 0:
            formatted_table = []
            
            for i, team in enumerate(standings):
                # FIX: Better manager name extraction
                first_name = team.get('player_first_name', '').strip()
                last_name = team.get('player_last_name', '').strip()
                
                # Try multiple field combinations
                if first_name and last_name:
                    manager_name = f"{first_name} {last_name}"
                elif first_name:
                    manager_name = first_name
                elif last_name:
                    manager_name = last_name
                else:
                    # Try alternative field names that might exist
                    manager_name = (team.get('player_name') or 
                                  team.get('manager_name') or 
                                  team.get('entry_name', 'Unknown Manager'))
                
                formatted_table.append({
                    'rank': i + 1,
                    'team_name': team.get('entry_name', 'Unknown Team').strip(),
                    'manager_name': manager_name,
                    'total_points': team.get('total', 0),
                    'gameweek_points': 0,  # Would need additional API call
                    'team_id': team.get('entry', 0)
                })
            
            return jsonify({
                "success": True,
                "is_pre_season": False,
                "table": formatted_table,
                "current_gameweek": analyzer.current_gw,
                "league_name": league_info.get('name', 'FPL League'),
                "total_teams": len(formatted_table)
            })
        
        else:
            return jsonify({"error": "No teams found in league"})
        
    except Exception as e:
        return jsonify({"error": f"Failed to load live table: {str(e)}"})

@app.route('/api/gameweek_table/<int:gameweek>')
def get_gameweek_table(gameweek):
    """Get gameweek-specific table ranked by gameweek points only"""
    if not analyzer.league_id:
        return jsonify({"error": "No league configured"})
    
    try:
        # First get the league standings for team info
        url = f"https://fantasy.premierleague.com/api/leagues-classic/{analyzer.league_id}/standings/"
        response = requests.get(url)
        
        if response.status_code != 200:
            return jsonify({"error": "Failed to fetch league data"})
        
        league_data = response.json()
        league_info = league_data.get('league', {})
        standings = league_data.get('standings', {}).get('results', [])
        
        if len(standings) == 0:
            return jsonify({"error": "No active teams found in league"})
        
        # Get gameweek performance for each team
        gameweek_table = []
        
        for team in standings:
            team_id = team.get('entry', 0)
            
            # Get team's gameweek data
            gw_url = f"https://fantasy.premierleague.com/api/entry/{team_id}/event/{gameweek}/picks/"
            gw_response = requests.get(gw_url)
            
            gameweek_points = 0
            transfer_cost = 0
            
            if gw_response.status_code == 200:
                gw_data = gw_response.json()
                entry_history = gw_data.get('entry_history', {})
                gameweek_points = entry_history.get('points', 0)
                transfer_cost = entry_history.get('event_transfers_cost', 0)
            
            # FIX: Better manager name extraction
            first_name = team.get('player_first_name', '').strip()
            last_name = team.get('player_last_name', '').strip()
            
            # Try multiple approaches to get manager name
            if first_name and last_name:
                manager_name = f"{first_name} {last_name}"
            elif first_name:
                manager_name = first_name
            elif last_name:
                manager_name = last_name
            else:
                # Try alternative field names
                manager_name = (team.get('player_name') or 
                              team.get('manager_name') or 
                              f"Manager {team_id}")
            
            gameweek_table.append({
                'team_name': team.get('entry_name', 'Unknown Team').strip(),
                'manager_name': manager_name,
                'total_points': team.get('total', 0),
                'gameweek_points': gameweek_points,
                'gameweek_transfer_cost': transfer_cost,
                'gameweek_net_points': gameweek_points - transfer_cost,
                'team_id': team_id,
                'rank': team.get('rank', 0)  # Overall season rank
            })
        
        # Sort by gameweek net points (gameweek points minus transfer cost)
        gameweek_table.sort(key=lambda x: x['gameweek_net_points'], reverse=True)
        
        # Assign gameweek ranks
        for i, team in enumerate(gameweek_table):
            team['gameweek_rank'] = i + 1
        
        return jsonify({
            "success": True,
            "is_pre_season": False,
            "table": gameweek_table,
            "current_gameweek": gameweek,
            "league_name": league_info.get('name', 'FPL League'),
            "total_teams": len(gameweek_table)
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to load gameweek table: {str(e)}"})

@app.route('/mock')
def mock_home():
    """Mock home page for testing with sample data"""
    return render_template('mock_index.html')

@app.route('/api/mock_table/<table_type>')
def get_mock_table(table_type):
    """Get mock table data for testing - supports 'preseason' or 'active'"""
    
    if table_type == 'preseason':
        # Mock pre-season data with 15 teams
        mock_teams = [
            {"team_name": "Salah's Army", "manager_name": "John Smith", "team_id": 1001},
            {"team_name": "Kane's Champions", "manager_name": "Emma Wilson", "team_id": 1002},
            {"team_name": "Haaland Heroes", "manager_name": "Michael Brown", "team_id": 1003},
            {"team_name": "Son's Squad", "manager_name": "Sarah Davis", "team_id": 1004},
            {"team_name": "De Bruyne's Dream", "manager_name": "David Miller", "team_id": 1005},
            {"team_name": "Sterling Silver", "manager_name": "Lisa Garcia", "team_id": 1006},
            {"team_name": "Mane's Magic", "manager_name": "James Rodriguez", "team_id": 1007},
            {"team_name": "Bruno's Brilliance", "manager_name": "Anna Martinez", "team_id": 1008},
            {"team_name": "Lukaku's Lions", "manager_name": "Chris Anderson", "team_id": 1009},
            {"team_name": "Mount's Marvels", "manager_name": "Rachel Thompson", "team_id": 1010},
            {"team_name": "Vardy's Veterans", "manager_name": "Tom White", "team_id": 1011},
            {"team_name": "Grealish's Gang", "manager_name": "Sophie Johnson", "team_id": 1012},
            {"team_name": "Rashford's Rockets", "manager_name": "Alex Turner", "team_id": 1013},
            {"team_name": "Foden's Force", "manager_name": "Maria Lopez", "team_id": 1014},
            {"team_name": "Greenwood's Glory", "manager_name": "Ryan Mitchell", "team_id": 1015}
        ]
        
        return jsonify({
            "success": True,
            "is_pre_season": True,
            "teams": mock_teams,
            "league_name": "Mock Test League",
            "total_teams": len(mock_teams)
        })
    
    elif table_type == 'active':
        # Mock active season data with 15 teams
        mock_table = [
            {"rank": 1, "team_name": "Salah's Army", "manager_name": "John Smith", "total_points": 1247, "gameweek_points": 68, "team_id": 1001},
            {"rank": 2, "team_name": "Kane's Champions", "manager_name": "Emma Wilson", "total_points": 1198, "gameweek_points": 45, "team_id": 1002},
            {"rank": 3, "team_name": "Haaland Heroes", "manager_name": "Michael Brown", "total_points": 1156, "gameweek_points": 52, "team_id": 1003},
            {"rank": 4, "team_name": "Son's Squad", "manager_name": "Sarah Davis", "total_points": 1134, "gameweek_points": 38, "team_id": 1004},
            {"rank": 5, "team_name": "De Bruyne's Dream", "manager_name": "David Miller", "total_points": 1098, "gameweek_points": 41, "team_id": 1005},
            {"rank": 6, "team_name": "Sterling Silver", "manager_name": "Lisa Garcia", "total_points": 1087, "gameweek_points": 55, "team_id": 1006},
            {"rank": 7, "team_name": "Mane's Magic", "manager_name": "James Rodriguez", "total_points": 1065, "gameweek_points": 29, "team_id": 1007},
            {"rank": 8, "team_name": "Bruno's Brilliance", "manager_name": "Anna Martinez", "total_points": 1043, "gameweek_points": 47, "team_id": 1008},
            {"rank": 9, "team_name": "Lukaku's Lions", "manager_name": "Chris Anderson", "total_points": 1021, "gameweek_points": 33, "team_id": 1009},
            {"rank": 10, "team_name": "Mount's Marvels", "manager_name": "Rachel Thompson", "total_points": 998, "gameweek_points": 42, "team_id": 1010},
            {"rank": 11, "team_name": "Vardy's Veterans", "manager_name": "Tom White", "total_points": 976, "gameweek_points": 36, "team_id": 1011},
            {"rank": 12, "team_name": "Grealish's Gang", "manager_name": "Sophie Johnson", "total_points": 954, "gameweek_points": 28, "team_id": 1012},
            {"rank": 13, "team_name": "Rashford's Rockets", "manager_name": "Alex Turner", "total_points": 932, "gameweek_points": 44, "team_id": 1013},
            {"rank": 14, "team_name": "Foden's Force", "manager_name": "Maria Lopez", "total_points": 918, "gameweek_points": 31, "team_id": 1014},
            {"rank": 15, "team_name": "Greenwood's Glory", "manager_name": "Ryan Mitchell", "total_points": 897, "gameweek_points": 39, "team_id": 1015}
        ]
        
        return jsonify({
            "success": True,
            "is_pre_season": False,
            "table": mock_table,
            "current_gameweek": 15,
            "league_name": "Mock Test League",
            "total_teams": len(mock_table)  
        })
    
    else:
        return jsonify({"error": "Invalid table type. Use 'preseason' or 'active'"})

@app.route('/api/stats/<stat_type>/<int:gameweek>')
def get_stats(stat_type, gameweek):
    """Get specific stat data"""
    return jsonify(analyzer.get_stat_data(stat_type, gameweek))

@app.route('/api/available_stats')
def available_stats():
    """Get list of available stat types"""
    return jsonify({
        "stats": [
            {"id": "ownership", "name": "Effective Ownership", "icon": "fas fa-users"},
            {"id": "captaincy", "name": "Captaincy Analysis", "icon": "fas fa-bolt"},
            {"id": "transfers", "name": "Transfer Summary", "icon": "fas fa-exchange-alt"},
            {"id": "rankings", "name": "Manager Rankings", "icon": "fas fa-trophy"},
            {"id": "unique", "name": "Unique Players", "icon": "fas fa-star"},
            {"id": "representation", "name": "Team Representation", "icon": "fas fa-building"}
        ]
    })

@app.route('/search')
def search_page():
    """Search page"""
    return render_template('search.html')

@app.route('/api/search_players')
def search_players():
    """Search for players by name"""
    search_term = request.args.get('q', '').strip()
    limit = request.args.get('limit', 10, type=int)
    
    if not search_term:
        return jsonify({"error": "Search term required"})
    
    if not analyzer.gdata:
        return jsonify({"error": "FPL data not loaded"})
    
    results = analyzer.search_players(search_term, limit)
    return jsonify(results)

@app.route('/api/player_league_stats/<int:player_id>/<int:gameweek>')
def get_player_league_stats(player_id, gameweek):
    """Get player statistics within the league for a specific gameweek"""
    if not analyzer.league_id or not analyzer.teams:
        return jsonify({"error": "No league configured"})
    
    try:
        stats = analyzer.get_player_league_stats(player_id, gameweek)
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": f"Failed to get player stats: {str(e)}"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)