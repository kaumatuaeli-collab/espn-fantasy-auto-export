#!/usr/bin/env python3
"""
ESPN API Diagnostic Tool
Shows exactly what data is available for players
"""

from espn_api.football import League
import os
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

def inspect_player(player, league):
    """Show all available attributes for a player"""
    print("\n" + "="*80)
    print(f"PLAYER: {player.name}")
    print("="*80)
    
    # Get all attributes
    attrs = [attr for attr in dir(player) if not attr.startswith('_')]
    
    for attr in attrs:
        try:
            value = getattr(player, attr)
            # Skip methods
            if callable(value):
                continue
            # Show the value
            if isinstance(value, (dict, list)) and len(str(value)) > 200:
                print(f"{attr}: [large data structure]")
            else:
                print(f"{attr}: {value}")
        except Exception as e:
            print(f"{attr}: ERROR - {e}")
    
    # Special inspection of stats if available
    if hasattr(player, 'stats'):
        print("\n--- STATS DETAIL ---")
        try:
            stats = player.stats
            print(f"Type: {type(stats)}")
            if isinstance(stats, dict):
                for week, stat in stats.items():
                    print(f"\nWeek {week}:")
                    print(f"  Type: {type(stat)}")
                    if isinstance(stat, dict):
                        for k, v in stat.items():
                            print(f"    {k}: {v}")
                    else:
                        # It's an object
                        stat_attrs = [a for a in dir(stat) if not a.startswith('_')]
                        for a in stat_attrs:
                            try:
                                val = getattr(stat, a)
                                if not callable(val):
                                    print(f"    {a}: {val}")
                            except:
                                pass
        except Exception as e:
            print(f"Error inspecting stats: {e}")

def main():
    try:
        print("ESPN API DIAGNOSTIC TOOL")
        print("="*80)
        
        league = connect_to_league()
        my_team = find_my_team(league)
        
        print(f"\nâ Connected to {league.settings.name}")
        print(f"â Current week: {league.current_week}")
        print(f"â Team: {my_team.team_name}")
        
        # Inspect first 3 players on my roster
        print("\n\nINSPECTING FIRST 3 PLAYERS ON YOUR ROSTER:")
        for i, player in enumerate(my_team.roster[:3]):
            inspect_player(player, league)
            if i >= 2:
                break
        
        print("\n" + "="*80)
        print("DIAGNOSTIC COMPLETE")
        print("="*80)
        
    except Exception as e:
        print(f"\nâ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
