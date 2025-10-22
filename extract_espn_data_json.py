#!/usr/bin/env python3
"""
ESPN Fantasy Football Comprehensive JSON Data Extractor
Extracts ALL available data for deep analysis and GitHub.io endpoint
"""

import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
import requests
from espn_api.football import League

# ESPN Configuration
LEAGUE_ID = 44181678
YEAR = 2025
ESPN_S2 = os.environ.get('ESPN_S2')
SWID = os.environ.get('SWID')
MY_TEAM_NAME = 'Intelligent MBLeague (TM)'

# NFL Team Abbreviation Mapping
ESPN_TO_STANDARD = {
    'Ari': 'ARI', 'Atl': 'ATL', 'Bal': 'BAL', 'Buf': 'BUF', 'Car': 'CAR',
    'Chi': 'CHI', 'Cin': 'CIN', 'Cle': 'CLE', 'Dal': 'DAL', 'Den': 'DEN',
    'Det': 'DET', 'GB': 'GB', 'Hou': 'HOU', 'Ind': 'IND', 'Jax': 'JAX',
    'KC': 'KC', 'LAC': 'LAC', 'LAR': 'LAR', 'LV': 'LV', 'Mia': 'MIA',
    'Min': 'MIN', 'NE': 'NE', 'NO': 'NO', 'NYG': 'NYG', 'NYJ': 'NYJ',
    'Phi': 'PHI', 'Pit': 'PIT', 'SF': 'SF', 'Sea': 'SEA', 'TB': 'TB',
    'Ten': 'TEN', 'Wsh': 'WSH',
    'ARI': 'ARI', 'ATL': 'ATL', 'BAL': 'BAL', 'BUF': 'BUF', 'CAR': 'CAR',
    'CHI': 'CHI', 'CIN': 'CIN', 'CLE': 'CLE', 'DAL': 'DAL', 'DEN': 'DEN',
    'DET': 'DET', 'HOU': 'HOU', 'IND': 'IND', 'JAX': 'JAX',
    'KC': 'KC', 'LAC': 'LAC', 'LAR': 'LAR', 'LV': 'LV', 'MIA': 'MIA',
    'MIN': 'MIN', 'NE': 'NE', 'NO': 'NO', 'NYG': 'NYG', 'NYJ': 'NYJ',
    'PHI': 'PHI', 'PIT': 'PIT', 'SF': 'SF', 'SEA': 'SEA', 'TB': 'TB',
    'TEN': 'TEN', 'WSH': 'WSH',
}

def connect_to_league():
    """Connect to ESPN Fantasy League"""
    print(f"Connecting to league {LEAGUE_ID}...")
    league = League(
        league_id=LEAGUE_ID,
        year=YEAR,
        espn_s2=ESPN_S2,
        swid=SWID
    )
    return league

def find_my_team(league):
    """Find user's team in the league"""
    for team in league.teams:
        if team.team_name == MY_TEAM_NAME:
            return team
    raise ValueError(f"Could not find team '{MY_TEAM_NAME}'")

