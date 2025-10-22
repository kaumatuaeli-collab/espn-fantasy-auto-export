#!/usr/bin/env python3
"""
ESPN Fantasy Football Data Extractor - JSON OUTPUT for GitHub Pages
Extracts data and saves to JSON file accessible via public URL
"""

from espn_api.football import League
import os
from datetime import datetime
import requests
import json

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

def fetch_nfl_schedule(week, year=2025):
    """Fetch NFL schedule from ESPN's public API"""
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={year}&seasontype=2&week={week}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        schedule = {}
        
        if 'events' in data:
            for event in data['events']:
                if 'competitions' in event and len(event['competitions']) > 0:
                    comp = event['competitions'][0]
                    if 'competitors' in comp:
                        home_team = None
                        away_team = None
                        
                        for competitor in comp['competitors']:
                            team_abbrev = competitor['team'].get('abbreviation', '')
                            is_home = competitor.get('homeAway') == 'home'
                            
                            if is_home:
                                home_team = team_abbrev
                            else:
                                away_team = team_abbrev
                        
                        if home_team and away_team:
                            schedule[home_team] = f'vs {away_team}'
                            schedule[away_team] = f'@{home_team}'
        
        all_teams = set(ESPN_TO_STANDARD.values())
        for team in all_teams:
            if team not in schedule:
                schedule[team] = 'BYE'
        
        return schedule
        
    except Exception as e:
        print(f"Warning: Could not fetch NFL schedule: {e}")
        return {}

def get_injury_status_display(status):
    """Get human-readable injury status"""
    if isinstance(status, list):
        if not status:
            status = 'ACTIVE'
        else:
            status = status[0]
    
    status_map = {
        'ACTIVE': 'Healthy',
        'QUESTIONABLE': 'Questionable',
        'DOUBTFUL': 'Doubtful', 
        'OUT': 'Out',
        'INJURY_RESERVE': 'IR',
        'IR': 'IR',
        'SUSPENSION': 'Suspended',
        'DAY_TO_DAY': 'Day-to-Day',
    }
    return status_map.get(status, str(status))

def get_player_dict(player, league, nfl_schedule):
    """Convert player object to dictionary"""
    week = league.current_week
    
    # Handle injury status
    injury_status = player.injuryStatus if hasattr(player, 'injuryStatus') else 'ACTIVE'
    if isinstance(injury_status, list):
        injury_status = injury_status[0] if injury_status else 'ACTIVE'
    
    # Get opponent from schedule
    team_abbrev = ESPN_TO_STANDARD.get(player.proTeam, player.proTeam)
    opponent = nfl_schedule.get(team_abbrev, 'vs OPP')
    
    # Get projections
    projected = 0
    if hasattr(player, 'stats') and isinstance(player.stats, dict):
        current_week_stats = player.stats.get(week, {})
        if isinstance(current_week_stats, dict):
            projected = current_week_stats.get('projected_points', 0)
            proj_breakdown = current_week_stats.get('projected_breakdown', {})
            if not proj_breakdown:
                opponent = 'BYE'
    
    # Get last week points
    last_week_points = 0
    if hasattr(player, 'stats') and isinstance(player.stats, dict):
        available_weeks = [w for w in player.stats.keys() if w > 0]
        if available_weeks:
            most_recent_week = max(available_weeks)
            recent_week_data = player.stats.get(most_recent_week, {})
            last_week_points = recent_week_data.get('points', 0) if isinstance(recent_week_data, dict) else 0
    
    return {
        'name': player.name,
        'position': player.position,
        'slot': player.lineupSlot,
        'pro_team': player.proTeam,
        'injury_status': injury_status,
        'injury_display': get_injury_status_display(injury_status),
        'opponent': opponent,
        'projected': round(projected, 1),
        'avg_points': round(player.avg_points, 1),
        'total_points': round(player.total_points, 1),
        'last_week_points': round(last_week_points, 1),
        'percent_owned': round(player.percent_owned, 0),
        'percent_started': round(player.percent_started, 0),
    }

