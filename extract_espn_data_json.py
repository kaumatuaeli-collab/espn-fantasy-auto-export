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
    'KC': 'KC', 'LAC': 'LAC', 'LAR': 'LAR', 'LV': 'LV', 'MIA': 'MIA'
