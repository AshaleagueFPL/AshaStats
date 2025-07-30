import requests
import json
import time
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union

class FPLLiveTable:
    """
    Fantasy Premier League Live Table Class
    
    Efficiently manages FPL API calls and provides live table data for a specific league.
    Caches data to minimize API requests and provides comprehensive league statistics.
    """
    
    def __init__(self, league_id: int):
        """
        Initialize FPL Live Table with a league ID
        
        Args:
            league_id (int): The FPL mini-league ID
        """
        self.league_id = league_id
        self.base_url = "https://fantasy.premierleague.com/api/"
        
        # Cached data to minimize API calls
        self.bootstrap_data = None
        self.league_data = None
        self.teams_data = {}  # Cache team data by team_id
        self.live_data = {}   # Cache live gameweek data
        self.live_snapshots = {}  # Store historical snapshots for change tracking
        self.current_gameweek = 1
        self.total_gameweeks = 38
        
        # Live tracking
        self.live_tracking_active = False
        self.live_tracking_thread = None
        self.live_callbacks = []
        
        # Initialize core data
        self._load_bootstrap_data()
        self._load_league_data()
    
    def _make_api_request(self, endpoint: str) -> Optional[Dict]:
        """
        Make API request to FPL with error handling
        
        Args:
            endpoint (str): API endpoint
            
        Returns:
            Optional[Dict]: JSON response or None if failed
        """
        url = f'{self.base_url}{endpoint}'
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Request Error for {endpoint}: {e}")
            return None
    
    def _load_bootstrap_data(self) -> bool:
        """
        Load bootstrap-static data (players, teams, gameweeks)
        This contains all players, teams, and gameweek information
        
        Returns:
            bool: True if successful, False otherwise
        """
        print("Loading FPL bootstrap data...")
        self.bootstrap_data = self._make_api_request("bootstrap-static/")
        
        if not self.bootstrap_data:
            print("Failed to load bootstrap data")
            return False
        
        # Find current gameweek
        for i, event in enumerate(self.bootstrap_data['events']):
            if event.get('is_current', False):
                self.current_gameweek = i + 1
                break
            elif event.get('is_next', False):
                self.current_gameweek = max(1, i)
                break
        else:
            # If no current/next found, use the last finished event
            for i, event in enumerate(self.bootstrap_data['events']):
                if event.get('finished', False):
                    self.current_gameweek = i + 1
        
        self.total_gameweeks = len(self.bootstrap_data['events'])
        print(f"Bootstrap data loaded. Current GW: {self.current_gameweek}")
        return True
    
    def _load_league_data(self) -> bool:
        print(f"Loading league data for League ID: {self.league_id}")
        self.league_data = self._make_api_request(f"leagues-classic/{self.league_id}/standings/")
        
        if not self.league_data:
            print("Failed to load league data - check if league ID is valid")
            return False
        
        if 'standings' not in self.league_data:
            print("Invalid league data structure - league may not exist")
            return False
        
        active_teams = len(self.league_data['standings']['results'])
        pending_teams = len(self.league_data.get('new_entries', {}).get('results', []))
        
        if active_teams == 0:
            print("Warning: League has no active teams")
        
        print(f"League data loaded. {active_teams} active teams, {pending_teams} pending teams")
        return True    
    
    def get_live_table(self, gameweek: Optional[int] = None, use_live_points: bool = True) -> List[Dict]:
        """
        Get the live table for the specified gameweek with real-time points calculation
        
        Args:
            gameweek (Optional[int]): Gameweek number, defaults to current gameweek
            use_live_points (bool): Whether to calculate live points during ongoing gameweeks
            
        Returns:
            List[Dict]: Live table with team rankings and actual live points
        """
        if not self.league_data:
            print("League data not available")
            return []
        
        # Check if season has started
        if not self.is_season_started():
            print("Cannot generate live table - season hasn't started yet")
            return []
        
        if gameweek is None:
            gameweek = self.current_gameweek
        
        print(f"Generating live table for GW{gameweek} (Live points: {use_live_points})")
        
        # Get live player data if calculating live points
        live_player_data = {}
        if use_live_points:
            live_player_data = self._get_live_gameweek_data(gameweek)
        
        live_table = []
        teams = self.league_data['standings']['results']
        
        for team in teams:
            team_id = team['entry']
            team_info = self._get_team_gameweek_data(team_id, gameweek)
            
            if team_info:
                # Calculate live points if requested and data available
                if use_live_points and live_player_data:
                    live_points = self._calculate_team_live_points(team_id, gameweek, live_player_data)
                    gameweek_points = live_points
                    # Calculate new total (previous total + live points - original gameweek points)
                    original_gw_points = team_info.get('points', 0)
                    previous_total = team['total'] - original_gw_points
                    live_total = previous_total + live_points
                else:
                    gameweek_points = team_info.get('points', 0)
                    live_total = team['total']
                
                live_entry = {
                    'rank': team['rank'],
                    'previous_rank': team['rank_sort'],
                    'team_name': team['entry_name'],
                    'player_name': f"{team['player_first_name']} {team['player_last_name']}",
                    'total_points': live_total,
                    'original_total_points': team['total'],
                    'gameweek_points': gameweek_points,
                    'original_gameweek_points': team_info.get('points', 0),
                    'gameweek_transfers': team_info.get('transfers', 0),
                    'gameweek_transfer_cost': team_info.get('event_transfers_cost', 0),
                    'gameweek_net_points': gameweek_points - team_info.get('event_transfers_cost', 0),
                    'team_value': team_info.get('value', 0) / 10,
                    'bank': team_info.get('bank', 0) / 10,
                    'started_event': team['started_event'],
                    'team_id': team_id,
                    'is_live': use_live_points and bool(live_player_data),
                    'live_points_difference': gameweek_points - team_info.get('points', 0) if use_live_points else 0
                }
                live_table.append(live_entry)
        
        # Sort by total points (highest first)
        live_table.sort(key=lambda x: x['total_points'], reverse=True)
        
        # Update ranks after sorting
        for i, team in enumerate(live_table):
            team['current_rank'] = i + 1
            team['rank_change'] = team['previous_rank'] - team['current_rank']
        
        return live_table
    
    def get_live_gameweek_table(self, gameweek: Optional[int] = None, use_live_points: bool = True) -> List[Dict]:
        """
        Get live gameweek table showing ONLY current gameweek points and rankings
        
        Args:
            gameweek (Optional[int]): Gameweek number, defaults to current gameweek
            use_live_points (bool): Whether to calculate live points during ongoing gameweeks
            
        Returns:
            List[Dict]: Gameweek table ranked by gameweek points only
        """
        if not self.league_data:
            print("League data not available")
            return []
        
        # Check if season has started
        if not self.is_season_started():
            print("Cannot generate gameweek table - season hasn't started yet")
            return []
        
        if gameweek is None:
            gameweek = self.current_gameweek
        
        print(f"Generating live gameweek table for GW{gameweek} (Live points: {use_live_points})")
        
        # Get live player data if calculating live points
        live_player_data = {}
        if use_live_points:
            live_player_data = self._get_live_gameweek_data(gameweek)
        
        gameweek_table = []
        teams = self.league_data['standings']['results']
        
        for team in teams:
            team_id = team['entry']
            team_info = self._get_team_gameweek_data(team_id, gameweek)
            
            if team_info:
                # Calculate live points if requested and data available
                if use_live_points and live_player_data:
                    live_gw_points = self._calculate_team_live_points(team_id, gameweek, live_player_data)
                    gameweek_points = live_gw_points
                else:
                    gameweek_points = team_info.get('points', 0)
                
                gameweek_entry = {
                    'gameweek_rank': 0,  # Will be set after sorting
                    'overall_rank': team['rank'],
                    'team_name': team['entry_name'],
                    'player_name': f"{team['player_first_name']} {team['player_last_name']}",
                    'gameweek_points': gameweek_points,
                    'original_gameweek_points': team_info.get('points', 0),
                    'gameweek_transfers': team_info.get('transfers', 0),
                    'gameweek_transfer_cost': team_info.get('event_transfers_cost', 0),
                    'gameweek_net_points': gameweek_points - team_info.get('event_transfers_cost', 0),
                    'total_points': team['total'],
                    'team_id': team_id,
                    'is_live': use_live_points and bool(live_player_data),
                    'live_points_difference': gameweek_points - team_info.get('points', 0) if use_live_points else 0,
                    'gameweek': gameweek
                }
                gameweek_table.append(gameweek_entry)
        
        # Sort by gameweek points (highest first)
        gameweek_table.sort(key=lambda x: x['gameweek_net_points'], reverse=True)
        
        # Update gameweek ranks after sorting
        for i, team in enumerate(gameweek_table):
            team['gameweek_rank'] = i + 1
            
            # Calculate rank movement from overall position
            team['rank_movement'] = team['overall_rank'] - team['gameweek_rank']
        
        return gameweek_table
    
    def get_gameweek_top_performers(self, gameweek: Optional[int] = None, limit: int = 10) -> Dict:
        """
        Get top performing teams and players for the current gameweek
        
        Args:
            gameweek (Optional[int]): Gameweek number, defaults to current
            limit (int): Number of top performers to return
            
        Returns:
            Dict: Top teams and players for the gameweek
        """
        if gameweek is None:
            gameweek = self.current_gameweek
        
        gw_table = self.get_live_gameweek_table(gameweek, use_live_points=True)
        
        if not gw_table:
            return {
                'gameweek': gameweek,
                'top_teams': [],
                'top_players': [],
                'biggest_climbers': [],
                'biggest_fallers': [],
                'total_teams': 0,
                'error': 'No gameweek data available'
            }
        
        # Get top performing players
        live_players = self.get_live_player_stats(gameweek)
        top_players = sorted(live_players.items(), 
                           key=lambda x: x[1]['stats'].get('total_points', 0), 
                           reverse=True)[:limit]
        
        # Find biggest climbers and fallers
        climbers = sorted([team for team in gw_table if team['rank_movement'] > 0], 
                         key=lambda x: x['rank_movement'], reverse=True)[:5]
        
        fallers = sorted([team for team in gw_table if team['rank_movement'] < 0], 
                        key=lambda x: x['rank_movement'])[:5]
        
        return {
            'gameweek': gameweek,
            'top_teams': gw_table[:limit],
            'top_players': [
                {
                    'player_id': pid,
                    'name': data['name'],
                    'team': data['team'],
                    'position': data['position'],
                    'points': data['stats'].get('total_points', 0),
                    'goals': data['stats'].get('goals_scored', 0),
                    'assists': data['stats'].get('assists', 0),
                    'bonus': data['stats'].get('bonus', 0),
                    'minutes': data['stats'].get('minutes', 0)
                }
                for pid, data in top_players
            ],
            'biggest_climbers': climbers,
            'biggest_fallers': fallers,
            'total_teams': len(gw_table)
        }
    
    def get_gameweek_summary(self, gameweek: Optional[int] = None) -> Dict:
        """
        Get comprehensive gameweek summary with statistics
        
        Args:
            gameweek (Optional[int]): Gameweek number, defaults to current
            
        Returns:
            Dict: Comprehensive gameweek statistics
        """
        if gameweek is None:
            gameweek = self.current_gameweek
        
        gw_table = self.get_live_gameweek_table(gameweek, use_live_points=True)
        
        # Return consistent structure even when no data
        if not gw_table:
            return {
                'gameweek': gameweek,
                'total_teams': 0,
                'average_points': 0.0,
                'average_net_points': 0.0,
                'average_transfers': 0.0,
                'highest_scorer': {'team_name': 'N/A', 'player_name': 'N/A', 'points': 0},
                'lowest_scorer': {'team_name': 'N/A', 'player_name': 'N/A', 'points': 0},
                'most_transfers': {'team_name': 'N/A', 'player_name': 'N/A', 'transfers': 0},
                'transfer_stats': {
                    'teams_with_transfers': 0,
                    'total_transfer_cost': 0,
                    'percentage_with_transfers': 0.0
                },
                'points_distribution': {
                    'max_points': 0,
                    'min_points': 0,
                    'points_range': 0
                },
                'error': 'No gameweek data available'
            }
                
        # Calculate statistics
        gw_points = [team['gameweek_points'] for team in gw_table]
        net_points = [team['gameweek_net_points'] for team in gw_table]
        transfer_counts = [team['gameweek_transfers'] for team in gw_table]
        
        # Find extremes
        highest_scorer = max(gw_table, key=lambda x: x['gameweek_points'])
        lowest_scorer = min(gw_table, key=lambda x: x['gameweek_points'])
        most_transfers = max(gw_table, key=lambda x: x['gameweek_transfers'])
        
        # Calculate averages
        avg_points = sum(gw_points) / len(gw_points) if gw_points else 0
        avg_net_points = sum(net_points) / len(net_points) if net_points else 0
        avg_transfers = sum(transfer_counts) / len(transfer_counts) if transfer_counts else 0
        
        # Count transfers
        teams_with_transfers = len([t for t in gw_table if t['gameweek_transfers'] > 0])
        total_transfer_cost = sum(team['gameweek_transfer_cost'] for team in gw_table)
        
        return {
            'gameweek': gameweek,
            'total_teams': len(gw_table),
            'average_points': round(avg_points, 1),
            'average_net_points': round(avg_net_points, 1),
            'average_transfers': round(avg_transfers, 1),
            'highest_scorer': {
                'team_name': highest_scorer['team_name'],
                'player_name': highest_scorer['player_name'], 
                'points': highest_scorer['gameweek_points']
            },
            'lowest_scorer': {
                'team_name': lowest_scorer['team_name'],
                'player_name': lowest_scorer['player_name'],
                'points': lowest_scorer['gameweek_points']
            },
            'most_transfers': {
                'team_name': most_transfers['team_name'],
                'player_name': most_transfers['player_name'],
                'transfers': most_transfers['gameweek_transfers']
            },
            'transfer_stats': {
                'teams_with_transfers': teams_with_transfers,
                'total_transfer_cost': total_transfer_cost,
                'percentage_with_transfers': round((teams_with_transfers / len(gw_table)) * 100, 1)
            },
            'points_distribution': {
                'max_points': max(gw_points) if gw_points else 0,
                'min_points': min(gw_points) if gw_points else 0,
                'points_range': max(gw_points) - min(gw_points) if gw_points else 0
            }
        }
    
    def _get_team_gameweek_data(self, team_id: int, gameweek: int) -> Optional[Dict]:
        """
        Get team data for a specific gameweek
        
        Args:
            team_id (int): Team ID
            gameweek (int): Gameweek number
            
        Returns:
            Optional[Dict]: Team gameweek data
        """
        cache_key = f"{team_id}_{gameweek}"
        
        # Check cache first
        if cache_key in self.teams_data:
            return self.teams_data[cache_key]
        
        # Fetch from API
        team_data = self._make_api_request(f"entry/{team_id}/event/{gameweek}/picks/")
        
        if team_data and 'entry_history' in team_data:
            entry_history = team_data['entry_history']
            
            # Cache the result
            self.teams_data[cache_key] = {
                'points': entry_history.get('points', 0),
                'total_points': entry_history.get('total_points', 0),
                'rank': entry_history.get('rank', 0),
                'rank_sort': entry_history.get('rank_sort', 0),
                'overall_rank': entry_history.get('overall_rank', 0),
                'transfers': entry_history.get('event_transfers', 0),
                'event_transfers_cost': entry_history.get('event_transfers_cost', 0),
                'value': entry_history.get('value', 0),
                'bank': entry_history.get('bank', 0)
            }
            
            return self.teams_data[cache_key]
        
        return None
    
    def get_team_squad(self, team_id: int, gameweek: Optional[int] = None) -> List[Dict]:
        """
        Get team squad for a specific gameweek
        
        Args:
            team_id (int): Team ID
            gameweek (Optional[int]): Gameweek number, defaults to current
            
        Returns:
            List[Dict]: Team squad with player details
        """
        if gameweek is None:
            gameweek = self.current_gameweek
        
        team_data = self._make_api_request(f"entry/{team_id}/event/{gameweek}/picks/")
        
        if not team_data or 'picks' not in team_data:
            return []
        
        squad = []
        for pick in team_data['picks']:
            player_info = self._get_player_info(pick['element'])
            if player_info:
                squad_player = {
                    'player_id': pick['element'],
                    'player_name': player_info['web_name'],
                    'team': self._get_team_name(player_info['team']),
                    'position': self._get_position_name(player_info['element_type']),
                    'selling_price': pick['selling_price'] / 10,
                    'multiplier': pick['multiplier'],
                    'is_captain': pick['is_captain'],
                    'is_vice_captain': pick['is_vice_captain'],
                    'position_in_squad': pick['position']
                }
                squad.append(squad_player)
        
        return squad
    
    def _get_player_info(self, player_id: int) -> Optional[Dict]:
        """Get player information from bootstrap data"""
        if not self.bootstrap_data:
            return None
        
        for player in self.bootstrap_data['elements']:
            if player['id'] == player_id:
                return player
        return None
    
    def _get_team_name(self, team_id: int) -> str:
        """Get team name from bootstrap data"""
        if not self.bootstrap_data:
            return f"Team {team_id}"
        
        for team in self.bootstrap_data['teams']:
            if team['id'] == team_id:
                return team['name']
        return f"Team {team_id}"
    
    def _get_position_name(self, position_id: int) -> str:
        """Get position name from bootstrap data"""
        if not self.bootstrap_data:
            return f"Position {position_id}"
        
        for position in self.bootstrap_data['element_types']:
            if position['id'] == position_id:
                return position['singular_name']
        return f"Position {position_id}"
    
    def get_league_info(self) -> Dict:
        """
        Get basic league information
        
        Returns:
            Dict: League information
        """
        if not self.league_data:
            return {}
        
        league_info = self.league_data['league']
        
        # Count active teams (may be 0 in pre-season)
        active_teams = len(self.league_data['standings']['results'])
        
        # Count pending teams (important for pre-season)
        pending_teams = len(self.league_data.get('new_entries', {}).get('results', []))
        
        # Total teams = active + pending
        total_teams = active_teams + pending_teams
        
        return {
            'id': league_info['id'],
            'name': league_info['name'],
            'created': league_info['created'],
            'closed': league_info['closed'],
            'rank': league_info.get('rank'),
            'max_entries': league_info.get('max_entries'),
            'league_type': league_info.get('league_type'),
            'scoring': league_info.get('scoring'),
            'admin_entry': league_info.get('admin_entry'),
            'start_event': league_info.get('start_event'),
            'total_teams': total_teams,  # Include pending teams in total
            'active_teams': active_teams,
            'pending_teams': pending_teams,
            'is_pre_season': not self.is_season_started()
        }    
    def refresh_data(self):
        """Refresh all cached data"""
        print("Refreshing FPL data...")
        self.teams_data.clear()
        self.live_data.clear()
        self._load_bootstrap_data()
        self._load_league_data()
        print("Data refresh completed")
    
    def get_gameweek_deadlines(self) -> List[Dict]:
        """
        Get all gameweek deadlines
        
        Returns:
            List[Dict]: Gameweek deadlines and status
        """
        if not self.bootstrap_data:
            return []
        
        deadlines = []
        for event in self.bootstrap_data['events']:
            deadlines.append({
                'gameweek': event['id'],
                'name': event['name'],
                'deadline_time': event['deadline_time'],
                'finished': event['finished'],
                'is_previous': event.get('is_previous', False),
                'is_current': event.get('is_current', False),
                'is_next': event.get('is_next', False)
            })
        
        return deadlines
    
    def _get_live_gameweek_data(self, gameweek: int) -> Dict:
        """
        Get live player data for the current gameweek
        
        Args:
            gameweek (int): Gameweek number
            
        Returns:
            Dict: Live player data with current stats
        """
        cache_key = f"live_gw_{gameweek}"
        
        # Check cache first (refresh every 5 minutes by checking if we have recent data)
        if cache_key in self.live_data:
            cached_time = self.live_data[cache_key].get('cached_at', 0)
            if datetime.now().timestamp() - cached_time < 300:  # 5 minutes
                return self.live_data[cache_key].get('data', {})
        
        print(f"Fetching live data for GW{gameweek}...")
        live_data = self._make_api_request(f"event/{gameweek}/live/")
        
        if live_data and 'elements' in live_data:
            # Process and cache the live data
            processed_data = {}
            for player_data in live_data['elements']:
                player_id = player_data['id']
                stats = player_data.get('stats', {})
                
                processed_data[player_id] = {
                    'minutes': stats.get('minutes', 0),
                    'goals_scored': stats.get('goals_scored', 0),
                    'assists': stats.get('assists', 0),
                    'clean_sheets': stats.get('clean_sheets', 0),
                    'goals_conceded': stats.get('goals_conceded', 0),
                    'own_goals': stats.get('own_goals', 0),
                    'penalties_saved': stats.get('penalties_saved', 0),
                    'penalties_missed': stats.get('penalties_missed', 0),
                    'yellow_cards': stats.get('yellow_cards', 0),
                    'red_cards': stats.get('red_cards', 0),
                    'saves': stats.get('saves', 0),
                    'bonus': stats.get('bonus', 0),
                    'bps': stats.get('bps', 0),  # Bonus Point System
                    'influence': stats.get('influence', 0),
                    'creativity': stats.get('creativity', 0),
                    'threat': stats.get('threat', 0),
                    'ict_index': stats.get('ict_index', 0),
                    'total_points': stats.get('total_points', 0)
                }
            
            # Cache the data
            self.live_data[cache_key] = {
                'data': processed_data,
                'cached_at': datetime.now().timestamp()
            }
            
            print(f"Live data cached for {len(processed_data)} players")
            return processed_data
        
        print("Failed to fetch live data")
        return {}
    
    def _calculate_team_live_points(self, team_id: int, gameweek: int, live_player_data: Dict) -> int:
        """
        Calculate live points for a team based on current player performances
        
        Args:
            team_id (int): Team ID
            gameweek (int): Gameweek number
            live_player_data (Dict): Live player statistics
            
        Returns:
            int: Total live points for the team
        """
        # Get team's squad for this gameweek
        team_data = self._make_api_request(f"entry/{team_id}/event/{gameweek}/picks/")
        
        if not team_data or 'picks' not in team_data:
            return 0
        
        total_points = 0
        
        for pick in team_data['picks']:
            player_id = pick['element']
            multiplier = pick['multiplier']
            
            # Skip if player is not playing (multiplier = 0)
            if multiplier == 0:
                continue
                
            # Get live stats for this player
            player_stats = live_player_data.get(player_id, {})
            
            if player_stats:
                # Use live total_points if available
                player_points = player_stats.get('total_points', 0)
            else:
                # Fallback: calculate points manually from individual stats
                player_points = self._calculate_player_points(player_id, player_stats)
            
            # Apply multiplier (captain = 2x, vice-captain = 2x if captain doesn't play, normal = 1x)
            total_points += player_points * multiplier
        
        return total_points
    
    def _calculate_player_points(self, player_id: int, stats: Dict) -> int:
        """
        Calculate FPL points for a player based on their stats
        
        Args:
            player_id (int): Player ID
            stats (Dict): Player statistics
            
        Returns:
            int: Total points for the player
        """
        if not stats:
            return 0
        
        # Get player info to determine position
        player_info = self._get_player_info(player_id)
        if not player_info:
            return 0
        
        position = player_info['element_type']  # 1=GK, 2=DEF, 3=MID, 4=FWD
        points = 0
        
        # Basic points for playing
        minutes = stats.get('minutes', 0)
        if minutes > 0:
            points += 1  # Appearance points
            if minutes >= 60:
                points += 1  # 60+ minutes bonus
        
        # Goals
        goals = stats.get('goals_scored', 0)
        if position == 1:  # Goalkeeper
            points += goals * 6
        elif position == 2:  # Defender
            points += goals * 6
        elif position == 3:  # Midfielder
            points += goals * 5
        elif position == 4:  # Forward
            points += goals * 4
        
        # Assists
        points += stats.get('assists', 0) * 3
        
        # Clean sheets
        if stats.get('clean_sheets', 0) > 0:
            if position in [1, 2]:  # GK or DEF
                points += 4
            elif position == 3:  # MID
                points += 1
        
        # Goals conceded (GK and DEF lose points)
        if position in [1, 2]:
            goals_conceded = stats.get('goals_conceded', 0)
            points -= (goals_conceded // 2)  # -1 for every 2 goals conceded
        
        # Penalties
        points += stats.get('penalties_saved', 0) * 5
        points -= stats.get('penalties_missed', 0) * 2
        
        # Cards
        points -= stats.get('yellow_cards', 0) * 1
        points -= stats.get('red_cards', 0) * 3
        
        # Own goals
        points -= stats.get('own_goals', 0) * 2
        
        # Goalkeeper saves (1 point per 3 saves)
        if position == 1:
            saves = stats.get('saves', 0)
            points += saves // 3
        
        # Bonus points
        points += stats.get('bonus', 0)
        
        return max(0, points)  # Ensure points don't go negative
    
    def get_live_player_stats(self, gameweek: Optional[int] = None) -> Dict:
        """
        Get live stats for all players in the current gameweek
        
        Args:
            gameweek (Optional[int]): Gameweek number, defaults to current
            
        Returns:
            Dict: Live player statistics with names and points
        """
        if gameweek is None:
            gameweek = self.current_gameweek
        
        live_data = self._get_live_gameweek_data(gameweek)
        
        if not live_data:
            return {}
        
        # Add player names to the data
        enhanced_data = {}
        for player_id, stats in live_data.items():
            player_info = self._get_player_info(player_id)
            if player_info:
                enhanced_data[player_id] = {
                    'name': player_info['web_name'],
                    'team': self._get_team_name(player_info['team']),
                    'position': self._get_position_name(player_info['element_type']),
                    'stats': stats,
                    'calculated_points': self._calculate_player_points(player_id, stats)
                }
        
        return enhanced_data
    
    def get_team_live_breakdown(self, team_id: int, gameweek: Optional[int] = None) -> Dict:
        """
        Get detailed live points breakdown for a specific team
        
        Args:
            team_id (int): Team ID
            gameweek (Optional[int]): Gameweek number, defaults to current
            
        Returns:
            Dict: Detailed breakdown of team's live performance
        """
        if gameweek is None:
            gameweek = self.current_gameweek
        
        # Get live player data
        live_player_data = self._get_live_gameweek_data(gameweek)
        
        if not live_player_data:
            return {"error": "No live data available"}
        
        # Get team squad
        team_data = self._make_api_request(f"entry/{team_id}/event/{gameweek}/picks/")
        
        if not team_data or 'picks' not in team_data:
            return {"error": "Could not fetch team data"}
        
        breakdown = {
            'team_id': team_id,
            'gameweek': gameweek,
            'players': [],
            'total_live_points': 0,
            'captain_points': 0,
            'vice_captain_points': 0
        }
        
        for pick in team_data['picks']:
            player_id = pick['element']
            player_info = self._get_player_info(player_id)
            
            if not player_info:
                continue
            
            player_stats = live_player_data.get(player_id, {})
            live_points = player_stats.get('total_points', 0)
            calculated_points = self._calculate_player_points(player_id, player_stats)
            
            # Use live points if available, otherwise calculated
            final_points = live_points if live_points > 0 else calculated_points
            multiplied_points = final_points * pick['multiplier']
            
            player_breakdown = {
                'player_id': player_id,
                'name': player_info['web_name'],
                'team': self._get_team_name(player_info['team']),
                'position': self._get_position_name(player_info['element_type']),
                'live_points': final_points,
                'multiplier': pick['multiplier'],
                'total_points': multiplied_points,
                'is_captain': pick['is_captain'],
                'is_vice_captain': pick['is_vice_captain'],
                'position_in_squad': pick['position'],
                'stats': player_stats
            }
            
            breakdown['players'].append(player_breakdown)
            
            if pick['multiplier'] > 0:  # Only count playing players
                breakdown['total_live_points'] += multiplied_points
                
                if pick['is_captain']:
                    breakdown['captain_points'] = multiplied_points
                elif pick['is_vice_captain']:
                    breakdown['vice_captain_points'] = final_points  # VC points without multiplier
        
        return breakdown

    # NEW SEASON / PENDING TEAMS METHODS
    
    def is_season_started(self) -> bool:
        """
        Check if the FPL season has started
        
        Returns:
            bool: True if season has started, False if it's pre-season
        """
        if not self.bootstrap_data:
            return False
        
        # Check if any gameweek is current or finished
        for event in self.bootstrap_data['events']:
            if event.get('is_current', False) or event.get('finished', False):
                return True
        
        # Also check if we have active teams (they only become active when season starts)
        if self.league_data:
            active_teams = len(self.league_data['standings']['results'])
            if active_teams > 0:
                return True
        
        return False   
     
    def get_league_status(self) -> Dict:
        """
        Get comprehensive league status including pending teams
        
        Returns:
            Dict: League status with active and pending teams
        """
        if not self.league_data:
            return {"error": "League data not available"}
        
        league_info = self.league_data['league']
        active_teams = self.league_data['standings']['results']
        
        # Try different possible structures for pending teams
        pending_teams = []
        
        # Check multiple possible locations for pending teams
        possible_pending_locations = [
            self.league_data.get('new_entries', {}).get('results', []),
            self.league_data.get('new_entries', []),
            self.league_data.get('pending_entries', {}).get('results', []),
            self.league_data.get('pending_entries', []),
            self.league_data.get('awaiting_approval', []),
            self.league_data.get('pending', [])
        ]
        
        for location in possible_pending_locations:
            if location and len(location) > 0:
                pending_teams = location
                break
        
        # If no pending teams found in standard locations, check if we need authentication
        # Some pending team data might require admin authentication
        if not pending_teams:
            # Try to fetch pending teams with a different approach
            pending_teams = self._get_pending_teams_alternative()
        
        # Check season status
        season_started = self.is_season_started()
        current_event = league_info.get('start_event', 1)
        
        status = {
            'league': {
                'id': league_info['id'],
                'name': league_info['name'],
                'admin_entry': league_info.get('admin_entry'),
                'start_event': current_event,
                'created': league_info['created'],
                'closed': league_info.get('closed', False),
                'max_entries': league_info.get('max_entries'),
                'league_type': league_info.get('league_type', 'x')
            },
            'season_status': {
                'is_new_season': not season_started,
                'season_started': season_started,
                'current_gameweek': self.current_gameweek
            },
            'teams': {
                'active': {
                    'count': len(active_teams),
                    'teams': [
                        {
                            'entry_id': team['entry'],
                            'team_name': team['entry_name'],
                            'player_name': f"{team['player_first_name']} {team['player_last_name']}",
                            'total_points': team['total'],
                            'rank': team['rank'],
                            'started_event': team['started_event']
                        }
                        for team in active_teams
                    ]
                },
                'pending': {
                    'count': len(pending_teams),
                    'teams': [
                        {
                            'entry_id': team.get('entry', team.get('id')),
                            'team_name': team.get('entry_name', team.get('team_name', 'Unknown')),
                            'player_name': f"{team.get('player_first_name', team.get('first_name', ''))} {team.get('player_last_name', team.get('last_name', ''))}",
                            'player_region_name': team.get('player_region_name', team.get('region', 'Unknown')),
                            'favourite_team': team.get('favourite_team', team.get('supported_team', 'Unknown')),
                            'years_active': team.get('years_active', team.get('fpl_years', 0)),
                            'joined_time': team.get('joined_time', team.get('created', team.get('requested_at')))
                        }
                        for team in pending_teams
                    ]
                }
            },
            'recommendations': [],
            'api_note': f"Pending teams detection: Found {len(pending_teams)} pending teams"
        }
        
        # Add recommendations based on league status
        if not season_started:
            if len(pending_teams) > 0:
                status['recommendations'].append(f"Review {len(pending_teams)} pending team(s) waiting to join")
            
            if len(active_teams) < 8:
                status['recommendations'].append("Consider inviting more managers - leagues with 8+ teams are more competitive")
            
            status['recommendations'].append(f"Season starts at Gameweek {current_event}")
        
        return status
    
    def _get_pending_teams_alternative(self) -> List[Dict]:
        """
        Alternative method to get pending teams - might require different endpoint
        
        Returns:
            List[Dict]: Pending teams if found
        """
        # Try alternative endpoints that might contain pending team information
        alternative_endpoints = [
            f"leagues-classic/{self.league_id}/",  # Base league endpoint
            f"leagues-classic/{self.league_id}/standings/?page_new_entries=1",  # With pagination
            f"leagues-entries-and-h2h-matches/league/{self.league_id}/",  # Alternative league endpoint
        ]
        
        for endpoint in alternative_endpoints:
            try:
                data = self._make_api_request(endpoint)
                if data:
                    # Check for pending teams in various possible locations
                    possible_locations = [
                        data.get('new_entries', {}).get('results', []),
                        data.get('new_entries', []),
                        data.get('pending_entries', []),
                        data.get('awaiting_approval', []),
                        data.get('requests', [])
                    ]
                    
                    for location in possible_locations:
                        if location and len(location) > 0:
                            print(f"Found pending teams in {endpoint}: {len(location)} teams")
                            return location
            except Exception as e:
                print(f"Error checking {endpoint} for pending teams: {e}")
                continue
        
        return []
    
    def get_pending_teams(self) -> List[Dict]:
        """
        Get list of teams waiting to join the league
        
        Returns:
            List[Dict]: Pending teams with details
        """
        if not self.league_data:
            return []
        
        # Try multiple possible locations for pending teams
        pending_teams = []
        
        # Check main league data first
        possible_locations = [
            self.league_data.get('new_entries', {}).get('results', []),
            self.league_data.get('new_entries', []),
            self.league_data.get('pending_entries', {}).get('results', []),
            self.league_data.get('pending_entries', []),
            self.league_data.get('awaiting_approval', []),
            self.league_data.get('pending', [])
        ]
        
        for location in possible_locations:
            if location and len(location) > 0:
                pending_teams = location
                break
        
        # If no pending teams found, try alternative method
        if not pending_teams:
            pending_teams = self._get_pending_teams_alternative()
        
        # Format the pending teams data
        formatted_teams = []
        for team in pending_teams:
            formatted_team = {
                'entry_id': team.get('entry', team.get('id')),
                'team_name': team.get('entry_name', team.get('team_name', 'Unknown')),
                'player_name': f"{team.get('player_first_name', team.get('first_name', ''))} {team.get('player_last_name', team.get('last_name', ''))}",
                'player_region_name': team.get('player_region_name', team.get('region', 'Unknown')),
                'favourite_team': team.get('favourite_team', team.get('supported_team', 'Unknown')),
                'years_active': team.get('years_active', team.get('fpl_years', 0)),
                'joined_time': team.get('joined_time', team.get('created', team.get('requested_at'))),
                'summary': team.get('summary', '')
            }
            formatted_teams.append(formatted_team)
        
        return formatted_teams
    
    def check_pending_teams_access(self) -> Dict:
        """
        Check if we can access pending teams and provide debugging information
        
        Returns:
            Dict: Debug information about pending teams access
        """
        debug_info = {
            'main_endpoint_checked': f"leagues-classic/{self.league_id}/standings/",
            'pending_teams_found': 0,
            'possible_locations_checked': [],
            'alternative_endpoints_tried': [],
            'authentication_required': False,
            'recommendations': []
        }
        
        if not self.league_data:
            debug_info['error'] = "No league data loaded"
            return debug_info
        
        # Check main league data structure
        main_locations = [
            ('new_entries.results', self.league_data.get('new_entries', {}).get('results', [])),
            ('new_entries', self.league_data.get('new_entries', [])),
            ('pending_entries.results', self.league_data.get('pending_entries', {}).get('results', [])),
            ('pending_entries', self.league_data.get('pending_entries', [])),
            ('awaiting_approval', self.league_data.get('awaiting_approval', [])),
            ('pending', self.league_data.get('pending', []))
        ]
        
        for location_name, data in main_locations:
            debug_info['possible_locations_checked'].append({
                'location': location_name,
                'found_items': len(data) if data else 0,
                'sample_keys': list(data[0].keys()) if data and len(data) > 0 else []
            })
            
            if data and len(data) > 0:
                debug_info['pending_teams_found'] = len(data)
        
        # Try alternative endpoints
        alternative_endpoints = [
            f"leagues-classic/{self.league_id}/",
            f"leagues-classic/{self.league_id}/standings/?page_new_entries=1",
            f"leagues-entries-and-h2h-matches/league/{self.league_id}/"
        ]
        
        for endpoint in alternative_endpoints:
            try:
                data = self._make_api_request(endpoint)
                endpoint_info = {
                    'endpoint': endpoint,
                    'success': data is not None,
                    'pending_found': 0
                }
                
                if data:
                    # Check for pending teams in this endpoint
                    alt_locations = [
                        data.get('new_entries', {}).get('results', []),
                        data.get('new_entries', []),
                        data.get('pending_entries', []),
                        data.get('awaiting_approval', [])
                    ]
                    
                    for alt_data in alt_locations:
                        if alt_data and len(alt_data) > 0:
                            endpoint_info['pending_found'] = len(alt_data)
                            debug_info['pending_teams_found'] = max(debug_info['pending_teams_found'], len(alt_data))
                            break
                
                debug_info['alternative_endpoints_tried'].append(endpoint_info)
                
            except Exception as e:
                debug_info['alternative_endpoints_tried'].append({
                    'endpoint': endpoint,
                    'success': False,
                    'error': str(e)
                })
        
        # Add recommendations based on findings
        if debug_info['pending_teams_found'] == 0:
            debug_info['recommendations'].extend([
                "No pending teams found - this could mean:",
                "1. There are genuinely no pending teams",
                "2. You need to be the league admin to see pending teams",
                "3. Authentication is required (login to FPL website first)",
                "4. The API structure has changed",
                "5. Pending teams are only visible during certain periods"
            ])
            debug_info['authentication_required'] = True
        else:
            debug_info['recommendations'].append(f"Found {debug_info['pending_teams_found']} pending teams successfully!")
        
        # Show available keys in league data for debugging
        debug_info['available_league_keys'] = list(self.league_data.keys())
        if 'standings' in self.league_data:
            debug_info['standings_keys'] = list(self.league_data['standings'].keys())
        
        return debug_info
    
    def get_pre_season_summary(self) -> Dict:
        """
        Get pre-season summary with actionable information
        
        Returns:
            Dict: Pre-season status and recommendations
        """
        league_status = self.get_league_status()
        
        if league_status.get('error'):
            return league_status
        
        season_started = league_status['season_status']['season_started']
        active_count = league_status['teams']['active']['count']
        pending_count = league_status['teams']['pending']['count']
        
        summary = {
            'status': 'Season Active' if season_started else 'Pre-Season',
            'team_summary': {
                'ready_to_play': active_count,
                'waiting_to_join': pending_count,
                'total_potential': active_count + pending_count
            },
            'next_steps': [],
            'admin_actions_needed': []
        }
        
        if not season_started:
            # Pre-season recommendations
            if pending_count > 0:
                summary['admin_actions_needed'].append(f"Review {pending_count} pending team(s)")
                summary['next_steps'].append("Accept or decline pending teams before the season starts")
            
            if active_count < 6:
                summary['admin_actions_needed'].append("Recruit more managers")
                summary['next_steps'].append("Invite friends - minimum 6 teams recommended")
            
            summary['next_steps'].append(f"Season starts at GW{league_status['league']['start_event']}")
            
            if active_count >= 8:
                summary['next_steps'].append("League looks ready! Good luck managers 🏆")
        else:
            # Mid-season status
            if pending_count > 0:
                summary['admin_actions_needed'].append(f"Review {pending_count} late joining team(s)")
            
            summary['next_steps'].append("Check live scores and league table")
        
        return summary
    
    # LIVE TRACKING METHODS
    
    def start_live_tracking(self, interval: int = 60, callback=None):
        """
        Start live tracking of league data
        
        Args:
            interval (int): Update interval in seconds (default: 60)
            callback: Optional callback function to call on updates
        """
        if self.live_tracking_active:
            print("Live tracking already active")
            return
        
        if callback:
            self.live_callbacks.append(callback)
        
        self.live_tracking_active = True
        self.live_tracking_thread = threading.Thread(
            target=self._live_tracking_loop,
            args=(interval,),
            daemon=True
        )
        self.live_tracking_thread.start()
        print(f"Live tracking started (interval: {interval}s)")
    
    def stop_live_tracking(self):
        """Stop live tracking"""
        self.live_tracking_active = False
        if self.live_tracking_thread:
            self.live_tracking_thread.join(timeout=5)
        print("Live tracking stopped")
    
    def _live_tracking_loop(self, interval: int):
        """Internal live tracking loop"""
        while self.live_tracking_active:
            try:
                # Get current live data
                current_table = self.get_live_table(use_live_points=True)
                current_players = self.get_live_player_stats()
                
                # Store snapshot
                timestamp = datetime.now().isoformat()
                self.live_snapshots[timestamp] = {
                    'table': current_table,
                    'players': current_players,
                    'gameweek': self.current_gameweek
                }
                
                # Call callbacks
                for callback in self.live_callbacks:
                    try:
                        callback(current_table, current_players)
                    except Exception as e:
                        print(f"Callback error: {e}")
                
                # Clean old snapshots (keep last 10)
                if len(self.live_snapshots) > 10:
                    oldest_key = min(self.live_snapshots.keys())
                    del self.live_snapshots[oldest_key]
                
            except Exception as e:
                print(f"Live tracking error: {e}")
            
            time.sleep(interval)
    
    def get_live_changes(self, minutes_ago: int = 15) -> Dict:
        """
        Get changes in the last X minutes
        
        Args:
            minutes_ago (int): Minutes to look back
            
        Returns:
            Dict: Changes in positions and points
        """
        if not self.live_snapshots:
            return {"error": "No live tracking data available"}
        
        cutoff_time = datetime.now().timestamp() - (minutes_ago * 60)
        
        # Find snapshots within time range
        relevant_snapshots = {}
        for timestamp, data in self.live_snapshots.items():
            snapshot_time = datetime.fromisoformat(timestamp).timestamp()
            if snapshot_time >= cutoff_time:
                relevant_snapshots[timestamp] = data
        
        if len(relevant_snapshots) < 2:
            return {"error": "Not enough data for comparison"}
        
        # Compare oldest and newest in range
        timestamps = sorted(relevant_snapshots.keys())
        old_data = relevant_snapshots[timestamps[0]]
        new_data = relevant_snapshots[timestamps[-1]]
        
        changes = {
            'time_range': f"{minutes_ago} minutes",
            'rank_changes': [],
            'point_changes': [],
            'new_goals': [],
            'new_assists': []
        }
        
        # Compare team positions
        old_table = {team['team_id']: team for team in old_data['table']}
        new_table = {team['team_id']: team for team in new_data['table']}
        
        for team_id, new_team in new_table.items():
            if team_id in old_table:
                old_team = old_table[team_id]
                
                # Rank changes
                if old_team['current_rank'] != new_team['current_rank']:
                    changes['rank_changes'].append({
                        'team_name': new_team['team_name'],
                        'old_rank': old_team['current_rank'],
                        'new_rank': new_team['current_rank'],
                        'change': old_team['current_rank'] - new_team['current_rank']
                    })
                
                # Point changes
                if old_team['gameweek_points'] != new_team['gameweek_points']:
                    changes['point_changes'].append({
                        'team_name': new_team['team_name'],
                        'old_points': old_team['gameweek_points'],
                        'new_points': new_team['gameweek_points'],
                        'change': new_team['gameweek_points'] - old_team['gameweek_points']
                    })
        
        # Compare player stats
        old_players = old_data.get('players', {})
        new_players = new_data.get('players', {})
        
        for player_id, new_player in new_players.items():
            if player_id in old_players:
                old_player = old_players[player_id]
                old_stats = old_player.get('stats', {})
                new_stats = new_player.get('stats', {})
                
                # New goals
                old_goals = old_stats.get('goals_scored', 0)
                new_goals = new_stats.get('goals_scored', 0)
                if new_goals > old_goals:
                    changes['new_goals'].append({
                        'player_name': new_player['name'],
                        'team': new_player['team'],
                        'goals_added': new_goals - old_goals
                    })
                
                # New assists
                old_assists = old_stats.get('assists', 0)
                new_assists = new_stats.get('assists', 0)
                if new_assists > old_assists:
                    changes['new_assists'].append({
                        'player_name': new_player['name'],
                        'team': new_player['team'],
                        'assists_added': new_assists - old_assists
                    })
        
        return changes
    
    # JSON EXPORT METHODS
    
    def to_json_league_status(self) -> str:
        """
        Export league status as JSON string
        
        Returns:
            str: JSON representation of league status
        """
        return json.dumps(self.get_league_status(), indent=2, default=str)
    
    def to_json_live_table(self, gameweek: Optional[int] = None) -> str:
        """
        Export live table as JSON string
        
        Args:
            gameweek (Optional[int]): Gameweek number
            
        Returns:
            str: JSON representation of live table
        """
        table_data = {
            'gameweek': gameweek or self.current_gameweek,
            'timestamp': datetime.now().isoformat(),
            'table': self.get_live_table(gameweek, use_live_points=True)
        }
        return json.dumps(table_data, indent=2, default=str)
    
    def to_json_gameweek_summary(self, gameweek: Optional[int] = None) -> str:
        """
        Export gameweek summary as JSON string
        
        Args:
            gameweek (Optional[int]): Gameweek number
            
        Returns:
            str: JSON representation of gameweek summary
        """
        summary_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': self.get_gameweek_summary(gameweek),
            'top_performers': self.get_gameweek_top_performers(gameweek)
        }
        return json.dumps(summary_data, indent=2, default=str)
    
    def to_json_pre_season_summary(self) -> str:
        """
        Export pre-season summary as JSON string
        
        Returns:
            str: JSON representation of pre-season summary
        """
        pre_season_data = {
            'timestamp': datetime.now().isoformat(),
            'pre_season': self.get_pre_season_summary(),
            'pending_teams': self.get_pending_teams()
        }
        return json.dumps(pre_season_data, indent=2, default=str)