def fetch_nfl_schedule(week, year=2025):
    """Fetch NFL schedule from ESPN's public API with game details"""
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={year}&seasontype=2&week={week}"
        print(f"Fetching NFL schedule for week {week}...")
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        schedule = {}
        game_details = {}
        
        if 'events' in data:
            for event in data['events']:
                if 'competitions' in event and len(event['competitions']) > 0:
                    comp = event['competitions'][0]
                    
                    # Extract game details
                    game_info = {
                        'date': event.get('date', ''),
                        'status': comp.get('status', {}).get('type', {}).get('description', 'Scheduled'),
                        'venue': comp.get('venue', {}).get('fullName', 'Unknown'),
                        'weather': comp.get('weather', {}),
                        'odds': comp.get('odds', [{}])[0] if comp.get('odds') else {},
                        'broadcasts': [b.get('names', [''])[0] for b in comp.get('broadcasts', [])],
                    }
                    
                    if 'competitors' in comp:
                        home_team = None
                        away_team = None
                        
                        for competitor in comp['competitors']:
                            team_abbrev = competitor['team'].get('abbreviation', '')
                            is_home = competitor.get('homeAway') == 'home'
                            
                            if is_home:
                                home_team = team_abbrev
                                game_info['home_team'] = team_abbrev
                                game_info['home_score'] = competitor.get('score', 0)
                            else:
                                away_team = team_abbrev
                                game_info['away_team'] = team_abbrev
                                game_info['away_score'] = competitor.get('score', 0)
                        
                        if home_team and away_team:
                            schedule[home_team] = f'vs {away_team}'
                            schedule[away_team] = f'@{home_team}'
                            game_details[home_team] = game_info
                            game_details[away_team] = game_info
        
        all_teams = set(ESPN_TO_STANDARD.values())
        for team in all_teams:
            if team not in schedule:
                schedule[team] = 'BYE'
                game_details[team] = {'status': 'BYE'}
        
        print(f"â Found {len([v for v in schedule.values() if v != 'BYE'])} games scheduled")
        return schedule, game_details
        
    except Exception as e:
        print(f"Warning: Could not fetch NFL schedule: {e}")
        return {}, {}

def get_weekly_stats(player, current_week):
    """Extract weekly performance data"""
    weekly_data = []
    
    if not hasattr(player, 'stats') or not isinstance(player.stats, dict):
        return weekly_data
    
    # Get all available weeks
    for week in range(1, current_week + 1):
        week_stats = player.stats.get(week, {})
        if isinstance(week_stats, dict):
            weekly_data.append({
                'week': week,
                'points': week_stats.get('points', 0),
                'projected_points': week_stats.get('projected_points', 0),
                'breakdown': week_stats.get('breakdown', {}),
                'projected_breakdown': week_stats.get('projected_breakdown', {}),
            })
    
    return weekly_data

def calculate_consistency_metrics(weekly_stats):
    """Calculate advanced consistency and performance metrics"""
    if not weekly_stats:
        return {}
    
    points = [w['points'] for w in weekly_stats if w['points'] > 0]
    projections = [w['projected_points'] for w in weekly_stats if w['projected_points'] > 0]
    
    if not points:
        return {}
    
    import statistics
    
    metrics = {
        'games_played': len(points),
        'avg_points': statistics.mean(points),
        'median_points': statistics.median(points),
        'std_dev': statistics.stdev(points) if len(points) > 1 else 0,
        'min_points': min(points),
        'max_points': max(points),
        'consistency_score': 0,
        'boom_weeks': 0,
        'bust_weeks': 0,
        'vs_projection_avg': 0,
    }
    
    # Consistency score (lower std_dev relative to mean = more consistent)
    if metrics['avg_points'] > 0:
        metrics['consistency_score'] = round(100 - (metrics['std_dev'] / metrics['avg_points'] * 100), 2)
    
    # Boom/Bust analysis (compared to season average)
    for pts in points:
        if pts > metrics['avg_points'] * 1.5:
            metrics['boom_weeks'] += 1
        elif pts < metrics['avg_points'] * 0.5:
            metrics['bust_weeks'] += 1
    
    # Performance vs projection
    if projections and len(points) == len(projections):
        diffs = [points[i] - projections[i] for i in range(len(points))]
        metrics['vs_projection_avg'] = round(statistics.mean(diffs), 2)
        metrics['exceeded_projection_pct'] = round(len([d for d in diffs if d > 0]) / len(diffs) * 100, 1)
    
    return metrics