def main():
    try:
        print("="*80)
        print("ESPN FANTASY FOOTBALL - JSON EXPORT FOR GITHUB PAGES")
        print("="*80)
        
        # Connect to league
        league = League(
            league_id=LEAGUE_ID,
            year=YEAR,
            espn_s2=ESPN_S2,
            swid=SWID
        )
        
        # Find my team
        my_team = None
        for team in league.teams:
            if team.team_name == MY_TEAM_NAME:
                my_team = team
                break
        
        if not my_team:
            raise ValueError(f"Could not find team: {MY_TEAM_NAME}")
        
        week = league.current_week
        nfl_schedule = fetch_nfl_schedule(week, YEAR)
        
        print(f"✓ Connected to {league.settings.name}")
        print(f"✓ Found team: {my_team.team_name}")
        print(f"✓ Current week: {week}")
        print(f"✓ Generating JSON data...")
        
        # Build complete data structure
        data = {
            'generated_at': datetime.now().isoformat(),
            'league': {
                'name': league.settings.name,
                'current_week': week,
                'total_weeks': league.settings.reg_season_count
            },
            'my_team': {
                'name': my_team.team_name,
                'wins': my_team.wins,
                'losses': my_team.losses,
                'standing': my_team.standing,
                'points_for': round(my_team.points_for, 2),
                'points_against': round(my_team.points_against, 2),
                'avg_per_week': round(my_team.points_for / max(1, my_team.wins + my_team.losses), 2)
            },
            'roster': [],
            'matchup': None,
            'standings': [],
            'available_players': {
                'QB': [],
                'RB': [],
                'WR': [],
                'TE': [],
                'K': [],
                'D/ST': []
            }
        }
        
        # My roster
        roster_sorted = sorted(my_team.roster, key=lambda p: (p.lineupSlot == 'BE', p.lineupSlot))
        for player in roster_sorted:
            data['roster'].append(get_player_dict(player, league, nfl_schedule))
        
        # Current matchup
        try:
            opponent = my_team.schedule[week - 1]
            if opponent:
                data['matchup'] = {
                    'opponent_name': opponent.team_name,
                    'opponent_record': f"{opponent.wins}-{opponent.losses}",
                    'opponent_standing': opponent.standing,
                    'opponent_avg': round(opponent.points_for / max(1, opponent.wins + opponent.losses), 2),
                    'opponent_total': round(opponent.points_for, 2)
                }
        except:
            data['matchup'] = {'status': 'BYE WEEK'}
        
        # League standings
        sorted_teams = sorted(league.teams, key=lambda x: x.standing)
        for team in sorted_teams:
            data['standings'].append({
                'rank': team.standing,
                'name': team.team_name,
                'wins': team.wins,
                'losses': team.losses,
                'points_for': round(team.points_for, 2),
                'points_against': round(team.points_against, 2),
                'avg_per_week': round(team.points_for / max(1, team.wins + team.losses), 2),
                'is_me': team.team_id == my_team.team_id
            })
        
        # Top available players by position
        try:
            free_agents = league.free_agents(size=100)
            
            for pos in ['QB', 'RB', 'WR', 'TE', 'K', 'D/ST']:
                pos_players = [p for p in free_agents if p.position == pos]
                
                # Sort by projected points
                def get_proj(p):
                    if hasattr(p, 'stats') and isinstance(p.stats, dict):
                        return p.stats.get(week, {}).get('projected_points', 0)
                    return 0
                
                pos_players.sort(key=get_proj, reverse=True)
                
                for player in pos_players[:15]:  # Top 15 per position
                    data['available_players'][pos].append(get_player_dict(player, league, nfl_schedule))
        except Exception as e:
            print(f"Warning: Could not fetch available players: {e}")
        
        # Create output directory
        os.makedirs('output', exist_ok=True)
        
        # Save JSON file
        output_file = 'output/fantasy-data.json'
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✓ JSON saved to {output_file}")
        print(f"✓ Data includes:")
        print(f"  - {len(data['roster'])} players on your roster")
        print(f"  - {len(data['standings'])} teams in standings")
        print(f"  - Top available players by position")
        
        print("\n" + "="*80)
        print("SUCCESS! JSON file ready for GitHub Pages")
        print("="*80)
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
