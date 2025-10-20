#!/usr/bin/env python3
"""
ESPN Fantasy Football Data Extractor - CORRECTED
Based on actual API structure from diagnostic
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
    """Extract comprehensive player details using correct API structure"""
    week = league.current_week
    
    details = {
        'name': player.name,
        'position': player.position,
        'slot': player.lineupSlot,
        'pro_team': player.proTeam,
        'injury_status': player.injuryStatus if hasattr(player, 'injuryStatus') else 'ACTIVE',
        'percent_owned': player.percent_owned,
        'percent_started': player.percent_started,
        'total_points': player.total_points,
        'avg_points': player.avg_points,
    }
    
    # Get current week projection and last 3 weeks from stats dict
    details['projected'] = 0
    details['last_3_weeks'] = []
    details['opponent'] = 'BYE'
    
    if hasattr(player, 'stats') and isinstance(player.stats, dict):
        # Current week projection
        current_week_stats = player.stats.get(week, {})
        if isinstance(current_week_stats, dict):
            details['projected'] = current_week_stats.get('projected_points', 0)
            # Check if this is a bye week (empty breakdown means bye)
            proj_breakdown = current_week_stats.get('projected_breakdown', {})
            if proj_breakdown:  # Has projections = playing this week
                details['opponent'] = 'vs OPP'  # ESPN doesn't give us opponent name easily
            else:
                details['opponent'] = 'BYE'
        
        # Last 3 weeks actual points
        for i in range(max(1, week - 3), week):
            week_stats = player.stats.get(i, {})
            if isinstance(week_stats, dict):
                points = week_stats.get('points', 0)
                details['last_3_weeks'].append(points)
            else:
                details['last_3_weeks'].append(0)
    
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
    """Get top available free agents"""
    try:
        week = league.current_week
        free_agents = league.free_agents(size=100)
        
        if position:
            free_agents = [p for p in free_agents if p.position == position]
        
        # Sort based on criteria
        if sort_by == 'projected':
            # Get current week projection from stats
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
        @media (max-width: 768px) {{
            body {{ padding: 10px; }}
            table {{ font-size: 12px; }}
            th, td {{ padding: 6px 4px; }}
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
    
    # My Roster
    html += f"""
    <div class="section">
        <h2>ð¥ My Roster - Week {week}</h2>
        <table>
            <tr>
                <th>Slot</th>
                <th>Player</th>
                <th>Pos</th>
                <th>Team</th>
                <th>Status</th>
                <th>Proj</th>
                <th>Avg</th>
                <th>Total</th>
                <th>Last 3 Weeks</th>
                <th>Own%</th>
                <th>Start%</th>
            </tr>
"""
    
    # Sort: starters first
    roster_sorted = sorted(my_team.roster, key=lambda p: (p.lineupSlot == 'BE', p.lineupSlot))
    
    for player in roster_sorted:
        details = get_player_details(player, league)
        
        row_class = 'starter' if details['slot'] != 'BE' else 'bench'
        injury_color = get_injury_color(details['injury_status'])
        status_display = details['injury_status'] if details['injury_status'] != 'ACTIVE' else 'â'
        
        last_3_display = ', '.join([f"{p:.1f}" for p in details['last_3_weeks']]) if details['last_3_weeks'] else 'N/A'
        
        html += f"""
            <tr class="{row_class}">
                <td><strong>{details['slot']}</strong></td>
                <td><strong>{details['name']}</strong></td>
                <td>{details['position']}</td>
                <td>{details['pro_team']}</td>
                <td style="background-color: {injury_color}; font-weight: bold;">{details['opponent']}</td>
                <td><strong>{details['projected']:.1f}</strong></td>
                <td>{details['avg_points']:.1f}</td>
                <td>{details['total_points']:.1f}</td>
                <td style="font-size: 11px;">{last_3_display}</td>
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
                    <th>Slot</th>
                    <th>Player</th>
                    <th>Pos</th>
                    <th>Status</th>
                    <th>Proj</th>
                    <th>Avg</th>
                    <th>Total</th>
                    <th>Last 3</th>
                </tr>
"""
        
        roster_sorted = sorted(team.roster, key=lambda p: (p.lineupSlot == 'BE', p.lineupSlot))
        
        for player in roster_sorted:
            details = get_player_details(player, league)
            row_class = 'starter' if details['slot'] != 'BE' else 'bench'
            injury_color = get_injury_color(details['injury_status'])
            status_display = details['injury_status'] if details['injury_status'] != 'ACTIVE' else 'â'
            last_3_display = ', '.join([f"{p:.1f}" for p in details['last_3_weeks']]) if details['last_3_weeks'] else 'N/A'
            
            html += f"""
                <tr class="{row_class}">
                    <td><strong>{details['slot']}</strong></td>
                    <td><strong>{details['name']}</strong></td>
                    <td>{details['position']}</td>
                    <td style="background-color: {injury_color}; font-size: 11px;">{details['opponent']}</td>
                    <td><strong>{details['projected']:.1f}</strong></td>
                    <td>{details['avg_points']:.1f}</td>
                    <td>{details['total_points']:.1f}</td>
                    <td style="font-size: 11px;">{last_3_display}</td>
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
                <th>Status</th>
                <th>Proj</th>
                <th>Avg</th>
                <th>Total</th>
                <th>Own%</th>
                <th>Start%</th>
            </tr>
"""
                
                for player in top_players:
                    details = get_player_details(player, league)
                    injury_color = get_injury_color(details['injury_status'])
                    
                    html += f"""
            <tr>
                <td><strong>{details['name']}</strong></td>
                <td>{details['pro_team']}</td>
                <td style="background-color: {injury_color};">{details['opponent']}</td>
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
        <p><strong>ð Complete Data Extraction</strong></p>
        <p>Share this report with Claude for strategic analysis</p>
        <p>Last updated: {current_time}</p>
    </div>
</body>
</html>
"""
    
    return html

def main():
    try:
        print("="*80)
        print("ESPN FANTASY FOOTBALL DATA EXTRACTOR - CORRECTED")
        print("="*80)
        
        league = connect_to_league()
        my_team = find_my_team(league)
        
        print(f"â Connected to {league.settings.name}")
        print(f"â Found team: {my_team.team_name}")
        print(f"â Current week: {league.current_week}")
        print(f"â Extracting data for {len(league.teams)} teams...")
        
        html = generate_html_report(league, my_team)
        
        filename = f"fantasy_report_week_{league.current_week}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"â Report saved to {filename}")
        print("\n" + "="*80)
        print("SUCCESS!")
        print("="*80)
        
    except Exception as e:
        print(f"\nâ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
