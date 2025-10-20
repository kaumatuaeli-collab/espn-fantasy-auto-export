#!/usr/bin/env python3
"""
Comprehensive ESPN Fantasy Football Data Extractor
Extracts detailed player data, league analysis, trade opportunities, and waiver targets
Generates an HTML report with full analysis
"""

from espn_api.football import League
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup
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
    }
    
    # Get recent stats if available
    if hasattr(player, 'stats'):
        try:
            details['last_week_points'] = player.stats.get(league.current_week - 1, {}).get('points', 0)
        except:
            details['last_week_points'] = 0
    else:
        details['last_week_points'] = 0
    
    return details

def analyze_matchup_quality(opponent_team):
    """Analyze opponent defense strength - lower score is better matchup"""
    if not opponent_team or opponent_team == 'BYE':
        return 'BYE', 'gray'
    
    # Simple heuristic - could be enhanced with real defensive rankings
    # For now, return neutral
    return 'AVERAGE', 'yellow'

def get_position_needs(team):
    """Identify weak positions on a team"""
    position_strength = {}
    
    for player in team.roster:
        pos = getattr(player, 'position', 'UNKNOWN')
        points = getattr(player, 'total_points', 0)
        
        if pos not in position_strength:
            position_strength[pos] = []
        position_strength[pos].append(points)
    
    # Calculate average by position
    needs = []
    for pos, points_list in position_strength.items():
        avg = sum(points_list) / len(points_list) if points_list else 0
        if avg < 50:  # Arbitrary threshold for "weak"
            needs.append(pos)
    
    return needs

def identify_trade_opportunities(league, my_team):
    """Identify potential trade partners based on roster needs"""
    my_needs = get_position_needs(my_team)
    opportunities = []
    
    for team in league.teams:
        if team.team_id == my_team.team_id:
            continue
        
        their_needs = get_position_needs(team)
        
        # Look for complementary needs
        for my_need in my_needs:
            # Check if they have surplus at my need position
            their_players = [p for p in team.roster if getattr(p, 'position', '') == my_need]
            if len(their_players) > 2:  # They have depth
                for their_need in their_needs:
                    my_players = [p for p in my_team.roster if getattr(p, 'position', '') == their_need]
                    if len(my_players) > 2:  # We have depth
                        opportunities.append({
                            'team': team.team_name,
                            'give': their_need,
                            'get': my_need,
                            'rationale': f"They need {their_need}, you need {my_need}"
                        })
    
    return opportunities

def get_top_available_players(league, position=None, limit=10):
    """Get top available free agents"""
    try:
        # ESPN API has free agents
        free_agents = league.free_agents(size=50)
        
        if position:
            free_agents = [p for p in free_agents if getattr(p, 'position', '') == position]
        
        # Sort by projected points
        free_agents.sort(key=lambda x: getattr(x, 'projected_points', 0), reverse=True)
        
        return free_agents[:limit]
    except:
        return []

