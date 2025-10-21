#!/usr/bin/env python3
"""
ESPN Fantasy Football Data Extractor - COMPLETE STRATEGIC VERSION
Full extraction with all league rosters, free agents, injury tracking, and trade analysis
"""

from espn_api.football import League
import os
from datetime import datetime
import requests

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
    """Fetch NFL schedule from ESPN's public API"""
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={year}&seasontype=2&week={week}"
        print(f"Fetching NFL schedule for week {week}...")
        
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
        
        print(f"â Found {len([v for v in schedule.values() if v != 'BYE'])} games scheduled")
        return schedule
        
    except Exception as e:
        print(f"Warning: Could not fetch NFL schedule: {e}")
        return {}

def get_injury_status_display(status):
    """Get human-readable injury status with expected return info"""
    # Handle case where status is a list (ESPN sometimes returns lists)
    if isinstance(status, list):
        if not status:
            status = 'ACTIVE'
        else:
            status = status[0]  # Take first status if list
    
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

def get_recent_weeks_with_calculation(player, current_week):
    """
    ESPN only stores 1-2 recent weeks. Calculate older weeks from season total.
    Returns: tuple of (last_3_display_string, has_reliable_data: bool)
    """
    if not hasattr(player, 'stats') or not isinstance(player.stats, dict):
        return "No data", False
    
    available_weeks = [w for w in player.stats.keys() if w > 0]
    
    if not available_weeks:
        return "No data", False
    
    most_recent_week = max(available_weeks)
    recent_week_data = player.stats.get(most_recent_week, {})
    recent_score = recent_week_data.get('points', 0) if isinstance(recent_week_data, dict) else 0
    
    season_data = player.stats.get(0, {})
    season_total = season_data.get('points', player.total_points) if isinstance(season_data, dict) else player.total_points
    
    previous_weeks_combined = season_total - recent_score
    
    if current_week == most_recent_week:
        return f"Wks 1-{current_week-1}: {previous_weeks_combined:.1f} | Wk {current_week}: {recent_score:.1f} (live)", True
    else:
        return f"Wks 1-{most_recent_week-1}: {previous_weeks_combined:.1f} | Wk {most_recent_week}: {recent_score:.1f}", True

def get_player_details(player, league, nfl_schedule):
    """Extract comprehensive player details"""
    week = league.current_week
    
    # Handle injury status - can be string or list
    injury_status = player.injuryStatus if hasattr(player, 'injuryStatus') else 'ACTIVE'
    if isinstance(injury_status, list):
        injury_status = injury_status[0] if injury_status else 'ACTIVE'
    
    details = {
        'name': player.name,
        'position': player.position,
        'slot': player.lineupSlot,
        'pro_team': player.proTeam,
        'injury_status': injury_status,
        'injury_display': get_injury_status_display(injury_status),
        'percent_owned': player.percent_owned,
        'percent_started': player.percent_started,
        'total_points': player.total_points,
        'avg_points': player.avg_points,
    }
    
    team_abbrev = ESPN_TO_STANDARD.get(player.proTeam, player.proTeam)
    details['opponent'] = nfl_schedule.get(team_abbrev, 'vs OPP')
    
    details['projected'] = 0
    
    if hasattr(player, 'stats') and isinstance(player.stats, dict):
        current_week_stats = player.stats.get(week, {})
        if isinstance(current_week_stats, dict):
            details['projected'] = current_week_stats.get('projected_points', 0)
            proj_breakdown = current_week_stats.get('projected_breakdown', {})
            if not proj_breakdown:
                details['opponent'] = 'BYE'
    
    details['recent_weeks_display'], details['has_reliable_data'] = get_recent_weeks_with_calculation(player, week)
    
    return details

