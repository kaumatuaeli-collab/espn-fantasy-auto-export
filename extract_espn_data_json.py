#!/usr/bin/env python3
"""
ESPN Fantasy Football OPTIMIZED JSON Data Extractor v4
Updates:
- Force fresh data from ESPN (no Week 8 cache)
- Expand historical data (10 weeks instead of 3)
- Add full season history for time-decay calculations
- Better debugging output
"""

import json
import os
from datetime import datetime
from collections import defaultdict
import requests
from espn_api.football import League
import time

# Cache for NFL schedule to avoid duplicate API calls
schedule_cache = {}

# ESPN Configuration
LEAGUE_ID = 44181678
YEAR = 2025
ESPN_S2 = os.environ.get('ESPN_S2')
SWID = os.environ.get('SWID')
MY_TEAM_NAME = 'Intelligent MBLeague (TM)'

# Configuration for smart data reduction
WEEKS_OF_HISTORY = 10  # Increased from 3 to 10
TOP_AVAILABLE_PER_POSITION = 15

# Position-aware relevance filters
POSITION_FILTERS = {
    'QB': {'min_proj': 12.0, 'min_owned': 15.0, 'min_avg': 10.0},
    'RB': {'min_proj': 4.0, 'min_owned': 15.0, 'min_avg': 3.5},
    'WR': {'min_proj': 5.0, 'min_owned': 20.0, 'min_avg': 4.0},
    'TE': {'min_proj': 5.0, 'min_owned': 20.0, 'min_avg': 4.0},
    'K': {'min_proj': 6.0, 'min_owned': 10.0, 'min_avg': 5.0},
    'D/ST': {'min_proj': 6.0, 'min_owned': 10.0, 'min_avg': 5.0},
}

INCLUDE_INJURED_STASHES = True
SHOW_FULL_OPPONENT_ROSTERS = True

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
    """Connect to ESPN Fantasy League with debugging"""
    print(f"\n🔌 Connecting to league {LEAGUE_ID}...")
    
    league = League(
        league_id=LEAGUE_ID,
        year=YEAR,
        espn_s2=ESPN_S2,
        swid=SWID
    )
    
    # Debug output
    print(f"✅ Connected successfully!")
    print(f"   📊 League: {league.settings.name}")
    print(f"   📅 ESPN Current Week: {league.current_week}")
    print(f"   🏁 Regular Season: {league.settings.reg_season_count} weeks")
    
    # Warning if data seems stale
    if league.current_week <= 8:
        print(f"\n⚠️  WARNING: ESPN reports Week {league.current_week}")
        print(f"⚠️  This may be outdated (expected Week 11+)")
    
    return league

def find_my_team(league):
    """Find user's team in the league"""
    for team in league.teams:
        if team.team_name == MY_TEAM_NAME:
            return team
    raise ValueError(f"Could not find team '{MY_TEAM_NAME}'")