def get_player_full_data(player, league, nfl_schedule, game_details):
    """Extract comprehensive player data"""
    week = league.current_week
    
    # Basic info
    injury_status = player.injuryStatus if hasattr(player, 'injuryStatus') else 'ACTIVE'
    if isinstance(injury_status, list):
        injury_status = injury_status[0] if injury_status else 'ACTIVE'
    
    pro_team = ESPN_TO_STANDARD.get(player.proTeam, player.proTeam)
    opponent_display = nfl_schedule.get(pro_team, 'vs OPP')
    
    # Get weekly stats
    weekly_stats = get_weekly_stats(player, week)
    
    # Calculate metrics
    consistency_metrics = calculate_consistency_metrics(weekly_stats)
    
    # Current week projection
    current_week_stats = player.stats.get(week, {}) if hasattr(player, 'stats') else {}
    projected = current_week_stats.get('projected_points', 0) if isinstance(current_week_stats, dict) else 0
    projected_breakdown = current_week_stats.get('projected_breakdown', {}) if isinstance(current_week_stats, dict) else {}
    
    # Game details for this week
    game_info = game_details.get(pro_team, {})
    
    player_data = {
        # Identity
        'name': player.name,
        'position': player.position,
        'eligible_slots': getattr(player, 'eligibleSlots', []),
        'lineup_slot': player.lineupSlot,
        'pro_team': pro_team,
        'player_id': getattr(player, 'playerId', None),
        
        # Health & Availability
        'injury_status': injury_status,
        'injury_status_display': get_injury_status_display(injury_status),
        
        # Matchup Info
        'opponent': opponent_display,
        'game_details': game_info,
        
        # Ownership
        'percent_owned': round(player.percent_owned, 1),
        'percent_started': round(player.percent_started, 1),
        'ownership_change': getattr(player, 'percent_change', 0),
        
        # Scoring Stats
        'total_points': round(player.total_points, 2),
        'avg_points': round(player.avg_points, 2),
        'projected_points': round(projected, 2),
        'projected_breakdown': projected_breakdown,
        
        # Advanced Metrics
        'consistency_metrics': consistency_metrics,
        'weekly_stats': weekly_stats,
        
        # Additional ESPN data
        'acquisition_type': getattr(player, 'acquisitionType', 'UNKNOWN'),
        'on_bye_week': opponent_display == 'BYE',
    }
    
    return player_data

def get_injury_status_display(status):
    """Get human-readable injury status"""
    if isinstance(status, list):
        status = status[0] if status else 'ACTIVE'
    
    status_map = {
        'ACTIVE': 'Healthy',
        'QUESTIONABLE': 'Questionable',
        'DOUBTFUL': 'Doubtful',
        'OUT': 'Out',
        'INJURY_RESERVE': 'IR (4+ weeks)',
        'IR': 'IR (4+ weeks)',
        'SUSPENSION': 'Suspended',
        'DAY_TO_DAY': 'Day-to-Day',
    }
    return status_map.get(status, str(status))

def get_scoring_type(league):
    """Safely detect league scoring type"""
    try:
        # Try different ways to access scoring settings
        if hasattr(league.settings, 'scoring_settings'):
            scoring = league.settings.scoring_settings
        elif hasattr(league, 'scoring_settings'):
            scoring = league.scoring_settings
        else:
            return 'Unknown'
        
        # Check for PPR value
        if isinstance(scoring, dict):
            ppr_value = scoring.get('receivingReceptions', scoring.get('rec', 0))
        else:
            ppr_value = getattr(scoring, 'receivingReceptions', getattr(scoring, 'rec', 0))
        
        if ppr_value == 1:
            return 'PPR'
        elif ppr_value == 0.5:
            return 'Half-PPR'
        else:
            return 'Standard'
    except:
        return 'Unknown'

def get_roster_settings(league):
    """Safely extract roster settings"""
    try:
        roster_info = {}
        
        if hasattr(league.settings, 'roster'):
            roster = league.settings.roster
            if isinstance(roster, dict):
                roster_info = roster
            else:
                # Try to get attributes
                for attr in ['rosterSize', 'roster_size', 'benchSize', 'bench_size']:
                    if hasattr(roster, attr):
                        roster_info[attr] = getattr(roster, attr)
        
        return roster_info if roster_info else {'note': 'Roster settings not available'}
    except:
        return {'note': 'Roster settings not available'}


