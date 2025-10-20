#!/usr/bin/env python3
"""
ESPN Fantasy Football Auto-Extractor
Runs weekly to pull fantasy football data and save to Google Sheets
"""

from espn_api.football import League
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from datetime import datetime
import json

# ESPN Configuration
LEAGUE_ID = 44181678
YEAR = 2025
ESPN_S2 = os.environ.get('ESPN_S2')
SWID = os.environ.get('SWID')
MY_TEAM_NAME = 'Intelligent MBLeague (TM)'

# Google Sheets Configuration
GOOGLE_CREDS_JSON = os.environ.get('GOOGLE_CREDS_JSON')
SPREADSHEET_NAME = 'ESPN Fantasy Football Data'

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

def save_to_google_sheets(data):
    """Save data to Google Sheets"""
    print("Connecting to Google Sheets...")
    
    # Parse credentials from environment variable
    creds_dict = json.loads(GOOGLE_CREDS_JSON)
    
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # Open or create spreadsheet
    try:
        sheet = client.open(SPREADSHEET_NAME)
        print(f"Found existing spreadsheet: {SPREADSHEET_NAME}")
    except gspread.SpreadsheetNotFound:
        sheet = client.create(SPREADSHEET_NAME)
        sheet.share('kaumatuaeli@gmail.com', perm_type='user', role='writer')
        print(f"Created new spreadsheet: {SPREADSHEET_NAME}")
    
    # Get the first worksheet (or create one)
    try:
        worksheet = sheet.get_worksheet(0)
    except:
        worksheet = sheet.add_worksheet(title="Weekly Data", rows="100", cols="20")
    
    # Clear existing content and write new data
    worksheet.clear()
    
    # Split data into lines and write to sheet
    lines = data.split('\n')
    for i, line in enumerate(lines, start=1):
        worksheet.update_cell(i, 1, line)
    
    print(f"Data saved to Google Sheets: {sheet.url}")
    return sheet.url

def main():
    try:
        # Connect to ESPN
        league = connect_to_league()
        my_team = find_my_team(league)
        
        # Format data
        data = format_data(league, my_team)
        
        # Save to Google Sheets
        sheet_url = save_to_google_sheets(data)
        
        print("\n" + "="*80)
        print("SUCCESS!")
        print(f"Week {league.current_week} data extracted and saved")
        print(f"View at: {sheet_url}")
        print("="*80)
        
    except Exception as e:
        print(f"ERROR: {e}")
        raise

if __name__ == "__main__":
    main()