def get_injury_color(status):
    """Get color coding for injury status"""
    if status == 'OUT':
        return '#ffcdd2'
    elif status in ['QUESTIONABLE', 'DOUBTFUL', 'DAY_TO_DAY']:
        return '#fff9c4'
    elif status in ['INJURY_RESERVE', 'IR', 'SUSPENSION']:
        return '#e1bee7'
    return '#ffffff'

def get_top_available_players(league, nfl_schedule, position=None, limit=15, sort_by='projected'):
    """Get top available free agents"""
    try:
        week = league.current_week
        free_agents = league.free_agents(size=100)
        
        if position:
            free_agents = [p for p in free_agents if p.position == position]
        
        if sort_by == 'projected':
            def get_proj(p):
                if hasattr(p, 'stats') and isinstance(p.stats, dict):
                    return p.stats.get(week, {}).get('projected_points', 0)
                return 0
            free_agents.sort(key=get_proj, reverse=True)
        elif sort_by == 'avg':
            free_agents.sort(key=lambda x: x.avg_points, reverse=True)
        elif sort_by == 'owned':
            free_agents.sort(key=lambda x: x.percent_owned, reverse=True)
        elif sort_by == 'started':
            free_agents.sort(key=lambda x: x.percent_started, reverse=True)
        
        return free_agents[:limit]
    except Exception as e:
        print(f"Error fetching free agents: {e}")
        return []