def analyze_positional_scarcity(league, position):
    """Analyze how scarce a position is based on rostered vs available players"""
    rostered = []
    available = []
    
    # Get all rostered players at position
    for team in league.teams:
        for player in team.roster:
            if player.position == position:
                rostered.append(player.avg_points)
    
    # Get available players at position
    try:
        free_agents = league.free_agents(size=50)
        for player in free_agents:
            if player.position == position:
                available.append(player.avg_points)
    except:
        pass
    
    if not rostered:
        return {}
    
    import statistics
    
    scarcity = {
        'position': position,
        'rostered_count': len(rostered),
        'available_count': len(available),
        'rostered_avg': round(statistics.mean(rostered), 2) if rostered else 0,
        'available_avg': round(statistics.mean(available), 2) if available else 0,
        'scarcity_score': 0,
    }
    
    # Scarcity score: higher when there's a big gap between rostered and available
    if scarcity['available_avg'] > 0:
        scarcity['scarcity_score'] = round(scarcity['rostered_avg'] / scarcity['available_avg'], 2)
    
    return scarcity

def get_recent_transactions(league, days=7):
    """Get recent league activity"""
    transactions = []
    
    try:
        # ESPN API provides recent activity
        if hasattr(league, 'recent_activity'):
            for activity in league.recent_activity(size=50):
                trans_date = getattr(activity, 'date', None)
                
                # Filter by date if available
                if trans_date:
                    activity_age = datetime.now() - datetime.fromtimestamp(trans_date / 1000)
                    if activity_age.days > days:
                        continue
                
                trans = {
                    'type': getattr(activity, 'action', 'UNKNOWN'),
                    'date': trans_date,
                    'team': getattr(activity, 'team_name', 'Unknown'),
                }
                
                # Add player info if available
                if hasattr(activity, 'actions'):
                    for action in activity.actions:
                        if hasattr(action, 'player'):
                            trans['player'] = action.player.name
                            trans['player_position'] = action.player.position
                
                transactions.append(trans)
    except Exception as e:
        print(f"Could not fetch transactions: {e}")
    
    return transactions

def calculate_strength_of_schedule(team, league, weeks_ahead=3):
    """Calculate remaining strength of schedule"""
    current_week = league.current_week
    upcoming_opponents = []
    
    try:
        for i in range(current_week, min(current_week + weeks_ahead, len(team.schedule))):
            opponent = team.schedule[i]
            if opponent:
                opp_avg = opponent.points_for / max(1, opponent.wins + opponent.losses)
                upcoming_opponents.append({
                    'week': i + 1,
                    'opponent': opponent.team_name,
                    'opponent_avg': round(opp_avg, 2),
                    'opponent_record': f"{opponent.wins}-{opponent.losses}",
                    'opponent_standing': opponent.standing,
                })
    except:
        pass
    
    if upcoming_opponents:
        avg_opponent_strength = sum(o['opponent_avg'] for o in upcoming_opponents) / len(upcoming_opponents)
        return {
            'upcoming_opponents': upcoming_opponents,
            'avg_opponent_strength': round(avg_opponent_strength, 2),
            'difficulty_rating': 'Hard' if avg_opponent_strength > 100 else 'Medium' if avg_opponent_strength > 85 else 'Easy',
        }
    
    return {}

def calculate_playoff_probability(team, league):
    """Estimate playoff probability based on current standing and remaining schedule"""
    teams_count = len(league.teams)
    playoff_spots = league.settings.playoff_team_count
    current_standing = team.standing
    
    weeks_remaining = league.settings.reg_season_count - league.current_week
    
    # Simple estimation
    if current_standing <= playoff_spots:
        base_prob = 90
    elif current_standing <= playoff_spots + 2:
        base_prob = 60
    elif current_standing <= playoff_spots + 4:
        base_prob = 30
    else:
        base_prob = 10
    
    # Adjust based on weeks remaining
    prob = min(99, base_prob + (weeks_remaining * 2))
    
    return {
        'estimated_probability': prob,
        'current_standing': current_standing,
        'playoff_spots': playoff_spots,
        'weeks_remaining': weeks_remaining,
        'must_win_games': max(0, playoff_spots - current_standing + 2) if current_standing > playoff_spots else 0,
    }

