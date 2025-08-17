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

    def search_players(self, search_term, limit=None):
        """
        Search for players by name (supports partial matching)
        
        Args:
            search_term (str): Name or partial name to search for
            limit (int, optional): Maximum number of results to return
            
        Returns:
            List[Dict]: List of matching players with all their attributes
        """
        if not self.gdata or not self.gdata.get('elements'):
            return {"error": "Player data not loaded"}
        
        if not search_term or not search_term.strip():
            return {"error": "Search term cannot be empty"}
        
        search_term = search_term.strip().lower()
        matching_players = []
        
        for player in self.gdata['elements']:
            # Search in multiple name fields
            web_name = player.get('web_name', '').lower()
            first_name = player.get('first_name', '').lower()
            second_name = player.get('second_name', '').lower()
            full_name = f"{first_name} {second_name}".lower()
            
            # Check if search term matches any name variation
            if (search_term in web_name or 
                search_term in first_name or 
                search_term in second_name or 
                search_term in full_name):
                
                # Add readable team and position names
                team_name = self.id_to_team_name(player['team'])
                position_name = self._get_position_name(player['element_type'])
                
                # Helper function to safely convert to float/int
                def safe_float(value, default=0.0):
                    try:
                        return float(value) if value is not None else default
                    except (ValueError, TypeError):
                        return default
                
                def safe_int(value, default=0):
                    try:
                        return int(value) if value is not None else default
                    except (ValueError, TypeError):
                        return default
                
                player_info = {
                    'id': player['id'],
                    'web_name': player['web_name'],
                    'first_name': player['first_name'],
                    'second_name': player['second_name'],
                    'full_name': f"{player['first_name']} {player['second_name']}",
                    'team_id': player['team'],
                    'team_name': team_name,
                    'position_id': player['element_type'],
                    'position_name': position_name,
                    'now_cost': safe_float(player['now_cost']) / 10,  # Convert to actual price
                    'total_points': safe_int(player['total_points']),
                    'points_per_game': round(safe_float(player.get('points_per_game', 0)), 1),
                    'selected_by_percent': safe_float(player.get('selected_by_percent', 0)),
                    'form': safe_float(player.get('form', 0)),
                    'dreamteam_count': safe_int(player.get('dreamteam_count', 0)),
                    'in_dreamteam': player.get('in_dreamteam', False),
                    'status': player.get('status', 'a'),  # a = available, d = doubtful, i = injured, etc.
                    'chance_of_playing_this_round': safe_int(player.get('chance_of_playing_this_round')),
                    'chance_of_playing_next_round': safe_int(player.get('chance_of_playing_next_round')),
                    'news': player.get('news', ''),
                    'news_added': player.get('news_added'),
                    'minutes': safe_int(player.get('minutes', 0)),
                    'goals_scored': safe_int(player.get('goals_scored', 0)),
                    'assists': safe_int(player.get('assists', 0)),
                    'clean_sheets': safe_int(player.get('clean_sheets', 0)),
                    'goals_conceded': safe_int(player.get('goals_conceded', 0)),
                    'own_goals': safe_int(player.get('own_goals', 0)),
                    'penalties_saved': safe_int(player.get('penalties_saved', 0)),
                    'penalties_missed': safe_int(player.get('penalties_missed', 0)),
                    'yellow_cards': safe_int(player.get('yellow_cards', 0)),
                    'red_cards': safe_int(player.get('red_cards', 0)),
                    'saves': safe_int(player.get('saves', 0)),
                    'bonus': safe_int(player.get('bonus', 0)),
                    'bps': safe_int(player.get('bps', 0)),  # Bonus Points System
                    'influence': safe_float(player.get('influence', 0)),
                    'creativity': safe_float(player.get('creativity', 0)),
                    'threat': safe_float(player.get('threat', 0)),
                    'ict_index': safe_float(player.get('ict_index', 0)),
                    'starts': safe_int(player.get('starts', 0)),
                    'expected_goals': safe_float(player.get('expected_goals', 0)),
                    'expected_assists': safe_float(player.get('expected_assists', 0)),
                    'expected_goal_involvements': safe_float(player.get('expected_goal_involvements', 0)),
                    'expected_goals_conceded': safe_float(player.get('expected_goals_conceded', 0)),
                    'value_form': safe_float(player.get('value_form', 0)),
                    'value_season': safe_float(player.get('value_season', 0)),
                    'cost_change_start': safe_int(player.get('cost_change_start', 0)),
                    'cost_change_event': safe_int(player.get('cost_change_event', 0)),
                    'cost_change_start_fall': safe_int(player.get('cost_change_start_fall', 0)),
                    'cost_change_event_fall': safe_int(player.get('cost_change_event_fall', 0)),
                    'transfers_in': safe_int(player.get('transfers_in', 0)),
                    'transfers_out': safe_int(player.get('transfers_out', 0)),
                    'transfers_in_event': safe_int(player.get('transfers_in_event', 0)),
                    'transfers_out_event': safe_int(player.get('transfers_out_event', 0)),
                    'ep_this': safe_float(player.get('ep_this', 0)),  # Expected points this gameweek
                    'ep_next': safe_float(player.get('ep_next', 0)),   # Expected points next gameweek
                    'special': player.get('special', False),
                    'squad_number': safe_int(player.get('squad_number')),
                    'photo': f"https://resources.premierleague.com/premierleague/photos/players/250x250/p{player.get('photo', '').replace('.jpg', '.png')}" if player.get('photo') else None
                }
                
                matching_players.append(player_info)
        
        # Sort by total points (highest first) for relevance
        matching_players.sort(key=lambda x: x['total_points'], reverse=True)
        
        # Apply limit if specified
        if limit and limit > 0:
            matching_players = matching_players[:limit]
        
        return {
            "search_term": search_term,
            "total_found": len(matching_players),
            "players": matching_players
        }        

    def _get_position_name(self, position_id):
        """Get position name from bootstrap data"""
        if not self.gdata or not self.gdata.get('element_types'):
            return f"Position {position_id}"
        
        for position in self.gdata['element_types']:
            if position['id'] == position_id:
                return position['singular_name']
        return f"Position {position_id}"
    
    def get_player_league_stats(self, player_id, gameweek):
        """
        Get detailed statistics for a specific player within the league
        
        Args:
            player_id (int): Player ID
            gameweek (int): Gameweek number
            
        Returns:
            Dict: Player statistics within the league
        """
        if not self.teams or not self.gdata:
            return {"error": "League data not loaded"}
        
        # Get player info
        player_info = self.get_player_struct(player_id)
        if not player_info:
            return {"error": "Player not found"}
        
        # Initialize stats
        stats = {
            'player': {
                'id': player_id,
                'web_name': player_info['web_name'],
                'full_name': f"{player_info['first_name']} {player_info['second_name']}",
                'team': self.id_to_team_name(player_info['team']),
                'position': self._get_position_name(player_info['element_type']),
                'price': player_info['now_cost'] / 10,
                'total_points': player_info['total_points']
            },
            'gameweek': gameweek,
            'ownership': {
                'teams': [],
                'count': 0,
                'percentage': 0
            },
            'captaincy': {
                'teams': [],
                'count': 0,
                'percentage': 0
            },
            'transfers': {
                'transferred_in': [],
                'transferred_out': [],
                'net_transfers': 0
            },
            'unique_ownership': {
                'is_unique': False,
                'owned_by': None
            }
        }
        
        total_teams = len(self.teams)
        
        # Check ownership and captaincy for current gameweek
        for team in self.teams:
            team_id = team['entry']
            team_name = team['entry_name']
            
            # Get team's current squad
            team_data = self.get_team_gw_info(team_id, gameweek)
            if not team_data or not team_data.get('picks'):
                continue
            
            # Check if team owns this player
            for pick in team_data['picks']:
                if pick['element'] == player_id:
                    stats['ownership']['teams'].append({
                        'team_name': team_name,
                        'manager': f"{team.get('player_first_name', '')} {team.get('player_last_name', '')}".strip(),
                        'multiplier': pick['multiplier'],
                        'is_captain': pick['is_captain'],
                        'is_vice_captain': pick['is_vice_captain'],
                    })
                    stats['ownership']['count'] += 1
                    
                    # Check captaincy
                    if pick['is_captain']:
                        stats['captaincy']['teams'].append({
                            'team_name': team_name,
                            'manager': f"{team.get('player_first_name', '')} {team.get('player_last_name', '')}".strip()
                        })
                        stats['captaincy']['count'] += 1
                    break
        
        # Calculate percentages
        stats['ownership']['percentage'] = round((stats['ownership']['count'] / total_teams) * 100, 1) if total_teams > 0 else 0
        stats['captaincy']['percentage'] = round((stats['captaincy']['count'] / total_teams) * 100, 1) if total_teams > 0 else 0
        
        # Check for unique ownership
        if stats['ownership']['count'] == 1:
            stats['unique_ownership']['is_unique'] = True
            stats['unique_ownership']['owned_by'] = stats['ownership']['teams'][0]
        
        # Check transfers for this gameweek
        for team in self.teams:
            team_id = team['entry']
            team_name = team['entry_name']
            
            transfers = self.get_team_transfers_info(team_id)
            if not transfers:
                continue
            
            for transfer in transfers:
                if transfer['event'] != gameweek:
                    continue
                
                manager_name = f"{team.get('player_first_name', '')} {team.get('player_last_name', '')}".strip()
                
                # Transferred in
                if transfer['element_in'] == player_id:
                    out_player_name = self.id_to_name(transfer['element_out'])
                    stats['transfers']['transferred_in'].append({
                        'team_name': team_name,
                        'manager': manager_name,
                        'replaced_player': out_player_name,
                        'cost': transfer.get('element_in_cost', 0) / 10,
                        'time': transfer.get('time', '')
                    })
                
                # Transferred out
                if transfer['element_out'] == player_id:
                    in_player_name = self.id_to_name(transfer['element_in'])
                    stats['transfers']['transferred_out'].append({
                        'team_name': team_name,
                        'manager': manager_name,
                        'replacement_player': in_player_name,
                        'time': transfer.get('time', '')
                    })
        
        # Calculate net transfers
        stats['transfers']['net_transfers'] = len(stats['transfers']['transferred_in']) - len(stats['transfers']['transferred_out'])
        
        return stats