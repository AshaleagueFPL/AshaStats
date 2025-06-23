from flask import Flask, render_template, jsonify, request
import requests
import json
from datetime import datetime

app = Flask(__name__)

# FPL API Base Configuration
BASE_URL = "https://fantasy.premierleague.com/api/"
GENERAL_INFO = "bootstrap-static/"
FIXTURES = "fixtures/"

class FPLAnalyzer:
    def __init__(self, league_id=None):
        self.league_id = league_id
        self.gdata = None
        self.teams = None
        self.current_gw = 1
    
    def get_team_gw_info(self, teamID, gw):
        """Get team gameweek info"""
        gwEntry = f"entry/{teamID}/event/{gw}/picks/"
        return self.fpl_api_get(gwEntry)

    def get_team_transfers_info(self, teamID):
        """Get team transfers info"""
        transfersData = f"entry/{teamID}/transfers/"
        return self.fpl_api_get(transfersData)

    def get_team_history_info(self, teamID):
        """Get team history info"""
        gwEntry = f"entry/{teamID}/history/"
        return self.fpl_api_get(gwEntry)

    def id_to_name(self, pid):
        """Convert player ID to name"""
        if not self.gdata or not self.gdata.get('elements'):
            return f"Player {pid}"
        
        for player in self.gdata['elements']:
            if player['id'] == pid:
                return player['web_name']
        
        return f"Player {pid}"

    def id_to_team_name(self, team_id):
        """Convert team ID to team name"""
        if not self.gdata or not self.gdata.get('teams'):
            return f"Team {team_id}"
        
        for team in self.gdata['teams']:
            if team['id'] == team_id:
                return team['name']
        
        return f"Team {team_id}"

    def get_player_struct(self, pid):
        """Get player structure by ID"""
        if not self.gdata or not self.gdata.get('elements'):
            return None
        
        for player in self.gdata['elements']:
            if player['id'] == pid:
                return player
        
        return None

    def gw_points_by_player_id(self, pid, gw):
        """Get gameweek points for a player"""
        # This is a simplified version - you may want to implement the full logic from your script
        player_data = self.fpl_api_get(f"element-summary/{pid}/")
        if not player_data or not player_data.get('history'):
            return 0
        
        for game in player_data['history']:
            if game['round'] == gw:
                return game['total_points']
        
        return 0
    
    def get_team_gw_info(self, teamID, gw):
        """Get team gameweek info"""
        gwEntry = f"entry/{teamID}/event/{gw}/picks/"
        return self.fpl_api_get(gwEntry)

    def id_to_name(self, pid):
        """Convert player ID to name"""
        if not self.gdata or not self.gdata.get('elements'):
            return f"Player {pid}"
        
        # Find player in elements array
        for player in self.gdata['elements']:
            if player['id'] == pid:
                return player['web_name']
        
        return f"Player {pid}"

    def fpl_api_get(self, endpoint):
        """Make API request to FPL"""
        url = f'{BASE_URL}{endpoint}'
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None
    
    def initialize_data(self):
        """Load basic FPL data"""
        self.gdata = self.fpl_api_get(GENERAL_INFO)
        if not self.gdata:
            return False
            
        # Find current gameweek - fix the logic
        current_found = False
        for i, event in enumerate(self.gdata['events']):
            if event.get('is_current', False):
                self.current_gw = i + 1
                current_found = True
                break
            elif event.get('is_next', False):
                self.current_gw = max(1, i)  # Previous GW if next is found
                current_found = True
                break
        
        # If no current/next found, use the last finished event
        if not current_found:
            for i, event in enumerate(self.gdata['events']):
                if event.get('finished', False):
                    self.current_gw = i + 1
            
        # Ensure current_gw doesn't exceed available gameweeks
        max_gw = len(self.gdata['events'])
        self.current_gw = min(self.current_gw, max_gw)
            
        return True
    
    def load_league_data(self):
        """Load league specific data"""
        if not self.league_id:
            return False
            
        league_data = self.fpl_api_get(f"leagues-classic/{self.league_id}/standings/")
        if league_data:
            self.teams = league_data['standings']['results']
            return True
        return False
    
    def get_stat_data(self, stat_type, gameweek):
        """Get specific stat data for a gameweek"""
        if not self.teams or not self.gdata:
            return {"error": "Data not loaded"}
            
        # This will be expanded with actual stat calculations
        stat_functions = {
            "ownership": self.get_effective_ownership,
            "captaincy": self.get_captaincy_stats,
            "transfers": self.get_transfer_stats,
            "rankings": self.get_manager_rankings,
            "unique": self.get_unique_players,
            "representation": self.get_team_representation
        }
        
        if stat_type in stat_functions:
            return stat_functions[stat_type](gameweek)
        
        return {"error": "Unknown stat type"}
    
    def get_effective_ownership(self, gameweek):
        """Calculate effective ownership for gameweek"""
        # Placeholder - will implement actual calculation
        return {
            "title": "Effective Ownership",
            "gameweek": gameweek,
            "data": [
                {"player": "Salah", "ownership": 85.5, "teams": ["Team1", "Team2"]},
                {"player": "Haaland", "ownership": 72.3, "teams": ["Team3", "Team4"]}
            ]
        }
    
    def get_captaincy_stats(self, gameweek):
        """Get captaincy statistics"""
        if not self.teams or not self.gdata:
            return {"error": "Data not loaded"}
        
        caps = {}
        for team in self.teams:
            teamID = team["entry"]
            data = self.get_team_gw_info(teamID, gameweek)
            if not data:
                continue
                
            for player in data["picks"]:
                if player["is_captain"]:
                    playerID = player["element"]
                    playerName = self.id_to_name(playerID)
                    if playerID in caps:
                        caps[playerID]["teams"].append(team["entry_name"])
                        caps[playerID]["count"] += 1
                    else:
                        caps[playerID] = {
                            "player": playerName,
                            "teams": [team["entry_name"]],
                            "count": 1
                        }
                    break
        
        # Sort by count (most captained first)
        captaincy_data = sorted(caps.values(), key=lambda x: x["count"], reverse=True)
        
        return {
            "title": "Captaincy Choices",
            "gameweek": gameweek,
            "data": captaincy_data,
            "total_teams": len(self.teams)
        }
    
    def get_transfer_stats(self, gameweek):
        """Get transfer statistics"""
        return {
            "title": "Transfer Summary",
            "gameweek": gameweek,
            "transfers_in": [
                {"player": "Player A", "teams": ["Team1", "Team2"], "count": 2}
            ],
            "transfers_out": [
                {"player": "Player B", "teams": ["Team3"], "count": 1}
            ]
        }
    
    def get_effective_ownership(self, gameweek):
        """Calculate effective ownership for gameweek"""
        if not self.teams or not self.gdata:
            return {"error": "Data not loaded"}
        
        EO = {}
        captains = {}
        
        for team in self.teams:
            teamID = team['entry']
            team_name = team['entry_name']
            data = self.get_team_gw_info(teamID, gameweek)
            
            if not data or not data.get("picks"):
                continue
                
            for pick in data["picks"]:
                if not pick.get("multiplier", 0):
                    continue
                    
                playerID = pick["element"]
                multiplier = pick["multiplier"]
                
                if playerID in EO:
                    EO[playerID]["ownership"] += multiplier
                    EO[playerID]["teams"].append(team_name)
                else:
                    EO[playerID] = {
                        "teams": [team_name],
                        "ownership": multiplier,
                        "player": self.id_to_name(playerID)
                    }
                
                # Track captains (multiplier > 1)
                if multiplier > 1:
                    if playerID in captains:
                        captains[playerID].append(team_name)
                    else:
                        captains[playerID] = [team_name]
        
        # Convert to list and calculate percentages
        players = []
        total_teams = len(self.teams)
        
        for playerID, data in EO.items():
            ownership_percentage = round(100 * (data["ownership"] / total_teams), 2)
            captain_teams = captains.get(playerID, [])
            
            players.append({
                "player": data["player"],
                "ownership": ownership_percentage,
                "teams": data["teams"],
                "captains": captain_teams,
                "raw_ownership": data["ownership"]
            })
        
        # Sort by effective ownership
        players = sorted(players, key=lambda x: x["raw_ownership"], reverse=True)
        
        return {
            "title": "Effective Ownership",
            "gameweek": gameweek,
            "data": players[:20],  # Top 20 most owned
            "total_teams": total_teams
        }
    
    def get_transfer_stats(self, gameweek):
        """Get transfer statistics for gameweek"""
        if not self.teams or not self.gdata:
            return {"error": "Data not loaded"}
        
        transfers_in = {}
        transfers_out = {}
        
        for team in self.teams:
            teamID = team["entry"]
            team_name = team["entry_name"]
            transfers = self.get_team_transfers_info(teamID)
            
            if not transfers:
                continue
                
            for transfer in transfers:
                if transfer['event'] != gameweek:
                    continue
                    
                in_player = transfer['element_in']
                out_player = transfer['element_out']
                
                # Track transfers in
                in_name = self.id_to_name(in_player)
                if in_player in transfers_in:
                    transfers_in[in_player]["teams"].append(team_name)
                    transfers_in[in_player]["count"] += 1
                else:
                    transfers_in[in_player] = {
                        "player": in_name,
                        "teams": [team_name],
                        "count": 1
                    }
                
                # Track transfers out
                out_name = self.id_to_name(out_player)
                if out_player in transfers_out:
                    transfers_out[out_player]["teams"].append(team_name)
                    transfers_out[out_player]["count"] += 1
                else:
                    transfers_out[out_player] = {
                        "player": out_name,
                        "teams": [team_name],
                        "count": 1
                    }
        
        # Sort by count
        in_data = sorted(transfers_in.values(), key=lambda x: x["count"], reverse=True)
        out_data = sorted(transfers_out.values(), key=lambda x: x["count"], reverse=True)
        
        return {
            "title": "Transfer Summary",
            "gameweek": gameweek,
            "transfers_in": in_data,
            "transfers_out": out_data,
            "total_teams": len(self.teams)
        }
        
    def get_manager_rankings(self, gameweek):
        """Get manager performance rankings for gameweek"""
        if not self.teams or not self.gdata:
            return {"error": "Data not loaded"}
        
        rankings = []
        
        for team in self.teams:
            teamID = team['entry']
            team_name = team['entry_name']
            gwInfo = self.get_team_gw_info(teamID, gameweek)
            
            if not gwInfo or not gwInfo.get('entry_history'):
                continue
                
            gw_points = gwInfo['entry_history']['points']
            transfer_cost = gwInfo['entry_history'].get('event_transfers_cost', 0)
            net_points = gw_points - transfer_cost
            
            rankings.append({
                "manager": team_name,
                "points": gw_points,
                "transfer_cost": transfer_cost,
                "net_points": net_points,
                "rank": 0  # Will be set after sorting
            })
        
        # Sort by net points and assign ranks
        rankings = sorted(rankings, key=lambda x: x["net_points"], reverse=True)
        for i, manager in enumerate(rankings):
            manager["rank"] = i + 1
        
        return {
            "title": "Manager Rankings",
            "gameweek": gameweek,
            "data": rankings,
            "total_teams": len(self.teams)
        }
    
    def get_unique_players(self, gameweek):
        """Get unique player selections for gameweek"""
        if not self.teams or not self.gdata:
            return {"error": "Data not loaded"}
        
        player_ownership = {}
        
        # Count how many teams own each player
        for team in self.teams:
            teamID = team['entry']
            team_name = team['entry_name']
            gwInfo = self.get_team_gw_info(teamID, gameweek)
            
            if not gwInfo or not gwInfo.get('picks'):
                continue
                
            for pick in gwInfo["picks"]:
                if not pick.get("multiplier", 0):  # Only playing players
                    continue
                    
                playerID = pick["element"]
                if playerID in player_ownership:
                    player_ownership[playerID]["teams"].append(team_name)
                else:
                    player_ownership[playerID] = {
                        "player": self.id_to_name(playerID),
                        "teams": [team_name]
                    }
        
        # Find unique players (owned by only one team)
        unique_by_manager = {}
        
        for playerID, data in player_ownership.items():
            if len(data["teams"]) == 1:
                manager = data["teams"][0]
                if manager in unique_by_manager:
                    unique_by_manager[manager].append(data["player"])
                else:
                    unique_by_manager[manager] = [data["player"]]
        
        # Convert to list format
        unique_data = []
        for manager, players in unique_by_manager.items():
            unique_data.append({
                "manager": manager,
                "unique_players": players,
                "count": len(players)
            })
        
        # Sort by number of unique players
        unique_data = sorted(unique_data, key=lambda x: x["count"], reverse=True)
        
        return {
            "title": "Unique Players",
            "gameweek": gameweek,
            "data": unique_data,
            "total_teams": len(self.teams)
        }
    
    def get_team_representation(self, gameweek):
        """Get Premier League team representation for gameweek"""
        if not self.teams or not self.gdata:
            return {"error": "Data not loaded"}
        
        team_count = {}
        total_players = 0
        
        # Initialize all PL teams
        for pl_team in self.gdata["teams"]:
            team_count[pl_team["name"]] = 0
        
        # Count players from each PL team
        for team in self.teams:
            teamID = team["entry"]
            gwInfo = self.get_team_gw_info(teamID, gameweek)
            
            if not gwInfo or not gwInfo.get('picks'):
                continue
                
            for pick in gwInfo["picks"]:
                if not pick.get("multiplier", 0):  # Only playing players
                    continue
                    
                playerID = pick["element"]
                player_info = self.get_player_struct(playerID)
                
                if player_info:
                    pl_team_name = self.id_to_team_name(player_info["team"])
                    if pl_team_name in team_count:
                        team_count[pl_team_name] += 1
                        total_players += 1
        
        # Convert to list with percentages
        representation_data = []
        for team_name, count in team_count.items():
            if count > 0:  # Only show teams with players
                percentage = round((count * 100) / total_players, 2) if total_players > 0 else 0
                representation_data.append({
                    "team": team_name,
                    "count": count,
                    "percentage": percentage
                })
        
        # Sort by count
        representation_data = sorted(representation_data, key=lambda x: x["count"], reverse=True)
        
        return {
            "title": "Team Representation",
            "gameweek": gameweek,
            "data": representation_data,
            "total_players": total_players,
            "total_teams": len(self.teams)
        }
    
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