def get_trade_targets_analysis(league, my_team):
    """Analyze potential trade targets based on team needs"""
    trade_targets = []
    
    # Analyze my team's weaknesses
    my_positions = defaultdict(list)
    for player in my_team.roster:
        if player.lineupSlot != 'BE':
            my_positions[player.position].append(player.avg_points)
    
    # Find teams with surpluses at positions I'm weak in
    for team in league.teams:
        if team.team_id == my_team.team_id:
            continue
        
        team_positions = defaultdict(list)
        for player in team.roster:
            team_positions[player.position].append({
                'name': player.name,
                'avg_points': player.avg_points,
                'lineup_slot': player.lineupSlot,
            })
        
        # Look for teams with depth at positions
        for pos, players in team_positions.items():
            if len(players) > 2:  # They have depth
                # Sort by points
                sorted_players = sorted(players, key=lambda x: x['avg_points'], reverse=True)
                
                # Their bench players might be trade targets
                bench_stars = [p for p in sorted_players if p['lineup_slot'] == 'BE' and p['avg_points'] > 5]
                
                if bench_stars:
                    trade_targets.append({
                        'team': team.team_name,
                        'position': pos,
                        'trade_candidates': bench_stars[:2],  # Top 2 bench players
                        'team_record': f"{team.wins}-{team.losses}",
                        'analysis': f"{team.team_name} has depth at {pos}",
                    })
    
    return trade_targets

def generate_comprehensive_json(league, my_team):
    """Generate comprehensive JSON with all available data"""
    print("Generating comprehensive JSON data...")
    
    current_week = league.current_week
    nfl_schedule, game_details = fetch_nfl_schedule(current_week, YEAR)
    
    # Build the massive data structure
    data = {
        'meta': {
            'generated_at': datetime.now().isoformat(),
            'league_id': LEAGUE_ID,
            'year': YEAR,
            'current_week': current_week,
            'last_updated': datetime.now().strftime('%Y-%m-%d %I:%M %p ET'),
        },
        
        'league_info': {
            'name': league.settings.name,
            'total_teams': len(league.teams),
            'regular_season_weeks': league.settings.reg_season_count,
            'playoff_teams': league.settings.playoff_team_count,
            'scoring_type': get_scoring_type(league),
            'roster_settings': get_roster_settings(league),
        },
        
        'my_team': {
            'team_id': my_team.team_id,
            'team_name': my_team.team_name,
            'owner': getattr(my_team, 'owner', 'Unknown'),
            'record': {
                'wins': my_team.wins,
                'losses': my_team.losses,
                'ties': getattr(my_team, 'ties', 0),
            },
            'standing': my_team.standing,
            'points_for': round(my_team.points_for, 2),
            'points_against': round(my_team.points_against, 2),
            'avg_points_per_week': round(my_team.points_for / max(1, my_team.wins + my_team.losses), 2),
            'playoff_probability': calculate_playoff_probability(my_team, league),
            'strength_of_schedule': calculate_strength_of_schedule(my_team, league),
        },
        
        'current_matchup': {},
        
        'my_roster': [],
        
        'all_teams': [],
        
        'available_players': {
            'QB': [],
            'RB': [],
            'WR': [],
            'TE': [],
            'K': [],
            'D/ST': [],
        },
        
        'positional_scarcity': {},
        
        'recent_transactions': get_recent_transactions(league),
        
        'trade_targets': get_trade_targets_analysis(league, my_team),
        
        'nfl_schedule': {
            'week': current_week,
            'games': game_details,
        },
        
        'next_week_preview': {},
    }
    
    # Current matchup
    try:
        opponent = my_team.schedule[current_week - 1]
        if opponent:
            data['current_matchup'] = {
                'week': current_week,
                'opponent_name': opponent.team_name,
                'opponent_record': f"{opponent.wins}-{opponent.losses}",
                'opponent_standing': opponent.standing,
                'opponent_avg': round(opponent.points_for / max(1, opponent.wins + opponent.losses), 2),
                'opponent_points_for': round(opponent.points_for, 2),
                'opponent_points_against': round(opponent.points_against, 2),
            }
    except:
        data['current_matchup'] = {'week': current_week, 'status': 'BYE'}
    
    # My roster with full details
    print("Extracting my roster...")
    for player in my_team.roster:
        data['my_roster'].append(get_player_full_data(player, league, nfl_schedule, game_details))
    
    # All league teams
    print("Extracting all league rosters...")
    for team in sorted(league.teams, key=lambda x: x.standing):
        team_data = {
            'team_id': team.team_id,
            'team_name': team.team_name,
            'owner': getattr(team, 'owner', 'Unknown'),
            'standing': team.standing,
            'record': {
                'wins': team.wins,
                'losses': team.losses,
                'ties': getattr(team, 'ties', 0),
            },
            'points_for': round(team.points_for, 2),
            'points_against': round(team.points_against, 2),
            'avg_points_per_week': round(team.points_for / max(1, team.wins + team.losses), 2),
            'roster': [],
            'strength_of_schedule': calculate_strength_of_schedule(team, league),
        }
        
        for player in team.roster:
            team_data['roster'].append(get_player_full_data(player, league, nfl_schedule, game_details))
        
        data['all_teams'].append(team_data)
    
    # Available players by position
    print("Extracting available players...")
    positions = ['QB', 'RB', 'WR', 'TE', 'K', 'D/ST']
    for pos in positions:
        try:
            free_agents = league.free_agents(size=50, position=pos)
            for player in free_agents[:15]:  # Top 15 per position
                data['available_players'][pos].append(
                    get_player_full_data(player, league, nfl_schedule, game_details)
                )
            
            # Calculate scarcity for this position
            data['positional_scarcity'][pos] = analyze_positional_scarcity(league, pos)
        except Exception as e:
            print(f"Error fetching {pos} free agents: {e}")
    
    # Next week preview
    next_week = current_week + 1
    if next_week <= league.settings.reg_season_count:
        next_schedule, next_game_details = fetch_nfl_schedule(next_week, YEAR)
        
        bye_players = []
        for player in my_team.roster:
            team_abbrev = ESPN_TO_STANDARD.get(player.proTeam, player.proTeam)
            if next_schedule.get(team_abbrev) == 'BYE':
                bye_players.append({
                    'name': player.name,
                    'position': player.position,
                    'lineup_slot': player.lineupSlot,
                    'avg_points': round(player.avg_points, 2),
                })
        
        try:
            next_opponent = my_team.schedule[next_week - 1]
            data['next_week_preview'] = {
                'week': next_week,
                'opponent': next_opponent.team_name if next_opponent else 'BYE',
                'bye_players': bye_players,
                'schedule': next_schedule,
            }
        except:
            data['next_week_preview'] = {'week': next_week, 'status': 'Unable to load'}
    
    return data

