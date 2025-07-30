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
    """Get live league table with proper manager names"""
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
                # Extract names carefully
                first_name = team_raw.get('player_first_name', '').strip()
                last_name = team_raw.get('player_last_name', '').strip()
                
                # Combine names
                if first_name and last_name:
                    manager_name = f"{first_name} {last_name}"
                elif first_name:
                    manager_name = first_name
                elif last_name:
                    manager_name = last_name
                else:
                    manager_name = "Unknown Manager"
                
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
                first_name = team.get('player_first_name', '').strip()
                last_name = team.get('player_last_name', '').strip()
                
                if first_name and last_name:
                    manager_name = f"{first_name} {last_name}"
                elif first_name:
                    manager_name = first_name
                elif last_name:
                    manager_name = last_name
                else:
                    manager_name = "Unknown Manager"
                
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)