def fetch_nfl_schedule_enhanced(week, year=2025):
    """Fetch NFL schedule with game timing, implied points, and context flags"""
    key = f"{year}_{week}"
    if key in schedule_cache:
        print(f"   📅 NFL schedule Week {week} (cached)")
        return schedule_cache[key]
    
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={year}&seasontype=2&week={week}"
        print(f"   📅 Fetching NFL schedule Week {week}...")
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        schedule = {}
        game_details = {}
        
        if 'events' in data:
            for event in data['events']:
                if 'competitions' in event and len(event['competitions']) > 0:
                    comp = event['competitions'][0]
                    game_date = event.get('date', '')
                    
                    is_tnf = False
                    is_mnf = False
                    is_snf = False
                    
                    if game_date:
                        try:
                            dt = datetime.fromisoformat(game_date.replace('Z', '+00:00'))
                            day_of_week = dt.strftime('%A')
                            hour = dt.hour
                            
                            is_tnf = day_of_week == 'Thursday'
                            is_mnf = day_of_week == 'Monday'
                            is_snf = day_of_week == 'Sunday' and hour >= 20
                        except:
                            pass
                    
                    game_info = {
                        'kickoff': game_date,
                        'status': comp.get('status', {}).get('type', {}).get('description', 'Scheduled'),
                        'is_tnf': is_tnf,
                        'is_mnf': is_mnf,
                        'is_snf': is_snf,
                    }
                    
                    spread = None
                    total = None
                    favored_team = None
                    
                    if comp.get('odds') and len(comp['odds']) > 0:
                        odds = comp['odds'][0]
                        spread_str = odds.get('details', '')
                        total = odds.get('overUnder', None)
                        
                        if spread_str and total:
                            try:
                                parts = spread_str.split()
                                if len(parts) >= 2:
                                    favored_team = parts[0]
                                    spread = float(parts[1])
                            except:
                                pass
                    
                    game_info['spread'] = spread
                    game_info['total'] = total
                    
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
                            
                            home_implied = None
                            away_implied = None
                            
                            if spread is not None and total is not None:
                                if favored_team == home_team:
                                    home_implied = round((total + abs(spread)) / 2, 1)
                                    away_implied = round((total - abs(spread)) / 2, 1)
                                elif favored_team == away_team:
                                    away_implied = round((total + abs(spread)) / 2, 1)
                                    home_implied = round((total - abs(spread)) / 2, 1)
                            
                            home_info = game_info.copy()
                            home_info['home'] = True
                            home_info['opp'] = away_team
                            home_info['implied_pts'] = home_implied
                            
                            away_info = game_info.copy()
                            away_info['home'] = False
                            away_info['opp'] = home_team
                            away_info['implied_pts'] = away_implied
                            
                            game_details[home_team] = home_info
                            game_details[away_team] = away_info
        
        all_teams = set(ESPN_TO_STANDARD.values())
        for team in all_teams:
            if team not in schedule:
                schedule[team] = 'BYE'
                game_details[team] = {'status': 'BYE'}
        
        print(f"      ✓ Found {len([v for v in schedule.values() if v != 'BYE'])} games")
        schedule_cache[key] = (schedule, game_details)
        return schedule, game_details
        
    except Exception as e:
        print(f"      ⚠️  Could not fetch NFL schedule: {e}")
        return {}, {}

def get_compact_eligibility(player):
    """Get compact eligibility slots"""
    eligible = []
    slot_map = {
        0: 'QB', 2: 'RB', 4: 'WR', 6: 'TE', 16: 'D/ST', 17: 'K',
        23: 'FLEX',
    }
    
    if hasattr(player, 'eligibleSlots'):
        for slot_id in player.eligibleSlots:
            if slot_id in slot_map:
                slot_name = slot_map[slot_id]
                if slot_name not in eligible:
                    eligible.append(slot_name)
    
    if not eligible and hasattr(player, 'position'):
        eligible = [player.position]
    
    return eligible

def get_recent_weekly_stats(player, current_week, weeks_back=WEEKS_OF_HISTORY):
    """Extract recent weekly performance - UPDATED to include more weeks"""
    weekly_points = []
    
    if not hasattr(player, 'stats') or not isinstance(player.stats, dict):
        return weekly_points
    
    start_week = max(1, current_week - weeks_back)
    
    for week in range(start_week, current_week + 1):
        week_stats = player.stats.get(week, {})
        if isinstance(week_stats, dict):
            points = week_stats.get('points', 0)
            if points is not None:  # Include zeros (player played but scored 0)
                weekly_points.append(round(points, 2))
    
    # Reverse so most recent is first (for EWMA)
    weekly_points.reverse()
    
    return weekly_points

def get_full_season_stats(player, current_week):
    """Get ALL games from entire season for time-decay calculations"""
    all_games = []
    
    if not hasattr(player, 'stats') or not isinstance(player.stats, dict):
        return all_games
    
    for week in range(1, current_week + 1):
        week_stats = player.stats.get(week, {})
        if isinstance(week_stats, dict):
            points = week_stats.get('points', 0)
            if points is not None and points > 0:
                all_games.append(round(points, 2))
    
    # Most recent first
    all_games.reverse()
    
    return all_games