def main():
    try:
        print("="*80)
        print("ESPN FANTASY FOOTBALL - COMPREHENSIVE JSON EXTRACTION")
        print("="*80)
        
        league = connect_to_league()
        my_team = find_my_team(league)
        
        print(f"â Connected to {league.settings.name}")
        print(f"â Found team: {my_team.team_name}")
        print(f"â Current week: {league.current_week}")
        
        data = generate_comprehensive_json(league, my_team)
        
        filename = "fantasy-data.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\nâ JSON data saved to {filename}")
        print(f"â File size: {os.path.getsize(filename) / 1024:.2f} KB")
        print(f"â Extracted {len(data['all_teams'])} teams")
        print(f"â Total players in dataset: {sum(len(data['available_players'][pos]) for pos in data['available_players'])}")
        
        # Also create a minified version for web serving
        filename_min = "fantasy-data.min.json"
        with open(filename_min, 'w', encoding='utf-8') as f:
            json.dump(data, f, separators=(',', ':'), ensure_ascii=False)
        
        print(f"â Minified version saved to {filename_min}")
        print(f"â Minified size: {os.path.getsize(filename_min) / 1024:.2f} KB")
        
        print("\n" + "="*80)
        print("SUCCESS! Comprehensive data extraction complete.")
        print("Upload this JSON to your GitHub.io endpoint!")
        print("="*80)
        
    except Exception as e:
        print(f"\nâ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
