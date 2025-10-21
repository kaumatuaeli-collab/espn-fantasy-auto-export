#!/usr/bin/env python3
"""
Diagnostic Script - Check what weekly data is available
This will show us exactly what the ESPN API is giving us
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

def main():
    print("="*80)
    print("DIAGNOSTIC: Checking Weekly Stats Data")
    print("="*80)
    
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
        print("Could not find your team!")
        return
    
    print(f"Current Week: {league.current_week}")
    print(f"Team: {my_team.team_name}")
    print("\nChecking a few players from your roster...\n")
    
    # Check first 5 players
    for i, player in enumerate(my_team.roster[:5]):
        print("="*80)
        print(f"Player: {player.name} ({player.position} - {player.proTeam})")
        print(f"Total Points (season): {player.total_points}")
        print(f"Average Points: {player.avg_points}")
        
        if hasattr(player, 'stats'):
            print(f"\nStats type: {type(player.stats)}")
            
            if isinstance(player.stats, dict):
                print(f"Available weeks in stats: {sorted(player.stats.keys())}")
                
                # Check weeks 1-7
                for week in range(1, 8):
                    week_data = player.stats.get(week, None)
                    if week_data:
                        print(f"\n  Week {week}:")
                        print(f"    Type: {type(week_data)}")
                        if isinstance(week_data, dict):
                            points = week_data.get('points', 'NOT FOUND')
                            proj_points = week_data.get('projected_points', 'NOT FOUND')
                            breakdown = week_data.get('breakdown', 'NOT FOUND')
                            proj_breakdown = week_data.get('projected_breakdown', 'NOT FOUND')
                            
                            print(f"    Actual Points: {points}")
                            print(f"    Projected Points: {proj_points}")
                            print(f"    Has breakdown: {breakdown != 'NOT FOUND' and bool(breakdown)}")
                            print(f"    Has proj_breakdown: {proj_breakdown != 'NOT FOUND' and bool(proj_breakdown)}")
                            
                            # Show full keys available
                            print(f"    Available keys: {list(week_data.keys())}")
                    else:
                        print(f"\n  Week {week}: NO DATA")
            else:
                print(f"Stats is not a dict, it's: {player.stats}")
        else:
            print("Player has no 'stats' attribute")
        
        print()
    
    print("="*80)
    print("DIAGNOSTIC COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