@app.route('/api/set_league', methods=['POST'])
def set_league():
    """Set league ID"""
    data = request.get_json()
    league_id = data.get('league_id')
    
    if not league_id:
        return jsonify({"success": False, "error": "League ID required"})
    
    analyzer.league_id = league_id
    if analyzer.load_league_data():
        return jsonify({
            "success": True,
            "team_count": len(analyzer.teams),
            "league_name": analyzer.teams[0].get('league_name', 'Unknown') if analyzer.teams else 'Unknown'
        })
    
    return jsonify({"success": False, "error": "Failed to load league data"})

@app.route('/api/stats/<stat_type>/<int:gameweek>')
def get_stats(stat_type, gameweek):
    """Get specific stat data"""
    return jsonify(analyzer.get_stat_data(stat_type, gameweek))

@app.route('/api/available_stats')
def available_stats():
    """Get list of available stat types"""
    return jsonify({
        "stats": [
            {"id": "ownership", "name": "Effective Ownership", "icon": "👥"},
            {"id": "captaincy", "name": "Captaincy Analysis", "icon": "⚡"},
            {"id": "transfers", "name": "Transfer Summary", "icon": "🔄"},
            {"id": "rankings", "name": "Manager Rankings", "icon": "🏆"},
            {"id": "unique", "name": "Unique Players", "icon": "⭐"},
            {"id": "representation", "name": "Team Representation", "icon": "🏟️"}
        ]
    })

@app.route('/manifest.json')
def manifest():
    """PWA manifest"""
    return jsonify({
        "name": "FPL League Analyzer",
        "short_name": "FPL Stats",
        "description": "Fantasy Premier League statistics for your mini-league",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#38003c",
        "theme_color": "#00ff85",
        "icons": [
            {
                "src": "/static/icon-192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/static/icon-512.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)