# Example usage and testing
if __name__ == "__main__":
    # Example usage
    league_id = 11862  # Replace with your league ID
    
    try:
        # Initialize the FPL Live Table
        fpl_table = FPLLiveTable(league_id)
        
        # Get league information
        league_info = fpl_table.get_league_info()
        print(f"League: {league_info.get('name', 'Unknown')}")
        print(f"Total Teams: {league_info.get('total_teams', 0)}")
        
        season_started = fpl_table.is_season_started()
        
        if not season_started:
            print(f"\n🆕 PRE-SEASON MODE - Season starts at GW{fpl_table.current_gameweek}")
            
            # Show pre-season information instead of game data
            league_status = fpl_table.get_league_status()
            print(f"Active teams: {league_status['teams']['active']['count']}")
            print(f"Pending teams: {league_status['teams']['pending']['count']}")
            
            # Show pending teams
            pending_teams = fpl_table.get_pending_teams()
            if pending_teams:
                print(f"\n🕒 TEAMS WAITING TO JOIN ({len(pending_teams)}):")
                print("-" * 40)
                for team in pending_teams:
                    print(f"• {team['team_name']} ({team['player_name']})")
                    if team.get('player_region_name'):
                        print(f"  Region: {team['player_region_name']}")
            
            # Show pre-season summary
            pre_season = fpl_table.get_pre_season_summary()
            print(f"\n📋 PRE-SEASON SUMMARY:")
            print(f"Status: {pre_season['status']}")
            print(f"Teams ready: {pre_season['team_summary']['ready_to_play']}")
            print(f"Teams waiting: {pre_season['team_summary']['waiting_to_join']}")
            
            if pre_season['next_steps']:
                print(f"\n📝 NEXT STEPS:")
                for step in pre_season['next_steps']:
                    print(f"• {step}")
            
            print("\n⚠️ Skipping live game data - season hasn't started yet")
            
        else:
        
            # Get live table for current gameweek with live points
            live_table = fpl_table.get_live_table(use_live_points=True)
            
            print(f"\n=== OVERALL LIVE TABLE - GW{fpl_table.current_gameweek} ===")
            print(f"{'Rank':<4} {'Team Name':<20} {'Manager':<20} {'Live Pts':<8} {'Total':<7} {'Diff':<6}")
            print("-" * 75)
            
            for team in live_table[:10]:  # Show top 10
                live_diff = team['live_points_difference']
                diff_symbol = f"+{live_diff}" if live_diff > 0 else str(live_diff) if live_diff < 0 else "0"
                
                print(f"{team['current_rank']:<4} {team['team_name'][:19]:<20} "
                    f"{team['player_name'][:19]:<20} {team['gameweek_points']:<8} "
                    f"{team['total_points']:<7} {diff_symbol:<6}")
            
            # Get gameweek-only table
            gameweek_table = fpl_table.get_live_gameweek_table(use_live_points=True)
            
            print(f"\n=== GAMEWEEK {fpl_table.current_gameweek} TABLE (GW Points Only) ===")
            print(f"{'GW Rank':<8} {'Team Name':<20} {'Manager':<20} {'GW Pts':<7} {'Net':<6} {'Move':<6}")
            print("-" * 75)
            
            for team in gameweek_table[:10]:  # Show top 10 for gameweek
                movement = team['rank_movement']
                move_symbol = f"↑{movement}" if movement > 0 else f"↓{abs(movement)}" if movement < 0 else "="
                
                print(f"{team['gameweek_rank']:<8} {team['team_name'][:19]:<20} "
                    f"{team['player_name'][:19]:<20} {team['gameweek_points']:<7} "
                    f"{team['gameweek_net_points']:<6} {move_symbol:<6}")
            
            # Get gameweek summary
            gw_summary = fpl_table.get_gameweek_summary()
            if gw_summary.get('error'):
                print(f"Error: {gw_summary['error']}")
                print(f"Total teams: {gw_summary['total_teams']}")
            else:
                print(f"Average Points: {gw_summary['average_points']}")
                print(f"Highest Scorer: {gw_summary['highest_scorer']['team_name']} ({gw_summary['highest_scorer']['points']} pts)")
                print(f"Teams with Transfers: {gw_summary['transfer_stats']['teams_with_transfers']}/{gw_summary['total_teams']} "
                    f"({gw_summary['transfer_stats']['percentage_with_transfers']}%)")
            
            # Get top performers
            top_performers = fpl_table.get_gameweek_top_performers(limit=5)
            
            if top_performers.get('error'):
                print(f"Error: {top_performers['error']}")
            else:
                print(f"{'Team':<20} {'Manager':<20} {'GW Pts':<7} {'Transfers':<9}")
                print("-" * 60)
                
                for team in top_performers['top_teams']:
                    transfers_text = f"{team['gameweek_transfers']}T" if team['gameweek_transfers'] > 0 else "0T"
                    print(f"{team['team_name'][:19]:<20} {team['player_name'][:19]:<20} "
                        f"{team['gameweek_points']:<7} {transfers_text:<9}")
                
                if top_performers['biggest_climbers']:
                    print(f"\n=== BIGGEST CLIMBERS THIS GAMEWEEK ===")
                    for team in top_performers['biggest_climbers'][:3]:
                        print(f"{team['team_name']} (↑{team['rank_movement']} positions) - {team['gameweek_points']} pts")

            
            # Show live player stats
            print(f"\n=== TOP LIVE PERFORMERS - GW{fpl_table.current_gameweek} ===")
            live_players = fpl_table.get_live_player_stats()
            
            # Sort by live points
            sorted_players = sorted(live_players.items(), 
                                key=lambda x: x[1]['stats'].get('total_points', 0), 
                                reverse=True)
            
            print(f"{'Player':<20} {'Team':<15} {'Pts':<4} {'Goals':<5} {'Assists':<7} {'Bonus':<5}")
            print("-" * 60)
            
            for player_id, data in sorted_players[:10]:
                stats = data['stats']
                print(f"{data['name'][:19]:<20} {data['team'][:14]:<15} "
                    f"{stats.get('total_points', 0):<4} {stats.get('goals_scored', 0):<5} "
                    f"{stats.get('assists', 0):<7} {stats.get('bonus', 0):<5}")
            
            # Initialize live tracking
            print("🔴 Starting live tracking...")
            fpl_table.start_live_tracking()
            
            print("\n" + "="*60)
            print("🆕 NEW SEASON / PENDING TEAMS DETECTION")
            print("="*60)
            
            # Check if it's a new season
            is_new = fpl_table.is_season_started()
            print(f"Season started: {is_new}")
            
            # DEBUGGING: Check pending teams access
            print("\n🔍 DEBUGGING PENDING TEAMS ACCESS:")
            print("-" * 40)
            pending_debug = fpl_table.check_pending_teams_access()
            
            print(f"Main endpoint: {pending_debug['main_endpoint_checked']}")
            print(f"Pending teams found: {pending_debug['pending_teams_found']}")
            print(f"Available league keys: {pending_debug['available_league_keys']}")
            
            if pending_debug.get('standings_keys'):
                print(f"Standings structure: {pending_debug['standings_keys']}")
            
            print("\nLocations checked for pending teams:")
            for location in pending_debug['possible_locations_checked']:
                print(f"  📍 {location['location']}: {location['found_items']} items")
                if location['sample_keys']:
                    print(f"     Sample keys: {location['sample_keys']}")
            
            print("\nAlternative endpoints tried:")
            for endpoint in pending_debug['alternative_endpoints_tried']:
                status = "✅" if endpoint['success'] else "❌"
                print(f"  {status} {endpoint['endpoint']}")
                if endpoint['success'] and 'pending_found' in endpoint:
                    print(f"     Pending teams: {endpoint['pending_found']}")
                elif not endpoint['success'] and 'error' in endpoint:
                    print(f"     Error: {endpoint['error']}")
            
            print(f"\nRecommendations:")
            for rec in pending_debug['recommendations']:
                print(f"  💡 {rec}")
            
            # Get league status (crucial for new seasons)
            league_status = fpl_table.get_league_status()
            print(f"\n📊 LEAGUE STATUS:")
            print(f"League: {league_status.get('league', {}).get('name', 'Unknown')}")
            print(f"Active teams: {league_status['teams']['active']['count']}")
            print(f"Pending teams: {league_status['teams']['pending']['count']}")
            print(f"Is new season: {league_status['season_status']['is_new_season']}")
            
            if 'api_note' in league_status:
                print(f"API Note: {league_status['api_note']}")
            
            # Show pending teams if any
            pending_teams = fpl_table.get_pending_teams()
            if pending_teams:
                print(f"\n🕒 TEAMS WAITING TO JOIN ({len(pending_teams)}):")
                print("-" * 40)
                for team in pending_teams:
                    print(f"• {team['team_name']} ({team['player_name']})")
                    print(f"  Region: {team.get('player_region_name', 'Unknown')}")
                    print(f"  Favourite team: {team.get('favourite_team', 'Unknown')}")
                    print(f"  Years active: {team.get('years_active', 0)}")
                    if team.get('joined_time'):
                        print(f"  Joined: {team['joined_time']}")
                    print()
            else:
                print("\n✅ No teams waiting to join")
                print("Note: This could mean no pending teams exist, or authentication may be required to see them.")
            
            # Show pre-season summary
            pre_season = fpl_table.get_pre_season_summary()
            print(f"\n📋 PRE-SEASON SUMMARY:")
            print(f"Status: {pre_season['status']}")
            print(f"Teams ready: {pre_season['team_summary']['ready_to_play']}")
            print(f"Teams waiting: {pre_season['team_summary']['waiting_to_join']}")
            
            if pre_season['next_steps']:
                print(f"\n📝 NEXT STEPS:")
                for step in pre_season['next_steps']:
                    print(f"• {step}")
            
            if pre_season['admin_actions_needed']:
                print(f"\n👨‍💼 ADMIN ACTIONS NEEDED:")
                for action in pre_season['admin_actions_needed']:
                    print(f"• {action}")
            
            print("\n" + "="*60)
            print("📱 NEW SEASON JSON APIs")
            print("="*60)
            
            # League Status JSON (most important for new seasons)
            print("\n1️⃣ LEAGUE STATUS JSON (includes pending teams):")
            print("=" * 45)
            status_json = fpl_table.to_json_league_status()
            print(status_json[:800] + "..." if len(status_json) > 800 else status_json)
            
            # Pre-season Summary JSON
            print("\n2️⃣ PRE-SEASON SUMMARY JSON:")
            print("=" * 30)
            preseason_json = fpl_table.to_json_pre_season_summary()
            print(preseason_json[:600] + "..." if len(preseason_json) > 600 else preseason_json)
            
            print("\n" + "="*60)
            print("💡 NEW SEASON GUI EXAMPLES:")
            print("="*60)
                        
            # Test live tracking for 30 seconds
            print(f"\n🔴 Testing live tracking for 30 seconds...")
            
            def live_update_callback(table, players):
                print(f"📊 Live update: Top team has {table[0]['gameweek_points']} points")
            
            fpl_table.live_callbacks.append(live_update_callback)
            
            # Wait and then stop
            time.sleep(30)
            fpl_table.stop_live_tracking()
            
            # Show any changes detected
            changes = fpl_table.get_live_changes(minutes_ago=30)
            if not changes.get('error'):
                print(f"\n📈 LIVE CHANGES (last 30 minutes):")
                if changes['rank_changes']:
                    print("Rank changes:")
                    for change in changes['rank_changes']:
                        print(f"  {change['team_name']}: {change['old_rank']} → {change['new_rank']}")
                
                if changes['point_changes']:
                    print("Point changes:")
                    for change in changes['point_changes']:
                        print(f"  {change['team_name']}: +{change['change']} points")
        
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure to replace 'league_id' with a valid FPL league ID")