def calculate_boom_bust_metrics(weekly_points):
    """Calculate boom/bust rates and consistency metrics"""
    if not weekly_points or len(weekly_points) == 0:
        return {}
    
    import statistics
    
    avg = statistics.mean(weekly_points)
    boom_threshold = avg * 1.2
    bust_threshold = avg * 0.6
    
    boom_weeks = sum(1 for p in weekly_points if p >= boom_threshold)
    bust_weeks = sum(1 for p in weekly_points if p <= bust_threshold)
    
    metrics = {
        'stdev': round(statistics.stdev(weekly_points), 2) if len(weekly_points) > 1 else 0,
        'boom': round(boom_weeks / len(weekly_points), 2),
        'bust': round(bust_weeks / len(weekly_points), 2),
    }
    
    return metrics

def get_player_data(player, league, nfl_schedule, game_details, include_history=False, minimal=False):
    """Extract player data with configurable detail level"""
    week = league.current_week
    
    injury_status = player.injuryStatus if hasattr(player, 'injuryStatus') else 'ACTIVE'
    if isinstance(injury_status, list):
        injury_status = injury_status[0] if injury_status else 'ACTIVE'
    
    pro_team = ESPN_TO_STANDARD.get(player.proTeam, player.proTeam)
    opponent_display = nfl_schedule.get(pro_team, 'BYE')
    
    current_week_stats = player.stats.get(week, {}) if hasattr(player, 'stats') else {}
    projected = current_week_stats.get('projected_points', 0) if isinstance(current_week_stats, dict) else 0
    
    game_info = game_details.get(pro_team, {})
    
    player_data = {
        'id': getattr(player, 'playerId', None),
        'name': player.name,
        'pos': player.position,
        'team': pro_team,
        'slot': getattr(player, 'lineupSlot', None),
        'inj': injury_status,
        'bye': opponent_display == 'BYE',
        'proj': round(projected, 2),
        'avg': round(player.avg_points, 2),
        'total': round(player.total_points, 2),
    }
    
    if not minimal:
        player_data['elig'] = get_compact_eligibility(player)
    
    if not minimal:
        player_data['own'] = round(player.percent_owned, 1)
        player_data['start'] = round(player.percent_started, 1)
    
    if not minimal and game_info.get('status') != 'BYE':
        player_data['opp'] = game_info.get('opp', opponent_display)
        player_data['kickoff'] = game_info.get('kickoff', '')
        player_data['home'] = game_info.get('home', None)
        
        if game_info.get('is_tnf'):
            player_data['is_tnf'] = True
        if game_info.get('is_mnf'):
            player_data['is_mnf'] = True
        if game_info.get('is_snf'):
            player_data['is_snf'] = True
        
        if game_info.get('implied_pts'):
            player_data['implied_pts'] = game_info['implied_pts']
    
    # UPDATED: Add both recent and full season history
    if include_history:
        weekly_points = get_recent_weekly_stats(player, week, weeks_back=3)
        all_season = get_full_season_stats(player, week)
        
        if weekly_points:
            player_data['last_n'] = weekly_points
            metrics = calculate_boom_bust_metrics(weekly_points)
            player_data.update(metrics)
        
        if all_season:
            player_data['all_game_history'] = all_season
    
    return player_data

def is_player_relevant_for_waivers(player, position, league, game_details):
    """Check if FA is relevant using position-aware filters"""
    filters = POSITION_FILTERS.get(position, {'min_proj': 5.0, 'min_owned': 20.0, 'min_avg': 4.0})
    
    current_week = league.current_week
    current_week_stats = player.stats.get(current_week, {}) if hasattr(player, 'stats') else {}
    projected = current_week_stats.get('projected_points', 0) if isinstance(current_week_stats, dict) else 0
    
    injury_status = player.injuryStatus if hasattr(player, 'injuryStatus') else 'ACTIVE'
    if isinstance(injury_status, list):
        injury_status = injury_status[0] if injury_status else 'ACTIVE'
    
    is_injured = injury_status in ['OUT', 'IR', 'INJURY_RESERVE', 'QUESTIONABLE', 'DOUBTFUL']
    
    if INCLUDE_INJURED_STASHES and is_injured and player.percent_owned > 10:
        return True
    
    passes_projection = projected >= filters['min_proj']
    passes_ownership = player.percent_owned >= filters['min_owned']
    passes_avg = player.avg_points >= filters['min_avg']
    
    if position in ['D/ST', 'K']:
        pro_team = ESPN_TO_STANDARD.get(player.proTeam, player.proTeam)
        game_info = game_details.get(pro_team, {})
        opp_team = game_info.get('opp')
        if opp_team:
            opp_game_info = game_details.get(opp_team, {})
            opp_implied = opp_game_info.get('implied_pts', 999)
            if opp_implied and opp_implied <= 20.5:
                return True
    
    return passes_projection or passes_ownership or passes_avg

