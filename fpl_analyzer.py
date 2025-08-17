import requests
import json
from datetime import datetime

class FPLAnalyzer:
    """Fantasy Premier League Statistics Analyzer"""
    
    def __init__(self, league_id=None):
        self.league_id = league_id
        self.gdata = None
        self.teams = None
        self.current_gw = 1
        self.base_url = "https://fantasy.premierleague.com/api/"
    
    def fpl_api_get(self, endpoint):
        """Make API request to FPL"""
        url = f'{self.base_url}{endpoint}'
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"API Error: {e}")
        return None
    
    def initialize_data(self):
        """Load basic FPL data"""
        self.gdata = self.fpl_api_get("bootstrap-static/")
        if not self.gdata:
            return False
            
        # Find current gameweek
        current_found = False
        for i, event in enumerate(self.gdata['events']):
            if event.get('is_current', False):
                self.current_gw = i + 1
                current_found = True
                break
            elif event.get('is_next', False):
                self.current_gw = max(1, i)
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
            # FIX: Better handling of team data
            standings = league_data.get('standings', {}).get('results', [])
            
            if standings:
                # Use active standings if available
                self.teams = standings
                print(f"Loaded {len(self.teams)} active teams")
            else:
                # Fall back to new entries (pre-season)
                new_entries = league_data.get('new_entries', {})
                if isinstance(new_entries, dict):
                    self.teams = new_entries.get('results', [])
                else:
                    self.teams = new_entries if isinstance(new_entries, list) else []
                print(f"Loaded {len(self.teams)} pending teams (pre-season)")
            
            # Debug: Print first team structure to see available fields
            if self.teams:
                print("Sample team data structure:")
                print(f"Available fields: {list(self.teams[0].keys())}")
                
            return True
        return False    
    
    def get_team_gw_info(self, team_id, gameweek):
        """Get team gameweek info"""
        return self.fpl_api_get(f"entry/{team_id}/event/{gameweek}/picks/")

    def get_team_transfers_info(self, team_id):
        """Get team transfers info"""
        return self.fpl_api_get(f"entry/{team_id}/transfers/")

    def get_team_history_info(self, team_id):
        """Get team history info"""
        return self.fpl_api_get(f"entry/{team_id}/history/")

    def id_to_name(self, player_id):
        """Convert player ID to name"""
        if not self.gdata or not self.gdata.get('elements'):
            return f"Player {player_id}"
        
        for player in self.gdata['elements']:
            if player['id'] == player_id:
                return player['web_name']
        
        return f"Player {player_id}"

    def id_to_team_name(self, team_id):
        """Convert team ID to team name"""
        if not self.gdata or not self.gdata.get('teams'):
            return f"Team {team_id}"
        
        for team in self.gdata['teams']:
            if team['id'] == team_id:
                return team['name']
        
        return f"Team {team_id}"

    def get_player_struct(self, player_id):
        """Get player structure by ID"""
        if not self.gdata or not self.gdata.get('elements'):
            return None
        
        for player in self.gdata['elements']:
            if player['id'] == player_id:
                return player
        
        return None
    
    def get_stat_data(self, stat_type, gameweek):
        """Get specific stat data for a gameweek"""
        if not self.teams or not self.gdata:
            return {"error": "Data not loaded"}
            
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
        if not self.teams or not self.gdata:
            return {"error": "Data not loaded"}
        
        EO = {}
        captains = {}
        
        for team in self.teams:
            team_id = team['entry']
            team_name = team['entry_name']
            data = self.get_team_gw_info(team_id, gameweek)
            
            if not data or not data.get("picks"):
                continue
                
            for pick in data["picks"]:
                if not pick.get("multiplier", 0):
                    continue
                    
                player_id = pick["element"]
                multiplier = pick["multiplier"]
                
                if player_id in EO:
                    EO[player_id]["ownership"] += multiplier
                    EO[player_id]["teams"].append(team_name)
                else:
                    EO[player_id] = {
                        "teams": [team_name],
                        "ownership": multiplier,
                        "player": self.id_to_name(player_id)
                    }
                
                # Track captains (multiplier > 1)
                if multiplier > 1:
                    if player_id in captains:
                        captains[player_id].append(team_name)
                    else:
                        captains[player_id] = [team_name]
        
        # Convert to list and calculate percentages
        players = []
        total_teams = len(self.teams)
        
        for player_id, data in EO.items():
            ownership_percentage = round(100 * (data["ownership"] / total_teams), 2)
            captain_teams = captains.get(player_id, [])
            
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
            "data": players,
            "total_teams": total_teams
        }
    
    def get_captaincy_stats(self, gameweek):
        """Get captaincy statistics"""
        if not self.teams or not self.gdata:
            return {"error": "Data not loaded"}
        
        caps = {}
        for team in self.teams:
            team_id = team["entry"]
            data = self.get_team_gw_info(team_id, gameweek)
            if not data:
                continue
                
            for player in data["picks"]:
                if player["is_captain"]:
                    player_id = player["element"]
                    player_name = self.id_to_name(player_id)
                    if player_id in caps:
                        caps[player_id]["teams"].append(team["entry_name"])
                        caps[player_id]["count"] += 1
                    else:
                        caps[player_id] = {
                            "player": player_name,
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
        """Get transfer statistics for gameweek"""
        if not self.teams or not self.gdata:
            return {"error": "Data not loaded"}
        
        transfers_in = {}
        transfers_out = {}
        
        for team in self.teams:
            team_id = team["entry"]
            team_name = team["entry_name"]
            transfers = self.get_team_transfers_info(team_id)
            
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
            team_id = team['entry']
            team_name = team['entry_name']
            gw_info = self.get_team_gw_info(team_id, gameweek)
            
            if not gw_info or not gw_info.get('entry_history'):
                continue
                
            gw_points = gw_info['entry_history']['points']
            transfer_cost = gw_info['entry_history'].get('event_transfers_cost', 0)
            net_points = gw_points - transfer_cost
            
            rankings.append({
                "manager": team_name,
                "points": gw_points,
                "transfer_cost": transfer_cost,
                "net_points": net_points,
                "rank": 0
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
            team_id = team['entry']
            team_name = team['entry_name']
            gw_info = self.get_team_gw_info(team_id, gameweek)
            
            if not gw_info or not gw_info.get('picks'):
                continue
                
            for pick in gw_info["picks"]:
                if not pick.get("multiplier", 0):
                    continue
                    
                player_id = pick["element"]
                if player_id in player_ownership:
                    player_ownership[player_id]["teams"].append(team_name)
                else:
                    player_ownership[player_id] = {
                        "player": self.id_to_name(player_id),
                        "teams": [team_name]
                    }
        
        # Find unique players (owned by only one team)
        unique_by_manager = {}
        
        for player_id, data in player_ownership.items():
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
            team_id = team["entry"]
            gw_info = self.get_team_gw_info(team_id, gameweek)
            
            if not gw_info or not gw_info.get('picks'):
                continue
                
            for pick in gw_info["picks"]:
                if not pick.get("multiplier", 0):
                    continue
                    
                player_id = pick["element"]
                player_info = self.get_player_struct(player_id)
                
                if player_info:
                    pl_team_name = self.id_to_team_name(player_info["team"])
                    if pl_team_name in team_count:
                        team_count[pl_team_name] += 1
                        total_players += 1
        
        # Convert to list with percentages
        representation_data = []
        for team_name, count in team_count.items():
            if count > 0:
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