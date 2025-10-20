#!/usr/bin/env python3
"""
Comprehensive ESPN Fantasy Football Data Extractor - FIXED
Properly extracts all data with correct API access patterns
"""

from espn_api.football import League
import os
from datetime import datetime

# ESPN Configuration
LEAGUE_ID = 44181678
YEAR = 2025
ESPN_S2 = os.environ.get('ESPN_S2')
SWID = os.environ.get('SWID')
MY_TEAM_NAME = 'Intelligent MBLeague (TM)'

# Slot position mapping
SLOT_MAP = {
    0: 'QB',
    2: 'RB',
    4: 'WR',
    6: 'TE',
    16: 'D/ST',
    17: 'K',
    20: 'BENCH',
    21: 'IR',
    23: 'FLEX'
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

def get_slot_name(lineupSlot):
    """Convert ESPN slot ID to readable name"""
    return SLOT_MAP.get(lineupSlot, 'BENCH')

def get_player_details(player, league, week=None):
    """Extract comprehensive player details with proper API access"""
    if week is None:
        week = league.current_week
    
    # Basic info
    details = {
        'name': player.name,
        'position': player.position if hasattr(player, 'position') else 'N/A',
        'eligibleSlots': player.eligibleSlots if hasattr(player, 'eligibleSlots') else [],
        'pro_team': player.proTeam if hasattr(player, 'proTeam') else 'N/A',
        'player_id': player.playerId if hasattr(player, 'playerId') else 0,
    }
    
    # Get lineup slot
    if hasattr(player, 'lineupSlot'):
        details['slot'] = get_slot_name(player.lineupSlot)
    else:
        details['slot'] = 'BENCH'
    
    # Injury status
    details['injury_status'] = player.injuryStatus if hasattr(player, 'injuryStatus') else 'ACTIVE'
    
    # Ownership percentages
    details['percent_owned'] = player.percent_owned if hasattr(player, 'percent_owned') else 0
    details['percent_started'] = player.percent_started if hasattr(player, 'percent_started') else 0
    
    # Get stats - this is where we need to be careful
    details['projected'] = 0
    details['total_points'] = 0
    details['avg_points'] = 0
    details['last_3_weeks'] = []
    details['opponent'] = 'BYE'
    
    try:
        # Try to get current week projection
        if hasattr(player, 'projected_points'):
            details['projected'] = player.projected_points
        
        # Try to get total and average points
        if hasattr(player, 'total_points'):
            details['total_points'] = player.total_points
        if hasattr(player, 'avg_points'):
            details['avg_points'] = player.avg_points
        
        # Get opponent for current week
        if hasattr(player, 'pro_opponent'):
            opp = player.pro_opponent
            details['opponent'] = opp if opp else 'BYE'
        
        # Get last 3 weeks stats
        if hasattr(player, 'stats'):
            for i in range(max(1, week - 3), week):
                try:
                    week_stats = player.stats.get(i, {})
                    if isinstance(week_stats, dict):
                        points = week_stats.get('points', 0)
                    else:
                        # Sometimes it's an object, not a dict
                        points = getattr(week_stats, 'points', 0) if week_stats else 0
                    details['last_3_weeks'].append(points)
                except:
                    details['last_3_weeks'].append(0)
    except Exception as e:
        print(f"Warning: Could not get all stats for {player.name}: {e}")
    
    # Calculate last 3 average
    if details['last_3_weeks']:
        details['last_3_avg'] = sum(details['last_3_weeks']) / len(details['last_3_weeks'])
    else:
        details['last_3_avg'] = 0
    
    return details

def get_injury_color(status):
    """Get color coding for injury status"""
    if status == 'OUT':
        return '#ffcdd2'
    elif status in ['QUESTIONABLE', 'DOUBTFUL']:
        return '#fff9c4'
    elif status in ['INJURY_RESERVE', 'IR']:
        return '#e1bee7'
    return '#ffffff'

def get_top_available_players(league, position=None, limit=15, sort_by='projected'):
    """Get top available free agents with multiple sorting options"""
    try:
        free_agents = league.free_agents(size=100, week=league.current_week)
        
        if position:
            free_agents = [p for p in free_agents if getattr(p, 'position', '') == position]
        
        # Sort based on criteria
        if sort_by == 'projected':
            free_agents.sort(key=lambda x: getattr(x, 'projected_points', 0), reverse=True)
        elif sort_by == 'avg':
            free_agents.sort(key=lambda x: getattr(x, 'avg_points', 0), reverse=True)
        elif sort_by == 'owned':
            free_agents.sort(key=lambda x: getattr(x, 'percent_owned', 0), reverse=True)
        elif sort_by == 'started':
            free_agents.sort(key=lambda x: getattr(x, 'percent_started', 0), reverse=True)
        
        return free_agents[:limit]
    except Exception as e:
        print(f"Error fetching free agents: {e}")
        return []

def generate_html_report(league, my_team):
    """Generate comprehensive HTML report"""
    
    current_time = datetime.now().strftime('%Y-%m-%d %I:%M %p ET')
    week = league.current_week
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fantasy Football Report - Week {week}</title>
    <style>
        * {{
            box-sizing: border-box;
        }}
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
        .header h1 {{
            margin: 0 0 10px 0;
        }}
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
        tr:hover {{
            background-color: #f8f9fa;
        }}
        .starter {{ 
            font-weight: bold; 
            background-color: #e3f2fd; 
        }}
        .bench {{ 
            color: #666; 
        }}
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
        @media (max-width: 768px) {{
            body {{ padding: 10px; }}
            table {{ font-size: 12px; }}
            th, td {{ padding: 6px 4px; }}
            .stat-box {{ padding: 5px 10px; font-size: 14px; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>ð {league.settings.name}</h1>
        <div>Week {week} of {league.settings.reg_season_count} | {current_time}</div>
        <div style="margin-top: 10px; font-size: 18px;">{my_team.team_name}</div>
    </div>
    
    <div class="summary">
        <h2>ð Quick Stats</h2>
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
        <h2>ð¯ Week {week} Matchup</h2>
        <h3>{my_team.team_name} vs {matchup.team_name}</h3>
        <div class="stat-box">Opponent Record: {matchup.wins}-{matchup.losses} (#{matchup.standing})</div>
        <div class="stat-box">Their Avg: {matchup.points_for/max(1, matchup.wins + matchup.losses):.2f} pts/wk</div>
        <div class="stat-box">Their Total: {matchup.points_for:.2f} PF</div>
    </div>
"""
    except:
        html += """
    <div class="alert">
        <strong>â ï¸ BYE WEEK</strong> - No matchup this week
    </div>
"""
    
    # My Roster - Detailed
    html += f"""
    <div class="section">
        <h2>ð¥ My Roster - Complete Analysis</h2>
        <table>
            <tr>
                <th>Slot</th>
                <th>Player</th>
                <th>Pos</th>
                <th>Team</th>
                <th>Opp</th>
                <th>Proj</th>
                <th>Avg</th>
                <th>Total</th>
                <th>Last 3</th>
                <th>Own%</th>
                <th>Start%</th>
                <th>Status</th>
            </tr>
"""
    
    # Sort roster: starters first, then bench
    roster_sorted = sorted(my_team.roster, key=lambda p: (getattr(p, 'lineupSlot', 20) == 20, getattr(p, 'lineupSlot', 20)))
    
    for player in roster_sorted:
        details = get_player_details(player, league)
        
        row_class = 'starter' if details['slot'] != 'BENCH' and details['slot'] != 'IR' else 'bench'
        injury_color = get_injury_color(details['injury_status'])
        
        status_display = details['injury_status'] if details['injury_status'] != 'ACTIVE' else 'â'
        
        last_3_display = ', '.join([f"{p:.1f}" for p in details['last_3_weeks']]) if details['last_3_weeks'] else 'N/A'
        
        html += f"""
            <tr class="{row_class}">
                <td><strong>{details['slot']}</strong></td>
                <td><strong>{details['name']}</strong></td>
                <td>{details['position']}</td>
                <td>{details['pro_team']}</td>
                <td>{details['opponent']}</td>
                <td><strong>{details['projected']:.1f}</strong></td>
                <td>{details['avg_points']:.1f}</td>
                <td>{details['total_points']:.1f}</td>
                <td style="font-size: 11px;">{last_3_display}</td>
                <td>{details['percent_owned']:.0f}%</td>
                <td>{details['percent_started']:.0f}%</td>
                <td style="background-color: {injury_color}; font-weight: bold;">{status_display}</td>
            </tr>
"""
    
    html += """
        </table>
    </div>
"""
    
    # All League Rosters
    html += """
    <div class="section">
        <h2>ð Complete League Rosters</h2>
"""
    
    sorted_teams = sorted(league.teams, key=lambda x: x.standing)
    for team in sorted_teams:
        is_my_team = team.team_id == my_team.team_id
        
        html += f"""
        <div style="margin: 20px 0; padding: 15px; background: {'#fff3cd' if is_my_team else '#f8f9fa'}; border-radius: 8px; border-left: 4px solid {'#ffc107' if is_my_team else '#e0e0e0'};">
            <h3>#{team.standing} - {team.team_name} {'ð YOU' if is_my_team else ''}</h3>
            <div class="stat-box">Record: {team.wins}-{team.losses}</div>
            <div class="stat-box">PF: {team.points_for:.2f}</div>
            <div class="stat-box">Avg: {team.points_for/max(1, team.wins + team.losses):.2f}/wk</div>
            
            <table style="margin-top: 10px;">
                <tr>
                    <th style="width: 12%;">Slot</th>
                    <th style="width: 23%;">Player</th>
                    <th style="width: 7%;">Pos</th>
                    <th style="width: 7%;">Opp</th>
                    <th style="width: 8%;">Proj</th>
                    <th style="width: 8%;">Avg</th>
                    <th style="width: 8%;">Total</th>
                    <th style="width: 15%;">Last 3</th>
                    <th style="width: 12%;">Status</th>
                </tr>
"""
        
        roster_sorted = sorted(team.roster, key=lambda p: (getattr(p, 'lineupSlot', 20) == 20, getattr(p, 'lineupSlot', 20)))
        
        for player in roster_sorted:
            details = get_player_details(player, league)
            row_class = 'starter' if details['slot'] != 'BENCH' and details['slot'] != 'IR' else 'bench'
            injury_color = get_injury_color(details['injury_status'])
            status_display = details['injury_status'] if details['injury_status'] != 'ACTIVE' else 'â'
            last_3_display = ', '.join([f"{p:.1f}" for p in details['last_3_weeks']]) if details['last_3_weeks'] else 'N/A'
            
            html += f"""
                <tr class="{row_class}">
                    <td><strong>{details['slot']}</strong></td>
                    <td><strong>{details['name']}</strong></td>
                    <td>{details['position']}</td>
                    <td>{details['opponent']}</td>
                    <td><strong>{details['projected']:.1f}</strong></td>
                    <td>{details['avg_points']:.1f}</td>
                    <td>{details['total_points']:.1f}</td>
                    <td style="font-size: 11px;">{last_3_display}</td>
                    <td style="background-color: {injury_color}; font-size: 11px; font-weight: bold;">{status_display}</td>
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
        ('projected', 'By Projected Points'),
        ('avg', 'By Season Average'),
        ('owned', 'By Ownership %'),
        ('started', 'By Started %')
    ]
    
    for sort_key, sort_name in sort_options:
        html += f"""
    <div class="section">
        <h2>ð¯ Top Available Players - {sort_name}</h2>
"""
        
        for pos in positions:
            top_players = get_top_available_players(league, position=pos, limit=10, sort_by=sort_key)
            if top_players:
                html += f"""
        <h3>{pos}</h3>
        <table>
            <tr>
                <th>Player</th>
                <th>Team</th>
                <th>Opp</th>
                <th>Proj</th>
                <th>Avg</th>
                <th>Total</th>
                <th>Own%</th>
                <th>Start%</th>
                <th>Status</th>
            </tr>
"""
                
                for player in top_players:
                    details = get_player_details(player, league)
                    injury_color = get_injury_color(details['injury_status'])
                    status_display = details['injury_status'] if details['injury_status'] != 'ACTIVE' else 'â'
                    
                    html += f"""
            <tr>
                <td><strong>{details['name']}</strong></td>
                <td>{details['pro_team']}</td>
                <td>{details['opponent']}</td>
                <td><strong>{details['projected']:.1f}</strong></td>
                <td>{details['avg_points']:.1f}</td>
                <td>{details['total_points']:.1f}</td>
                <td>{details['percent_owned']:.0f}%</td>
                <td>{details['percent_started']:.0f}%</td>
                <td style="background-color: {injury_color};">{status_display}</td>
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
        <h2>ð League Standings</h2>
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
        marker = ' ð' if team.team_id == my_team.team_id else ''
        avg_per_week = team.points_for / max(1, team.wins + team.losses)
        
        html += f"""
            <tr class="{row_class}">
                <td>{team.standing}</td>
                <td><strong>{team.team_name}</strong>{marker}</td>
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
    
    # Upcoming Schedule
    html += f"""
    <div class="section">
        <h2>ð My Upcoming Schedule</h2>
        <table>
            <tr>
                <th>Week</th>
                <th>Opponent</th>
                <th>Their Record</th>
                <th>Their Avg</th>
            </tr>
"""
    
    for i in range(week - 1, min(week + 4, league.settings.reg_season_count)):
        opponent = my_team.schedule[i]
        week_num = i + 1
        if opponent:
            opp_avg = opponent.points_for / max(1, opponent.wins + opponent.losses)
            html += f"""
            <tr>
                <td>Week {week_num}</td>
                <td>{opponent.team_name}</td>
                <td>{opponent.wins}-{opponent.losses} (#{opponent.standing})</td>
                <td>{opp_avg:.2f} pts/wk</td>
            </tr>
"""
        else:
            html += f"""
            <tr>
                <td>Week {week_num}</td>
                <td colspan="3">BYE WEEK</td>
            </tr>
"""
    
    html += """
        </table>
    </div>
"""
    
    # Footer
    html += f"""
    <div class="section" style="text-align: center; color: #666;">
        <p><strong>ð Data Extraction Complete</strong></p>
        <p>Share this report with Claude for strategic analysis, trade recommendations, and start/sit decisions</p>
        <p>Last updated: {current_time}</p>
    </div>
</body>
</html>
"""
    
    return html

def main():
    try:
        print("="*80)
        print("ESPN FANTASY FOOTBALL COMPREHENSIVE DATA EXTRACTOR")
        print("="*80)
        
        # Connect to ESPN
        league = connect_to_league()
        my_team = find_my_team(league)
        
        print(f"â Connected to {league.settings.name}")
        print(f"â Found team: {my_team.team_name}")
        print(f"â Current week: {league.current_week}")
        print(f"â Extracting data for {len(league.teams)} teams...")
        
        # Generate HTML report
        print("\nGenerating comprehensive HTML report...")
        html = generate_html_report(league, my_team)
        
        # Save to file
        filename = f"fantasy_report_week_{league.current_week}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"â Report saved to {filename}")
        
        print("\n" + "="*80)
        print("SUCCESS! Comprehensive data extraction complete.")
        print("Share this report with Claude for strategic analysis.")
        print("="*80)
        
    except Exception as e:
        print(f"\nâ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