def analyze_positional_depth(roster):
    """Analyze roster depth by position"""
    positions = defaultdict(list)
    
    for player in roster:
        if player.lineupSlot != 'IR':
            positions[player.position].append({
                'name': player.name,
                'avg': round(player.avg_points, 2),
                'slot': player.lineupSlot,
            })
    
    depth = {}
    for pos, players in positions.items():
        starters = len([p for p in players if p['slot'] != 'BE'])
        bench = len([p for p in players if p['slot'] == 'BE'])
        
        depth[pos] = {
            'total': len(players),
            'start': starters,
            'bench': bench,
        }
    
    return depth

def get_schedule_lookahead(team, league, weeks_ahead=3):
    """Get next N weeks opponents with game context"""
    current_week = league.current_week
    upcoming = []
    
    try:
        for i in range(weeks_ahead):
            check_week = current_week + i
            if check_week >= len(team.schedule):
                break
            
            schedule, game_details = fetch_nfl_schedule_enhanced(check_week + 1, YEAR)
            
            opponent = team.schedule[check_week]
            if opponent:
                opp_avg = opponent.points_for / max(1, opponent.wins + opponent.losses)
                upcoming.append({
                    'week': check_week + 1,
                    'opp': opponent.team_name,
                    'opp_avg': round(opp_avg, 2),
                    'difficulty': 'Hard' if opp_avg > 100 else 'Med' if opp_avg > 85 else 'Easy',
                })
    except:
        pass
    
    return upcoming

def identify_trade_opportunities(league, my_team):
    """Find teams with surplus at positions where you're weak"""
    my_depth = analyze_positional_depth(my_team.roster)
    weak_positions = [pos for pos, info in my_depth.items() 
                      if info['total'] < 2 and pos not in ['K', 'D/ST']]
    
    opportunities = []
    
    for team in league.teams:
        if team.team_id == my_team.team_id:
            continue
        
        team_depth = analyze_positional_depth(team.roster)
        
        for weak_pos in weak_positions:
            if team_depth.get(weak_pos, {}).get('total', 0) >= 3:
                opportunities.append({
                    'team': team.team_name,
                    'record': f"{team.wins}-{team.losses}",
                    'pos': weak_pos,
                    'their_depth': team_depth[weak_pos]['total'],
                })
    
    return opportunities

