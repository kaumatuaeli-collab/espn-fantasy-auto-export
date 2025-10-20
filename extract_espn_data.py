#!/usr/bin/env python3
"""
Comprehensive ESPN Fantasy Football Data Extractor
Extracts complete league data for strategic analysis
"""

from espn_api.football import League
import os
from datetime import datetime
import json

# ESPN Configuration
LEAGUE_ID = 44181678
YEAR = 2025
ESPN_S2 = os.environ.get('ESPN_S2')
SWID = os.environ.get('SWID')
MY_TEAM_NAME = 'Intelligent MBLeague (TM)'

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

def get_player_details(player, league):
    """Extract comprehensive player details"""
    details = {
        'name': player.name,
        'position': getattr(player, 'position', 'N/A'),
        'slot': getattr(player, 'slot_position', 'BENCH'),
        'pro_team': getattr(player, 'proTeam', 'N/A'),
        'opponent': getattr(player, 'pro_opponent', 'BYE'),
        'projected': getattr(player, 'projected_points', 0),
        'injury_status': getattr(player, 'injuryStatus', 'ACTIVE'),
        'percent_owned': getattr(player, 'percent_owned', 0),
        'percent_started': getattr(player, 'percent_started', 0),
        'total_points': getattr(player, 'total_points', 0),
        'avg_points': getattr(player, 'avg_points', 0),
        'player_id': getattr(player, 'playerId', 0),
    }
    
    # Calculate games played (for accurate averaging)
    details['games_played'] = 0
    if hasattr(player, 'stats'):
        for week, stat in player.stats.items():
            if stat.get('points', 0) > 0:
                details['games_played'] += 1
    
    # Get last 3 weeks performance
    last_3_weeks = []
    if hasattr(player, 'stats'):
        current_week = league.current_week
        for i in range(max(1, current_week - 3), current_week):
            week_points = player.stats.get(i, {}).get('points', 0)
            last_3_weeks.append(week_points)
    
    details['last_3_weeks'] = last_3_weeks
    details['last_3_avg'] = sum(last_3_weeks) / len(last_3_weeks) if last_3_weeks else 0
    
    return details

def get_injury_color(status):
    """Get color coding for injury status"""
    if status == 'OUT':
        return '#ffcdd2'  # Light red
    elif status in ['QUESTIONABLE', 'DOUBTFUL']:
        return '#fff9c4'  # Light yellow
    elif status == 'INJURY_RESERVE':
        return '#e1bee7'  # Light purple
    return '#ffffff'  # White

def get_top_available_players(league, position=None, limit=15, sort_by='projected'):
    """Get top available free agents with multiple sorting options"""
    try:
        free_agents = league.free_agents(size=100)
        
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

def analyze_position_strength(roster):
    """Analyze team strength by position"""
    position_stats = {}
    
    for player in roster:
        pos = getattr(player, 'position', 'UNKNOWN')
        if pos not in position_stats:
            position_stats[pos] = {
                'count': 0,
                'total_points': 0,
                'avg_points': 0,
                'players': []
            }
        
        total = getattr(player, 'total_points', 0)
        avg = getattr(player, 'avg_points', 0)
        
        position_stats[pos]['count'] += 1
        position_stats[pos]['total_points'] += total
        position_stats[pos]['avg_points'] += avg
        position_stats[pos]['players'].append({
            'name': player.name,
            'total': total,
            'avg': avg
        })
    
    # Calculate averages
    for pos in position_stats:
        count = position_stats[pos]['count']
        if count > 0:
            position_stats[pos]['team_avg'] = position_stats[pos]['avg_points'] / count
    
    return position_stats

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
            position: sticky;
            top: 0;
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
        .position-strength {{
            display: inline-block;
            padding: 5px 10px;
            margin: 3px;
            border-radius: 5px;
            font-size: 12px;
        }}
        .strength-high {{ background-color: #c8e6c9; color: #2e7d32; }}
        .strength-mid {{ background-color: #fff9c4; color: #f57f17; }}
        .strength-low {{ background-color: #ffcdd2; color: #c62828; }}
        .mini-table {{
            font-size: 12px;
            margin: 10px 0;
        }}
        .tabs {{
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }}
        .tab {{
            padding: 10px 20px;
            background-color: #e0e0e0;
            border-radius: 5px;
            cursor: pointer;
            font-weight: 600;
        }}
        .tab.active {{
            background-color: #667eea;
            color: white;
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
    
    for player in my_team.roster:
        details = get_player_details(player, league)
        
        row_class = 'starter' if details['slot'] != 'BENCH' else 'bench'
        injury_color = get_injury_color(details['injury_status'])
        
        status_display = details['injury_status'] if details['injury_status'] != 'ACTIVE' else 'â'
        
        last_3_display = ', '.join([f"{p:.1f}" for p in details['last_3_weeks']]) if details['last_3_weeks'] else 'N/A'
        
        html += f"""
            <tr class="{row_class}">
                <td>{details['slot']}</td>
                <td><strong>{details['name']}</strong></td>
                <td>{details['position']}</td>
                <td>{details['pro_team']}</td>
                <td>{details['opponent']}</td>
                <td>{details['projected']:.1f}</td>
                <td>{details['avg_points']:.1f}</td>
                <td>{details['total_points']:.1f}</td>
                <td style="font-size: 11px;">{last_3_display}</td>
                <td>{details['percent_owned']:.0f}%</td>
                <td>{details['percent_started']:.0f}%</td>
                <td style="background-color: {injury_color};">{status_display}</td>
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
        team_class = 'alert' if is_my_team else ''
        
        # Analyze position strength
        pos_strength = analyze_position_strength(team.roster)
        
        html += f"""
        <div class="{team_class}" style="margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 8px;">
            <h3>#{team.standing} - {team.team_name} {'ð YOU' if is_my_team else ''}</h3>
            <div class="stat-box">Record: {team.wins}-{team.losses}</div>
            <div class="stat-box">PF: {team.points_for:.2f}</div>
            <div class="stat-box">Avg: {team.points_for/max(1, team.wins + team.losses):.2f}/wk</div>
            
            <table style="margin-top: 10px;">
                <tr>
                    <th style="width: 15%;">Slot</th>
                    <th style="width: 25%;">Player</th>
                    <th style="width: 8%;">Pos</th>
                    <th style="width: 8%;">Proj</th>
                    <th style="width: 8%;">Avg</th>
                    <th style="width: 8%;">Total</th>
                    <th style="width: 15%;">Last 3</th>
                    <th style="width: 13%;">Status</th>
                </tr>
"""
        
        for player in team.roster:
            details = get_player_details(player, league)
            row_class = 'starter' if details['slot'] != 'BENCH' else 'bench'
            injury_color = get_injury_color(details['injury_status'])
            status_display = details['injury_status'] if details['injury_status'] != 'ACTIVE' else 'â'
            last_3_display = ', '.join([f"{p:.1f}" for p in details['last_3_weeks']]) if details['last_3_weeks'] else 'N/A'
            
            html += f"""
                <tr class="{row_class}">
                    <td>{details['slot']}</td>
                    <td><strong>{details['name']}</strong></td>
                    <td>{details['position']}</td>
                    <td>{details['projected']:.1f}</td>
                    <td>{details['avg_points']:.1f}</td>
                    <td>{details['total_points']:.1f}</td>
                    <td style="font-size: 11px;">{last_3_display}</td>
                    <td style="background-color: {injury_color}; font-size: 11px;">{status_display}</td>
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
                <td>{details['projected']:.1f}</td>
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