def generate_html_report(league, my_team):
    """Generate comprehensive HTML report"""
    
    current_time = datetime.now().strftime('%Y-%m-%d %I:%M %p ET')
    week = league.current_week
    
    nfl_schedule = fetch_nfl_schedule(week, YEAR)
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fantasy Football Report - Week {week}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
            line-height: 1.6;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .header h1 {{ margin: 0 0 10px 0; }}
        .summary {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            margin-top: 0;
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        .section h3 {{
            color: #764ba2;
            margin-top: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            font-size: 14px;
        }}
        th {{
            background-color: #667eea;
            color: white;
            padding: 12px 8px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 10px 8px;
            border-bottom: 1px solid #e0e0e0;
        }}
        tr:hover {{ background-color: #f8f9fa; }}
        .starter {{ font-weight: bold; background-color: #e3f2fd; }}
        .bench {{ color: #666; }}
        .stat-box {{
            display: inline-block;
            padding: 8px 15px;
            margin: 5px;
            border-radius: 5px;
            background-color: #e3f2fd;
            font-weight: 600;
        }}
        .alert {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 15px 0;
        }}
        .info-box {{
            background-color: #e3f2fd;
            border-left: 4px solid #2196F3;
            padding: 15px;
            margin: 15px 0;
            font-size: 13px;
        }}
        @media (max-width: 768px) {{
            body {{ padding: 10px; }}
            table {{ font-size: 12px; }}
            th, td {{ padding: 6px 4px; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{league.settings.name}</h1>
        <div>Week {week} of {league.settings.reg_season_count} | {current_time}</div>
        <div style="margin-top: 10px; font-size: 18px;">{my_team.team_name}</div>
    </div>
    
    <div class="info-box">
        <strong>Note:</strong> ESPN's API only stores 1-2 recent weeks of detailed stats. 
        "Recent Weeks" shows the most recent available week data, plus a combined total for all previous weeks.
    </div>
    
    <div class="summary">
        <h2>Quick Stats</h2>
        <div class="stat-box">Record: {my_team.wins}-{my_team.losses}</div>
        <div class="stat-box">Standing: #{my_team.standing} of {len(league.teams)}</div>
        <div class="stat-box">Points For: {my_team.points_for:.2f}</div>
        <div class="stat-box">Points Against: {my_team.points_against:.2f}</div>
        <div class="stat-box">Avg Points/Week: {my_team.points_for/max(1, my_team.wins + my_team.losses):.2f}</div>
    </div>
"""
    
    # This week's matchup
    try:
        matchup = my_team.schedule[week - 1]
        if matchup:
            html += f"""
    <div class="section">
        <h2>Week {week} Matchup</h2>
        <h3>{my_team.team_name} vs {matchup.team_name}</h3>
        <div class="stat-box">Opponent Record: {matchup.wins}-{matchup.losses} (#{matchup.standing})</div>
        <div class="stat-box">Their Avg: {matchup.points_for/max(1, matchup.wins + matchup.losses):.2f} pts/wk</div>
        <div class="stat-box">Their Total: {matchup.points_for:.2f} PF</div>
    </div>
"""
    except:
        html += """
    <div class="alert">
        <strong>BYE WEEK</strong> - No matchup this week
    </div>
"""
    
    # My Roster
    html += f"""
    <div class="section">
        <h2>My Roster - Week {week}</h2>
        <table>
            <tr>
                <th>Slot</th>
                <th>Player</th>
                <th>Pos</th>
                <th>Team</th>
                <th>Injury</th>
                <th>Status</th>
                <th>Proj</th>
                <th>Avg</th>
                <th>Total</th>
                <th>Recent Weeks</th>
                <th>Own%</th>
                <th>Start%</th>
            </tr>
"""
    
    roster_sorted = sorted(my_team.roster, key=lambda p: (p.lineupSlot == 'BE', p.lineupSlot))
    
    for player in roster_sorted:
        details = get_player_details(player, league, nfl_schedule)
        
        row_class = 'starter' if details['slot'] != 'BE' else 'bench'
        injury_color = get_injury_color(details['injury_status'])
        
        html += f"""
            <tr class="{row_class}">
                <td><strong>{details['slot']}</strong></td>
                <td><strong>{details['name']}</strong></td>
                <td>{details['position']}</td>
                <td>{details['pro_team']}</td>
                <td style="background-color: {injury_color};">{details['injury_display']}</td>
                <td><strong>{details['opponent']}</strong></td>
                <td><strong>{details['projected']:.1f}</strong></td>
                <td>{details['avg_points']:.1f}</td>
                <td>{details['total_points']:.1f}</td>
                <td style="font-size: 11px;">{details['recent_weeks_display']}</td>
                <td>{details['percent_owned']:.0f}%</td>
                <td>{details['percent_started']:.0f}%</td>
            </tr>
"""
    
    html += """
        </table>
    </div>
"""
    
    # All League Rosters
    html += """
    <div class="section">
        <h2>Complete League Rosters</h2>
        <p style="color: #666; font-size: 13px;">Use this to identify trade targets, see what other teams need, and scout potential waiver pickups before others notice them.</p>
"""
    
    sorted_teams = sorted(league.teams, key=lambda x: x.standing)
    for team in sorted_teams:
        is_my_team = team.team_id == my_team.team_id
        
        html += f"""
        <div style="margin: 20px 0; padding: 15px; background: {'#fff3cd' if is_my_team else '#f8f9fa'}; border-radius: 8px; border-left: 4px solid {'#ffc107' if is_my_team else '#e0e0e0'};">
            <h3>#{team.standing} - {team.team_name} {' &lt;- YOU' if is_my_team else ''}</h3>
            <div class="stat-box">Record: {team.wins}-{team.losses}</div>
            <div class="stat-box">PF: {team.points_for:.2f}</div>
            <div class="stat-box">Avg: {team.points_for/max(1, team.wins + team.losses):.2f}/wk</div>
            
            <table style="margin-top: 10px;">
                <tr>
                    <th>Slot</th>
                    <th>Player</th>
                    <th>Pos</th>
                    <th>Injury</th>
                    <th>Status</th>
                    <th>Proj</th>
                    <th>Avg</th>
                    <th>Total</th>
                    <th>Recent</th>
                </tr>
"""
        
        roster_sorted = sorted(team.roster, key=lambda p: (p.lineupSlot == 'BE', p.lineupSlot))
        
        for player in roster_sorted:
            details = get_player_details(player, league, nfl_schedule)
            row_class = 'starter' if details['slot'] != 'BE' else 'bench'
            injury_color = get_injury_color(details['injury_status'])
            
            html += f"""
                <tr class="{row_class}">
                    <td><strong>{details['slot']}</strong></td>
                    <td><strong>{details['name']}</strong></td>
                    <td>{details['position']}</td>
                    <td style="background-color: {injury_color}; font-size: 10px;">{details['injury_display']}</td>
                    <td style="font-size: 11px;"><strong>{details['opponent']}</strong></td>
                    <td><strong>{details['projected']:.1f}</strong></td>
                    <td>{details['avg_points']:.1f}</td>
                    <td>{details['total_points']:.1f}</td>
                    <td style="font-size: 10px;">{details['recent_weeks_display']}</td>
                </tr>
"""
        
        html += """
            </table>
        </div>
"""
    
    html += """
    </div>
"""
    
    # Top Available Players - Multiple Views
    positions = ['QB', 'RB', 'WR', 'TE', 'K', 'D/ST']
    sort_options = [
        ('projected', 'By Projected Points This Week'),
        ('avg', 'By Season Average'),
        ('owned', 'By Ownership % (Trending)'),
        ('started', 'By Started % (League Value)')
    ]
    
    for sort_key, sort_name in sort_options:
        html += f"""
    <div class="section">
        <h2>Top Available Players - {sort_name}</h2>
        <p style="color: #666; font-size: 13px;">
"""
        
        if sort_key == 'projected':
            html += """Best waiver pickups for this week's matchup. High projections = immediate impact."""
        elif sort_key == 'avg':
            html += """Most consistent performers available. Good for ROS (rest of season) value."""
        elif sort_key == 'owned':
            html += """Trending players gaining attention. Grab them before your league mates do."""
        else:
            html += """Players actually being started in other leagues. Real-world validation of value."""
        
        html += """
        </p>
"""
        
        for pos in positions:
            top_players = get_top_available_players(league, nfl_schedule, position=pos, limit=10, sort_by=sort_key)
            if top_players:
                html += f"""
        <h3>{pos}</h3>
        <table>
            <tr>
                <th>Player</th>
                <th>Team</th>
                <th>Injury</th>
                <th>Status</th>
                <th>Proj</th>
                <th>Avg</th>
                <th>Total</th>
                <th>Own%</th>
                <th>Start%</th>
            </tr>
"""
                
                for player in top_players:
                    details = get_player_details(player, league, nfl_schedule)
                    injury_color = get_injury_color(details['injury_status'])
                    
                    html += f"""
            <tr>
                <td><strong>{details['name']}</strong></td>
                <td>{details['pro_team']}</td>
                <td style="background-color: {injury_color}; font-size: 11px;">{details['injury_display']}</td>
                <td><strong>{details['opponent']}</strong></td>
                <td><strong>{details['projected']:.1f}</strong></td>
                <td>{details['avg_points']:.1f}</td>
                <td>{details['total_points']:.1f}</td>
                <td>{details['percent_owned']:.0f}%</td>
                <td>{details['percent_started']:.0f}%</td>
            </tr>
"""
                
                html += """
        </table>
"""
        
        html += """
    </div>
"""
    
    # League Standings
    html += """
    <div class="section">
        <h2>League Standings</h2>
        <table>
            <tr>
                <th>Rank</th>
                <th>Team</th>
                <th>Record</th>
                <th>PF</th>
                <th>PA</th>
                <th>Avg/Wk</th>
            </tr>
"""
    
    for team in sorted_teams:
        row_class = 'starter' if team.team_id == my_team.team_id else ''
        avg_per_week = team.points_for / max(1, team.wins + team.losses)
        
        html += f"""
            <tr class="{row_class}">
                <td>{team.standing}</td>
                <td><strong>{team.team_name}</strong>{' &lt;- YOU' if team.team_id == my_team.team_id else ''}</td>
                <td>{team.wins}-{team.losses}</td>
                <td>{team.points_for:.2f}</td>
                <td>{team.points_against:.2f}</td>
                <td>{avg_per_week:.2f}</td>
            </tr>
"""
    
    html += """
        </table>
    </div>
"""
    
    # Next Week Preparation - NEW SECTION
    next_week = week + 1
    if next_week <= league.settings.reg_season_count:
        html += f"""
    <div class="section">
        <h2>Week {next_week} Preparation - Your Next Matchup</h2>
"""
        
        next_opponent = my_team.schedule[next_week - 1] if next_week - 1 < len(my_team.schedule) else None
        
        if next_opponent:
            opp_avg = next_opponent.points_for / max(1, next_opponent.wins + next_opponent.losses)
            my_avg = my_team.points_for / max(1, my_team.wins + my_team.losses)
            
            html += f"""
        <h3>vs {next_opponent.team_name}</h3>
        <div class="stat-box">Their Record: {next_opponent.wins}-{next_opponent.losses} (#{next_opponent.standing})</div>
        <div class="stat-box">Their Avg: {opp_avg:.2f} pts/wk</div>
        <div class="stat-box">Your Avg: {my_avg:.2f} pts/wk</div>
        <div class="stat-box">Point Differential: {my_avg - opp_avg:+.2f}</div>
        
        <h3>Your Players on BYE Week {next_week}</h3>
"""
            
            # Check which of your players are on BYE next week
            next_week_schedule = fetch_nfl_schedule(next_week, YEAR)
            bye_players = []
            
            for player in my_team.roster:
                team_abbrev = ESPN_TO_STANDARD.get(player.proTeam, player.proTeam)
                player_status = next_week_schedule.get(team_abbrev, 'UNKNOWN')
                if player_status == 'BYE':
                    bye_players.append(player)
            
            if bye_players:
                html += """
        <div class="alert">
            <strong>WARNING: You have players on BYE next week!</strong>
        </div>
        <table>
            <tr>
                <th>Player</th>
                <th>Position</th>
                <th>Slot</th>
                <th>Team</th>
                <th>Avg Points</th>
                <th>Impact</th>
            </tr>
"""
                
                for player in bye_players:
                    is_starter = player.lineupSlot != 'BE'
                    impact = "MUST REPLACE" if is_starter else "Bench (OK)"
                    impact_color = "#ffcdd2" if is_starter else "#c8e6c9"
                    
                    html += f"""
            <tr>
                <td><strong>{player.name}</strong></td>
                <td>{player.position}</td>
                <td>{player.lineupSlot}</td>
                <td>{player.proTeam}</td>
                <td>{player.avg_points:.1f}</td>
                <td style="background-color: {impact_color};"><strong>{impact}</strong></td>
            </tr>
"""
                
                html += """
        </table>
        <p style="color: #666; margin-top: 10px;">Check the "Top Available Players" sections below to find replacements!</p>
"""
            else:
                html += """
        <div style="background-color: #c8e6c9; padding: 15px; border-radius: 5px; margin: 10px 0;">
            <strong>â Good news!</strong> None of your players are on BYE next week.
        </div>
"""
            
            # Show opponent's potential BYE issues
            opp_bye_count = 0
            for player in next_opponent.roster:
                team_abbrev = ESPN_TO_STANDARD.get(player.proTeam, player.proTeam)
                player_status = next_week_schedule.get(team_abbrev, 'UNKNOWN')
                if player_status == 'BYE' and player.lineupSlot != 'BE':
                    opp_bye_count += 1
            
            if opp_bye_count > 0:
                html += f"""
        <div class="info-box">
            <strong>Opponent Intel:</strong> {next_opponent.team_name} has {opp_bye_count} starter(s) on BYE next week. This could be your advantage!
        </div>
"""
        else:
            html += """
        <div class="alert">
            <strong>BYE WEEK</strong> - You have no matchup next week. Use this time to optimize your roster!
        </div>
"""
        
        html += """
    </div>
"""
    
    # Upcoming Schedule (Extended 3 weeks)
    html += f"""
    <div class="section">
        <h2>Upcoming Schedule (Next 3 Weeks)</h2>
        <p style="color: #666; font-size: 13px;">Plan ahead - identify tough matchups, BYE week issues, and potential wins.</p>
        <table>
            <tr>
                <th>Week</th>
                <th>Opponent</th>
                <th>Their Record</th>
                <th>Their Avg</th>
                <th>Difficulty</th>
                <th>Your BYE Players</th>
            </tr>
"""
    
    for i in range(week, min(week + 3, league.settings.reg_season_count)):
        opponent = my_team.schedule[i]
        week_num = i + 1
        
        # Get BYE info for this week
        future_schedule = fetch_nfl_schedule(week_num, YEAR)
        bye_count = 0
        bye_starters = 0
        
        for player in my_team.roster:
            team_abbrev = ESPN_TO_STANDARD.get(player.proTeam, player.proTeam)
            player_status = future_schedule.get(team_abbrev, 'UNKNOWN')
            if player_status == 'BYE':
                bye_count += 1
                if player.lineupSlot != 'BE':
                    bye_starters += 1
        
        if opponent:
            opp_avg = opponent.points_for / max(1, opponent.wins + opponent.losses)
            my_avg = my_team.points_for / max(1, my_team.wins + my_team.losses)
            
            if opp_avg > my_avg + 10:
                difficulty = "HARD"
                diff_color = "#ffcdd2"
            elif opp_avg > my_avg:
                difficulty = "Medium"
                diff_color = "#fff9c4"
            else:
                difficulty = "Favorable"
                diff_color = "#c8e6c9"
            
            bye_display = f"{bye_count} total ({bye_starters} starters)" if bye_count > 0 else "None"
            bye_color = "#ffcdd2" if bye_starters > 0 else "#ffffff"
            
            html += f"""
            <tr>
                <td><strong>Week {week_num}</strong></td>
                <td>{opponent.team_name}</td>
                <td>{opponent.wins}-{opponent.losses} (#{opponent.standing})</td>
                <td>{opp_avg:.2f} pts/wk</td>
                <td style="background-color: {diff_color};"><strong>{difficulty}</strong></td>
                <td style="background-color: {bye_color};">{bye_display}</td>
            </tr>
"""
        else:
            html += f"""
            <tr>
                <td><strong>Week {week_num}</strong></td>
                <td colspan="5">YOUR BYE WEEK - No matchup</td>
            </tr>
"""
    
    html += """
        </table>
    </div>
"""
    
    # Footer
    html += f"""
    <div class="section" style="text-align: center; color: #666;">
        <p><strong>Complete Strategic Data Extraction</strong></p>
        <p>Share this report with Claude for lineup advice, trade analysis, and waiver recommendations</p>
        <p>Last updated: {current_time}</p>
    </div>
</body>
</html>
"""
    
    return html

def main():
    try:
        print("="*80)
        print("ESPN FANTASY FOOTBALL - COMPLETE STRATEGIC EXTRACTION")
        print("="*80)
        
        league = connect_to_league()
        my_team = find_my_team(league)
        
        print(f"â Connected to {league.settings.name}")
        print(f"â Found team: {my_team.team_name}")
        print(f"â Current week: {league.current_week}")
        print(f"â Extracting comprehensive data...")
        
        html = generate_html_report(league, my_team)
        
        filename = f"fantasy_report_week_{league.current_week}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"â Report saved to {filename}")
        print(f"â Extracted data for {len(league.teams)} teams")
        print(f"â Analyzed {len(league.free_agents(size=100))} available players")
        print("\n" + "="*80)
        print("SUCCESS! Full strategic report generated.")
        print("="*80)
        
    except Exception as e:
        print(f"\nâ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