def generate_html_report(league, my_team, trade_opps, available_players):
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
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
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
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th {{
            background-color: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #e0e0e0;
        }}
        tr:hover {{
            background-color: #f8f9fa;
        }}
        .injury-out {{ background-color: #ffebee; color: #c62828; font-weight: bold; }}
        .injury-questionable {{ background-color: #fff3e0; color: #ef6c00; font-weight: bold; }}
        .injury-ir {{ background-color: #f3e5f5; color: #6a1b9a; font-weight: bold; }}
        .good-matchup {{ background-color: #e8f5e9; }}
        .bad-matchup {{ background-color: #ffebee; }}
        .starter {{ font-weight: bold; background-color: #e3f2fd; }}
        .bench {{ color: #666; }}
        .stat-box {{
            display: inline-block;
            padding: 5px 10px;
            margin: 5px;
            border-radius: 5px;
            background-color: #e3f2fd;
        }}
        .alert {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 15px 0;
        }}
        .success {{
            background-color: #d4edda;
            border-left: 4px solid #28a745;
            padding: 15px;
            margin: 15px 0;
        }}
        @media (max-width: 768px) {{
            body {{ padding: 10px; }}
            table {{ font-size: 14px; }}
            th, td {{ padding: 8px 6px; }}
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
        <p><strong>Opponent Record:</strong> {matchup.wins}-{matchup.losses} (#{matchup.standing})</p>
        <p><strong>Their Points For:</strong> {matchup.points_for:.2f}</p>
    </div>
"""
    except:
        html += """
    <div class="alert">
        <strong>â ï¸ BYE WEEK</strong> - No matchup this week
    </div>
"""
    
    # My Roster
    html += """
    <div class="section">
        <h2>ð¥ My Roster</h2>
        <table>
            <tr>
                <th>Slot</th>
                <th>Player</th>
                <th>Pos</th>
                <th>Team</th>
                <th>Opp</th>
                <th>Proj</th>
                <th>Last Week</th>
                <th>Owned %</th>
                <th>Started %</th>
                <th>Status</th>
            </tr>
"""
    
    for player in my_team.roster:
        details = get_player_details(player, league)
        
        row_class = 'starter' if details['slot'] != 'BENCH' else 'bench'
        injury_class = ''
        
        if details['injury_status'] == 'OUT':
            injury_class = 'injury-out'
        elif details['injury_status'] in ['QUESTIONABLE', 'DOUBTFUL']:
            injury_class = 'injury-questionable'
        elif details['injury_status'] == 'INJURY_RESERVE':
            injury_class = 'injury-ir'
        
        status_display = details['injury_status'] if details['injury_status'] != 'ACTIVE' else 'â'
        
        html += f"""
            <tr class="{row_class}">
                <td>{details['slot']}</td>
                <td><strong>{details['name']}</strong></td>
                <td>{details['position']}</td>
                <td>{details['pro_team']}</td>
                <td>{details['opponent']}</td>
                <td>{details['projected']:.1f}</td>
                <td>{details['last_week_points']:.1f}</td>
                <td>{details['percent_owned']:.1f}%</td>
                <td>{details['percent_started']:.1f}%</td>
                <td class="{injury_class}">{status_display}</td>
            </tr>
"""
    
    html += """
        </table>
    </div>
"""
    
    # League Standings
    html += """
    <div class="section">
        <h2>ð League Standings</h2>
        <table>
            <tr>
                <th>Rank</th>
                <th>Team</th>
                <th>Record</th>
                <th>PF</th>
                <th>PA</th>
            </tr>
"""
    
    sorted_teams = sorted(league.teams, key=lambda x: x.standing)
    for team in sorted_teams:
        row_class = 'starter' if team.team_id == my_team.team_id else ''
        marker = ' ð' if team.team_id == my_team.team_id else ''
        
        html += f"""
            <tr class="{row_class}">
                <td>{team.standing}</td>
                <td><strong>{team.team_name}</strong>{marker}</td>
                <td>{team.wins}-{team.losses}</td>
                <td>{team.points_for:.2f}</td>
                <td>{team.points_against:.2f}</td>
            </tr>
"""
    
    html += """
        </table>
    </div>
"""
    
    # Trade Opportunities
    if trade_opps:
        html += """
    <div class="section">
        <h2>ð Trade Opportunities</h2>
        <table>
            <tr>
                <th>Team</th>
                <th>You Give</th>
                <th>You Get</th>
                <th>Rationale</th>
            </tr>
"""
        
        for opp in trade_opps:
            html += f"""
            <tr>
                <td>{opp['team']}</td>
                <td>{opp['give']}</td>
                <td>{opp['get']}</td>
                <td>{opp['rationale']}</td>
            </tr>
"""
        
        html += """
        </table>
    </div>
"""
    
    # Top Available Players by Position
    positions = ['QB', 'RB', 'WR', 'TE', 'D/ST', 'K']
    html += """
    <div class="section">
        <h2>ð¯ Top Available Players</h2>
"""
    
    for pos in positions:
        top_players = get_top_available_players(league, position=pos, limit=5)
        if top_players:
            html += f"""
        <h3>{pos}</h3>
        <table>
            <tr>
                <th>Player</th>
                <th>Team</th>
                <th>Projected</th>
                <th>Owned %</th>
            </tr>
"""
            
            for player in top_players:
                details = get_player_details(player, league)
                html += f"""
            <tr>
                <td><strong>{details['name']}</strong></td>
                <td>{details['pro_team']}</td>
                <td>{details['projected']:.1f}</td>
                <td>{details['percent_owned']:.1f}%</td>
            </tr>
"""
            
            html += """
        </table>
"""
    
    html += """
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
            </tr>
"""
    
    for i in range(week - 1, min(week + 3, league.settings.reg_season_count)):
        opponent = my_team.schedule[i]
        week_num = i + 1
        if opponent:
            html += f"""
            <tr>
                <td>Week {week_num}</td>
                <td>{opponent.team_name}</td>
                <td>{opponent.wins}-{opponent.losses}</td>
            </tr>
"""
        else:
            html += f"""
            <tr>
                <td>Week {week_num}</td>
                <td colspan="2">BYE WEEK</td>
            </tr>
"""
    
    html += """
        </table>
    </div>
"""
    
    # Footer
    html += f"""
    <div class="section" style="text-align: center; color: #666;">
        <p>Generated automatically by ESPN Fantasy Extractor</p>
        <p>Last updated: {current_time}</p>
    </div>
</body>
</html>
"""
    
    return html

def main():
    try:
        print("="*80)
        print("ESPN FANTASY FOOTBALL COMPREHENSIVE EXTRACTOR")
        print("="*80)
        
        # Connect to ESPN
        league = connect_to_league()
        my_team = find_my_team(league)
        
        print(f"â Connected to {league.settings.name}")
        print(f"â Found team: {my_team.team_name}")
        print(f"â Current week: {league.current_week}")
        
        # Analyze trade opportunities
        print("\nAnalyzing trade opportunities...")
        trade_opps = identify_trade_opportunities(league, my_team)
        print(f"â Found {len(trade_opps)} potential trade opportunities")
        
        # Get available players
        print("\nFetching top available players...")
        available_players = get_top_available_players(league, limit=20)
        print(f"â Found {len(available_players)} top available players")
        
        # Generate HTML report
        print("\nGenerating HTML report...")
        html = generate_html_report(league, my_team, trade_opps, available_players)
        
        # Save to file
        filename = f"fantasy_report_week_{league.current_week}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"â Report saved to {filename}")
        
        print("\n" + "="*80)
        print("SUCCESS! Comprehensive report generated.")
        print("="*80)
        
    except Exception as e:
        print(f"\nâ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
