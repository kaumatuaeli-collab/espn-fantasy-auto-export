#!/usr/bin/env python3
"""
ESPN Fantasy Football Auto-Extractor
Runs weekly to pull fantasy football data and save to repository
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

def format_data(league, my_team):
    """Format league data for output"""
    output = []
    
    # Header
    output.append("="*80)
    output.append("ESPN FANTASY FOOTBALL DATA EXPORT")
    output.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output.append("="*80)
    output.append("")
    
    # League and team info
    output.append(f"LEAGUE: {league.settings.name}")
    output.append(f"WEEK: {league.current_week} of {league.settings.reg_season_count}")
    output.append(f"MY TEAM: {my_team.team_name}")
    output.append(f"RECORD: {my_team.wins}-{my_team.losses}")
    output.append(f"POINTS FOR: {my_team.points_for:.2f}")
    output.append(f"STANDING: #{my_team.standing}")
    output.append("")
    
    # Current matchup
    output.append(f"--- WEEK {league.current_week} MATCHUP ---")
    try:
        matchup = my_team.schedule[league.current_week - 1]
        if matchup:
            output.append(f"{my_team.team_name} vs {matchup.team_name}")
            output.append(f"My Projected: {my_team.projected_lineup_points():.2f}")
            output.append(f"Opponent Projected: {matchup.projected_lineup_points():.2f}")
            output.append(f"Opponent Record: {matchup.wins}-{matchup.losses}")
        else:
            output.append("BYE WEEK")
    except:
        output.append("Matchup info unavailable")
    output.append("")
    
    # Roster
    output.append(f"--- MY ROSTER ---")
    output.append(f"{'SLOT':<8} {'PLAYER':<30} {'TEAM':<6} {'OPP':<10} {'PROJ':<6} {'STATUS'}")
    output.append("-"*80)
    
    for player in my_team.roster:
        slot = player.slot_position if hasattr(player, 'slot_position') else 'N/A'
        name = player.name[:29]
        pro_team = player.proTeam if hasattr(player, 'proTeam') else 'N/A'
        opponent = player.pro_opponent if hasattr(player, 'pro_opponent') else 'N/A'
        projected = player.projected_points if hasattr(player, 'projected_points') else 0
        
        injury_status = ''
        if hasattr(player, 'injuryStatus') and player.injuryStatus and player.injuryStatus != 'ACTIVE':
            injury_status = f"({player.injuryStatus})"
        
        output.append(f"{slot:<8} {name:<30} {pro_team:<6} {opponent:<10} {projected:<6.1f} {injury_status}")
    
    output.append("")
    
    # Standings
    output.append("--- LEAGUE STANDINGS ---")
    output.append(f"{'RANK':<6} {'TEAM':<30} {'RECORD':<10} {'PF':<10} {'PA':<10}")
    output.append("-"*80)
    
    sorted_teams = sorted(league.teams, key=lambda x: x.standing)
    for team in sorted_teams:
        record = f"{team.wins}-{team.losses}"
        marker = " <- ME" if team.team_name == MY_TEAM_NAME else ""
        output.append(f"{team.standing:<6} {team.team_name:<30} {record:<10} {team.points_for:<10.2f} {team.points_against:<10.2f}{marker}")
    
    output.append("")
    
    # Upcoming schedule
    output.append("--- MY UPCOMING SCHEDULE ---")
    for i in range(league.current_week - 1, min(league.current_week + 3, league.settings.reg_season_count)):
        opponent = my_team.schedule[i]
        week_num = i + 1
        if opponent:
            output.append(f"Week {week_num}: vs {opponent.team_name} ({opponent.wins}-{opponent.losses})")
        else:
            output.append(f"Week {week_num}: BYE")
    
    output.append("")
    output.append("="*80)
    
    return "\n".join(output)

def main():
    try:
        # Connect to ESPN
        league = connect_to_league()
        my_team = find_my_team(league)
        
        # Format data
        data = format_data(league, my_team)
        
        # Save to file
        filename = f"fantasy_data_week_{league.current_week}.txt"
        with open(filename, 'w') as f:
            f.write(data)
        
        print("\n" + "="*80)
        print("SUCCESS!")
        print(f"Week {league.current_week} data extracted and saved to {filename}")
        print("="*80)
        
        # Also print to console so it appears in GitHub Actions logs
        print("\n" + data)
        
    except Exception as e:
        print(f"ERROR: {e}")
        raise

if __name__ == "__main__":
    main()