def generate_optimized_json(league, my_team):
    """Generate optimized JSON with smart filtering"""
    print("\n📊 Generating optimized JSON...")
    
    current_week = league.current_week
    nfl_schedule, game_details = fetch_nfl_schedule_enhanced(current_week, YEAR)
    
    data = {
        'meta': {
            'generated': datetime.now().isoformat(),
            'league': LEAGUE_ID,
            'year': YEAR,
            'week': current_week,
            'version': 'v4_expanded_history',
        },
        
        'league': {
            'name': league.settings.name,
            'teams': len(league.teams),
            'reg_weeks': league.settings.reg_season_count,
            'playoff_teams': league.settings.playoff_team_count,
        },
        
        'my_team': {
            'name': my_team.team_name,
            'record': f"{my_team.wins}-{my_team.losses}",
            'standing': my_team.standing,
            'pf': round(my_team.points_for, 2),
            'pa': round(my_team.points_against, 2),
            'avg': round(my_team.points_for / max(1, my_team.wins + my_team.losses), 2),
            'depth': analyze_positional_depth(my_team.roster),
            'schedule': get_schedule_lookahead(my_team, league),
        },
        
        'matchup': {},
        'roster': [],
        'opponents': [],
        'waivers': {},
        'trades': [],
        'byes': {},
    }
    
    try:
        opponent = my_team.schedule[current_week - 1]
        if opponent:
            data['matchup'] = {
                'week': current_week,
                'opp': opponent.team_name,
                'opp_record': f"{opponent.wins}-{opponent.losses}",
                'opp_avg': round(opponent.points_for / max(1, opponent.wins + opponent.losses), 2),
            }
    except:
        data['matchup'] = {'week': current_week, 'bye': True}
    
    print("   🏈 Processing my roster...")
    for player in my_team.roster:
        data['roster'].append(
            get_player_data(player, league, nfl_schedule, game_details, 
                          include_history=True, minimal=False)
        )
    
    print("   👥 Processing opponent rosters...")
    for team in sorted(league.teams, key=lambda x: x.standing):
        if team.team_id == my_team.team_id:
            continue
        
        if SHOW_FULL_OPPONENT_ROSTERS:
            team_data = {
                'name': team.team_name,
                'record': f"{team.wins}-{team.losses}",
                'avg': round(team.points_for / max(1, team.wins + team.losses), 2),
                'depth': analyze_positional_depth(team.roster),
                'roster': [
                    get_player_data(p, league, nfl_schedule, game_details, 
                                  include_history=False, minimal=True)
                    for p in team.roster
                ],
            }
        else:
            team_data = {
                'name': team.team_name,
                'record': f"{team.wins}-{team.losses}",
                'depth': analyze_positional_depth(team.roster),
            }
        
        data['opponents'].append(team_data)
    
    print("   📋 Processing waiver targets...")
    for pos in ['QB', 'RB', 'WR', 'TE', 'K', 'D/ST']:
        data['waivers'][pos] = []
        try:
            free_agents = league.free_agents(size=50, position=pos)
            
            relevant = []
            for player in free_agents:
                if is_player_relevant_for_waivers(player, pos, league, game_details):
                    relevant.append(player)
                    
                    if len(relevant) >= TOP_AVAILABLE_PER_POSITION:
                        break
            
            data['waivers'][pos] = [
                get_player_data(p, league, nfl_schedule, game_details,
                              include_history=False, minimal=False)
                for p in relevant
            ]
            
        except Exception as e:
            print(f"      ⚠️  Error fetching {pos}: {e}")
    
    print("   💼 Identifying trade opportunities...")
    data['trades'] = identify_trade_opportunities(league, my_team)
    
    print("   🚫 Checking upcoming bye weeks...")
    for week_ahead in [1, 2]:
        check_week = current_week + week_ahead
        if check_week <= league.settings.reg_season_count:
            future_schedule, _ = fetch_nfl_schedule_enhanced(check_week, YEAR)
            
            bye_players = []
            for player in my_team.roster:
                team_abbrev = ESPN_TO_STANDARD.get(player.proTeam, player.proTeam)
                if future_schedule.get(team_abbrev) == 'BYE':
                    bye_players.append({
                        'name': player.name,
                        'pos': player.position,
                        'slot': player.lineupSlot,
                        'starter': player.lineupSlot != 'BE',
                    })
            
            if bye_players:
                data['byes'][f'w{check_week}'] = bye_players
    
    return data

def main():
    try:
        print("="*70)
        print("ESPN FANTASY FOOTBALL - DATA EXTRACTION v4")
        print("Expanded History • Fresh Data • Better Debugging")
        print("="*70)
        
        # Log current time for debugging
        current_time = datetime.now()
        print(f"\n🕐 Extraction Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📅 Date: {current_time.date()}")
        
        # Small delay to ensure fresh API data
        print("⏳ Waiting 2 seconds for API freshness...")
        time.sleep(2)
        
        league = connect_to_league()
        my_team = find_my_team(league)
        
        print(f"✅ Found: {my_team.team_name}")
        print(f"📊 Record: {my_team.wins}-{my_team.losses} (#{my_team.standing})")
        
        data = generate_optimized_json(league, my_team)
        
        # Save with simplified filename
        filename = "fantasy-data.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        size_kb = os.path.getsize(filename) / 1024
        
        print(f"\n{'='*70}")
        print(f"✅ SUCCESS!")
        print(f"{'='*70}")
        print(f"📁 File: {filename} ({size_kb:.1f} KB)")
        print(f"📊 Week: {data['meta']['week']}")
        print(f"🏈 Roster Players: {len(data['roster'])}")
        print(f"📋 Waiver Players: {sum(len(v) for v in data['waivers'].values())}")
        print(f"{'='*70}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
