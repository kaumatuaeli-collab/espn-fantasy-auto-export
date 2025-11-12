#!/usr/bin/env python3
"""
Fantasy Football Player Analyst v1.1
Pure player evaluation module - scores quality independent of roster context

Consensus framework with ChatGPT refinements:
- Percentile-based normalization (robust to outliers)
- Continuous matchup scoring
- Time-decayed averages
- Confidence scaling
- Real opportunity scores
- Top-3 reasoning for explainability
- Version tracking for reproducibility
"""

import json
import hashlib
import numpy as np
from typing import Dict, List, Tuple
from collections import defaultdict

# ============================================================================
# CONFIGURATION
# ============================================================================

MODEL_VERSION = 'player_analyst_v1.1'

# Position-specific starter weights (from consensus)
STARTER_WEIGHTS = {
    'QB': {
        'implied_pts': 0.40,
        'ewma_fp': 0.25,
        'avg': 0.20,
        'matchup': 0.10,
        'proj': 0.05,
    },
    'RB': {
        'implied_pts': 0.35,
        'ewma_fp': 0.30,
        'avg': 0.20,
        'matchup': 0.10,
        'proj': 0.05,
    },
    'WR': {
        'ewma_fp': 0.35,
        'avg': 0.25,
        'implied_pts': 0.20,
        'matchup': 0.15,
        'proj': 0.05,
    },
    'TE': {
        'avg': 0.40,
        'ewma_fp': 0.25,
        'implied_pts': 0.15,
        'matchup': 0.15,
        'proj': 0.05,
    },
    'D/ST': {
        'matchup': 0.40,
        'opp_implied_low': 0.30,
        'pressure': 0.15,
        'home': 0.10,
        'proj': 0.05,
    },
    'K': {
        'implied_pts': 0.50,
        'proj': 0.20,
        'home': 0.20,
        'avg': 0.10,
    },
}

# Waiver weights
WAIVER_WEIGHTS = {
    'upside': 0.30,
    'trend': 0.25,
    'implied_pts': 0.20,
    'opportunity': 0.15,
    'avg': 0.10,
}

# ROS weights
ROS_WEIGHTS = {
    'avg': 0.30,
    'trend': 0.25,
    'implied_pts': 0.20,
    'consistency': 0.15,
    'proj': 0.10,
}

# EWMA weights for last 3 games
EWMA_WEIGHTS = [0.5, 0.3, 0.2]

# Injury penalties
INJURY_PENALTIES = {
    'ACTIVE': 0.0,
    'QUESTIONABLE': -1.0,
    'DOUBTFUL': -3.0,
    'OUT': -10.0,
    'IR': -10.0,
    'INJURY_RESERVE': -10.0,
}

# Confidence multipliers (ChatGPT refinement #5)
CONFIDENCE_MULTIPLIERS = {
    'HIGH': 1.00,
    'MEDIUM': 0.90,
    'LOW': 0.80,
}

# ============================================================================
# CORE CALCULATION FUNCTIONS
# ============================================================================

def calculate_ewma(last_n: List[float], weights: List[float] = EWMA_WEIGHTS) -> float:
    """
    Exponentially weighted moving average
    
    Args:
        last_n: Recent game scores [most_recent, second, third]
        weights: Exponential weights (must sum to 1.0)
    
    Returns:
        Weighted average
    """
    if not last_n or len(last_n) == 0:
        return 0.0
    
    weighted_sum = 0.0
    for i in range(min(len(last_n), len(weights))):
        weighted_sum += last_n[i] * weights[i]
    
    return round(weighted_sum, 2)


def calculate_time_decay_avg(game_history: List[float], half_life: int = 6) -> float:
    """
    Season average with exponential decay (ChatGPT refinement #3)
    
    Args:
        game_history: All games [most_recent, ..., oldest]
        half_life: Games for weight to decay by 50%
    
    Returns:
        Time-weighted average
    
    Why: Early season outliers fade naturally
    """
    if not game_history:
        return 0.0
    
    # Calculate decay weights
    weights = [0.5 ** (i / half_life) for i in range(len(game_history))]
    
    # Weighted average
    weighted_sum = sum(score * weights[i] for i, score in enumerate(game_history))
    total_weight = sum(weights)
    
    return round(weighted_sum / total_weight, 2)


def normalize_score_robust(value: float, values_array: List[float], 
                          lo_q: float = 0.05, hi_q: float = 0.95) -> float:
    """
    Percentile-based normalization with winsorization (ChatGPT refinement #1)
    
    Args:
        value: Value to normalize
        values_array: All values for this metric
        lo_q: Lower quantile (default 5th percentile)
        hi_q: Upper quantile (default 95th percentile)
    
    Returns:
        Normalized score 0-10
    
    Why: Outliers don't explode the scale
    """
    if not values_array or len(values_array) < 3:
        return 5.0
    
    lo, hi = np.quantile(values_array, [lo_q, hi_q])
    
    if hi == lo:
        return 5.0
    
    # Winsorize (clip to range)
    value = min(max(value, lo), hi)
    
    # Normalize to 0-10
    normalized = 10 * (value - lo) / (hi - lo)
    return round(normalized, 1)


def calculate_trend_score(last_n: List[float], season_avg: float) -> float:
    """
    Compare recent form to season average
    
    Args:
        last_n: Recent game scores
        season_avg: Season average fantasy points
    
    Returns:
        Trend score 0-10
    """
    if not last_n or len(last_n) < 2 or season_avg == 0:
        return 5.0
    
    ewma = calculate_ewma(last_n)
    ratio = ewma / season_avg
    
    if ratio >= 1.3:
        return 9.0
    elif ratio >= 1.1:
        return 7.0
    elif ratio >= 0.9:
        return 5.0
    elif ratio >= 0.8:
        return 4.0
    else:
        return 3.0


def calculate_upside_score(stdev: float, avg: float, boom_rate: float) -> float:
    """
    Calculate ceiling/boom potential
    
    Args:
        stdev: Standard deviation
        avg: Season average
        boom_rate: % of games >120% of average
    
    Returns:
        Upside score 0-10
    """
    if avg == 0:
        return 0.0
    
    cv = stdev / avg
    upside = (boom_rate * 6) + (cv * 4)
    
    return min(10.0, round(upside, 1))


def calculate_risk_index(injury_status: str, stdev: float, avg: float) -> Dict:
    """
    Composite risk assessment
    
    Args:
        injury_status: ACTIVE/QUESTIONABLE/DOUBTFUL/OUT/IR
        stdev: Standard deviation
        avg: Season average
    
    Returns:
        Dict with risk_score, risk_category, use_case
    """
    # Injury component (60% weight)
    injury_risk = abs(INJURY_PENALTIES.get(injury_status, 0)) * 1.0
    
    # Volatility component (40% weight)
    cv = (stdev / avg) if avg > 0 else 0
    volatility_risk = min(10, cv * 10)
    
    # Composite
    risk_score = (injury_risk * 0.6) + (volatility_risk * 0.4)
    
    # Categorize
    if risk_score > 6:
        category = 'HIGH'
        use_case = 'Bench/Stash'
    elif risk_score > 3:
        category = 'MEDIUM'
        use_case = 'Flex'
    else:
        category = 'LOW'
        use_case = 'Core Starter'
    
    return {
        'risk_score': round(risk_score, 1),
        'risk_category': category,
        'use_case': use_case,
    }


def calculate_matchup_score_continuous(player: Dict, game_details: Dict) -> float:
    """
    Continuous matchup quality from opponent implied points (ChatGPT refinement #2)
    
    Args:
        player: Player dict
        game_details: Game context
    
    Returns:
        Matchup score 0-10 (continuous)
    """
    opp_team = player.get('opp')
    if not opp_team or opp_team == 'BYE':
        return 5.0
    
    opp_game = game_details.get(opp_team, {})
    opp_implied = opp_game.get('implied_pts', 22)
    
    if player['pos'] == 'D/ST':
        # Lower opponent scoring = better for DST
        lo, hi = 14, 28
        opp_implied = min(max(opp_implied, lo), hi)
        return round(10 * (hi - opp_implied) / (hi - lo), 1)
    else:
        # Higher opponent implied = worse defense = better matchup
        lo, hi = 17, 27
        opp_implied = min(max(opp_implied, lo), hi)
        return round(10 * (opp_implied - lo) / (hi - lo), 1)


def calculate_opportunity_score(player: Dict, player_pool: List[Dict]) -> float:
    """
    Opportunity from market signals + injury vacancy (ChatGPT refinement #6)
    
    Args:
        player: Player dict
        player_pool: All players
    
    Returns:
        Opportunity score 0-10
    """
    start_pct = player.get('start', 0)
    own_pct = player.get('own', 0)
    
    # Get all players at same position for normalization
    pos = player.get('pos')
    pos_players = [p for p in player_pool if p.get('pos') == pos]
    
    if not pos_players:
        return 5.0
    
    all_starts = [p.get('start', 0) for p in pos_players]
    all_owns = [p.get('own', 0) for p in pos_players]
    
    start_score = normalize_score_robust(start_pct, all_starts)
    own_score = normalize_score_robust(own_pct, all_owns)
    
    # Weighted combination
    base = (start_score * 0.6) + (own_score * 0.4)
    
    # Injury vacancy bonus (same team, same position, OUT/IR)
    vacancy_bonus = 0.0
    team = player.get('team')
    
    for teammate in player_pool:
        if (teammate.get('team') == team and 
            teammate.get('pos') == pos and
            teammate.get('inj') in ['OUT', 'IR', 'INJURY_RESERVE'] and
            teammate.get('id') != player.get('id')):
            vacancy_bonus = 2.0
            break
    
    return min(10.0, base + vacancy_bonus)


def calculate_kicker_environment(home: bool, dome: bool = False, 
                                wind_mph: float = None) -> float:
    """
    Kicker environment quality (ChatGPT refinement #8)
    
    Args:
        home: Is kicker at home?
        dome: Is game in dome?
        wind_mph: Wind speed (optional)
    
    Returns:
        Environment score 0-10
    """
    base = 7.0 if home else 5.0
    
    if dome:
        base += 1.5
    
    if wind_mph is not None:
        if wind_mph >= 20:
            base -= 2.0
        elif wind_mph >= 12:
            base -= 1.0
    
    return max(0.0, min(10.0, base))


def calculate_dst_pressure_score(player: Dict, all_dst: List[Dict]) -> float:
    """
    D/ST pressure proxy using EWMA FP (ChatGPT refinement #7)
    
    Args:
        player: D/ST player
        all_dst: All D/ST players
    
    Returns:
        Pressure score 0-10
    """
    if player['pos'] != 'D/ST':
        return 5.0
    
    ewma = calculate_ewma(player.get('last_n', []))
    all_ewma = [calculate_ewma(d.get('last_n', [])) for d in all_dst if d.get('last_n')]
    
    if not all_ewma:
        return 5.0
    
    return normalize_score_robust(ewma, all_ewma)


def apply_injury_penalty(score: float, injury_status: str) -> float:
    """
    Reduce score based on injury, clamped at 0 (ChatGPT refinement #4)
    
    Args:
        score: Base score
        injury_status: Injury status
    
    Returns:
        Adjusted score ≥ 0
    """
    penalty = INJURY_PENALTIES.get(injury_status, 0.0)
    return max(0.0, score + penalty)


def calculate_confidence(player: Dict) -> str:
    """
    Assess data quality for predictions
    
    Args:
        player: Player dict
    
    Returns:
        'HIGH' | 'MEDIUM' | 'LOW'
    """
    games_played = len(player.get('last_n', []))
    injury_status = player.get('inj', 'ACTIVE')
    avg = player.get('avg', 0)
    stdev = player.get('stdev', 0)
    
    cv = (stdev / avg) if avg > 0 else 999
    
    # High confidence: 3+ games, active, CV < 0.5
    if games_played >= 3 and injury_status == 'ACTIVE' and cv < 0.5:
        return 'HIGH'
    
    # Low confidence: <2 games or injured or very volatile
    if games_played < 2 or injury_status in ['OUT', 'IR', 'DOUBTFUL'] or cv > 1.0:
        return 'LOW'
    
    return 'MEDIUM'


def apply_confidence_scaling(scores: Dict, confidence: str) -> Dict:
    """
    Scale all scores by confidence level (ChatGPT refinement #5)
    
    Args:
        scores: Dict with starter_score, waiver_score, ros_score
        confidence: HIGH/MEDIUM/LOW
    
    Returns:
        Scaled scores dict
    """
    multiplier = CONFIDENCE_MULTIPLIERS.get(confidence, 0.90)
    
    return {
        'starter_score': round(scores['starter_score'] * multiplier, 2),
        'waiver_score': round(scores['waiver_score'] * multiplier, 2),
        'ros_score': round(scores['ros_score'] * multiplier, 2),
    }


def extract_top_reasons(components: Dict, weights: Dict, k: int = 3) -> List[str]:
    """
    Identify top K contributors to score (ChatGPT refinement #9)
    
    Args:
        components: Dict of normalized component scores
        weights: Dict of weight values
        k: Number of top reasons
    
    Returns:
        List of top K component names
    """
    contributions = []
    for key, weight in weights.items():
        if key in components:
            contrib = components[key] * weight
            contributions.append((key, contrib, weight))
    
    contributions.sort(key=lambda x: x[1], reverse=True)
    
    reasons = []
    for i in range(min(k, len(contributions))):
        key, contrib, weight = contributions[i]
        reasons.append(f"{key} ({int(weight*100)}%)")
    
    return reasons


def calculate_weights_checksum(weights: Dict) -> str:
    """
    Generate checksum for weights (ChatGPT refinement #10)
    
    Args:
        weights: Weight dict
    
    Returns:
        SHA256 checksum (first 8 chars)
    """
    weights_str = json.dumps(weights, sort_keys=True)
    checksum = hashlib.sha256(weights_str.encode()).hexdigest()
    return checksum[:8]


# ============================================================================
# MAIN ANALYSIS FUNCTION
# ============================================================================

def analyze_player(player: Dict, player_pool: List[Dict], 
                  game_details: Dict) -> Dict:
    """
    Complete player analysis - v1.1
    
    Args:
        player: PlayerData dict from ESPN
        player_pool: All players for normalization
        game_details: Game context for matchup proxy
    
    Returns:
        PlayerAnalysis dict with all scores and metadata
    """
    pos = player['pos']
    
    # Skip if on bye (optional - can still score)
    if player.get('bye', False):
        pass  # We'll score them but flag them
    
    # Calculate time-decayed average (use last_n as proxy for full history)
    # Note: ESPN data has 'last_n' but not full game history
    # We'll use 'avg' as fallback and time-decay the last_n
    all_games = player.get('last_n', [])
    if all_games and len(all_games) >= 3:
        time_decay_avg = calculate_time_decay_avg(all_games)
    else:
        time_decay_avg = player.get('avg', 0)
    
    # Calculate intermediate metrics
    ewma = calculate_ewma(all_games)
    trend = calculate_trend_score(all_games, time_decay_avg)
    upside = calculate_upside_score(
        player.get('stdev', 0),
        time_decay_avg,
        player.get('boom_rate', 0) if 'boom_rate' in player else player.get('boom', 0)
    )
    risk = calculate_risk_index(
        player.get('inj', 'ACTIVE'),
        player.get('stdev', 0),
        time_decay_avg
    )
    
    # Matchup score (continuous)
    matchup = calculate_matchup_score_continuous(player, game_details)
    
    # Opportunity score
    opportunity = calculate_opportunity_score(player, player_pool)
    
    # Position-specific scores
    kicker_env = 5.0
    pressure_score = 5.0
    
    if pos == 'K':
        kicker_env = calculate_kicker_environment(
            player.get('home', False),
            player.get('dome', False),
            player.get('wind_mph')
        )
    
    if pos == 'D/ST':
        all_dst = [p for p in player_pool if p['pos'] == 'D/ST']
        pressure_score = calculate_dst_pressure_score(player, all_dst)
    
    # Normalize components (percentile-based)
    pos_players = [p for p in player_pool if p['pos'] == pos]
    
    # Get arrays for normalization
    all_implied = [p.get('implied_pts', 22) for p in player_pool if p.get('implied_pts')]
    pos_ewma = [calculate_ewma(p.get('last_n', [])) for p in pos_players if p.get('last_n')]
    pos_avg = [p.get('avg', 0) for p in pos_players if p.get('avg', 0) > 0]
    pos_proj = [p.get('proj', 0) for p in pos_players if p.get('proj', 0) > 0]
    
    components = {
        'implied_pts': normalize_score_robust(player.get('implied_pts', 22), all_implied) if player.get('implied_pts') else 5.0,
        'ewma_fp': normalize_score_robust(ewma, pos_ewma) if pos_ewma else 5.0,
        'avg': normalize_score_robust(time_decay_avg, pos_avg) if pos_avg else 5.0,
        'matchup': matchup,
        'proj': normalize_score_robust(player.get('proj', 0), pos_proj) if pos_proj and player.get('proj', 0) > 0 else 5.0,
        'trend': trend,
        'upside': upside,
        'opportunity': opportunity,
    }
    
    # D/ST specific
    if pos == 'D/ST':
        components['opp_implied_low'] = matchup
        components['pressure'] = pressure_score
        components['home'] = 7.0 if player.get('home', False) else 5.0
    
    # Kicker specific
    if pos == 'K':
        components['home'] = kicker_env
    
    # Apply position-specific weights
    starter_weights = STARTER_WEIGHTS.get(pos, STARTER_WEIGHTS['WR'])
    
    # Calculate base scores
    starter_score = sum([
        components.get(key, 5.0) * weight 
        for key, weight in starter_weights.items()
    ])
    
    waiver_score = (
        components['upside'] * WAIVER_WEIGHTS['upside'] +
        components['trend'] * WAIVER_WEIGHTS['trend'] +
        components['implied_pts'] * WAIVER_WEIGHTS['implied_pts'] +
        components['opportunity'] * WAIVER_WEIGHTS['opportunity'] +
        components['avg'] * WAIVER_WEIGHTS['avg']
    )
    
    # Consistency score for ROS
    consistency_score = 10 - min(10, (player.get('stdev', 0) / time_decay_avg) * 10) if time_decay_avg > 0 else 5.0
    
    ros_score = (
        components['avg'] * ROS_WEIGHTS['avg'] +
        components['trend'] * ROS_WEIGHTS['trend'] +
        components['implied_pts'] * ROS_WEIGHTS['implied_pts'] +
        consistency_score * ROS_WEIGHTS['consistency'] +
        components['proj'] * ROS_WEIGHTS['proj']
    )
    
    # Apply injury penalties
    starter_score = apply_injury_penalty(starter_score, player.get('inj', 'ACTIVE'))
    waiver_score = apply_injury_penalty(waiver_score, player.get('inj', 'ACTIVE'))
    ros_score = apply_injury_penalty(ros_score, player.get('inj', 'ACTIVE'))
    
    # Calculate confidence
    confidence = calculate_confidence(player)
    
    # Apply confidence scaling
    scores = apply_confidence_scaling({
        'starter_score': starter_score,
        'waiver_score': waiver_score,
        'ros_score': ros_score,
    }, confidence)
    
    # Extract top reasons
    starter_reasons = extract_top_reasons(
        {k: v for k, v in components.items() if k in starter_weights},
        starter_weights,
        k=3
    )
    
    waiver_reasons = extract_top_reasons({
        'upside': components['upside'],
        'trend': components['trend'],
        'implied_pts': components['implied_pts'],
        'opportunity': components['opportunity'],
        'avg': components['avg'],
    }, WAIVER_WEIGHTS, k=3)
    
    ros_reasons = extract_top_reasons({
        'avg': components['avg'],
        'trend': components['trend'],
        'implied_pts': components['implied_pts'],
        'consistency': consistency_score,
        'proj': components['proj'],
    }, ROS_WEIGHTS, k=3)
    
    # Collect flags
    flags = []
    if player.get('bye'):
        flags.append('BYE')
    if player.get('inj') not in ['ACTIVE', '']:
        flags.append('INJURY')
    if player.get('is_tnf'):
        flags.append('TNF')
    if player.get('is_mnf'):
        flags.append('MNF')
    if player.get('is_snf'):
        flags.append('SNF')
    
    # Generate checksums
    weights_checksum = f"STARTER:{calculate_weights_checksum(STARTER_WEIGHTS)}|WAIVER:{calculate_weights_checksum(WAIVER_WEIGHTS)}|ROS:{calculate_weights_checksum(ROS_WEIGHTS)}"
    
    # Package output
    return {
        'id': player.get('id'),
        'name': player.get('name'),
        'position': pos,
        'team': player.get('team'),
        
        'starter_score': scores['starter_score'],
        'waiver_score': scores['waiver_score'],
        'ros_score': scores['ros_score'],
        
        'risk_index': risk['risk_score'],
        'risk_category': risk['risk_category'],
        'confidence': confidence,
        'confidence_multiplier': CONFIDENCE_MULTIPLIERS[confidence],
        
        'starter_components': {k: round(v, 1) for k, v in components.items() if k in starter_weights},
        'waiver_components': {
            'upside': round(components['upside'], 1),
            'trend': round(components['trend'], 1),
            'implied_pts': round(components['implied_pts'], 1),
            'opportunity': round(components['opportunity'], 1),
            'avg': round(components['avg'], 1),
        },
        'ros_components': {
            'avg': round(components['avg'], 1),
            'trend': round(components['trend'], 1),
            'implied_pts': round(components['implied_pts'], 1),
            'consistency': round(consistency_score, 1),
            'proj': round(components['proj'], 1),
        },
        
        'starter_reasons': starter_reasons,
        'waiver_reasons': waiver_reasons,
        'ros_reasons': ros_reasons,
        
        'metadata': {
            'avg_raw': player.get('avg', 0),
            'time_decay_avg': time_decay_avg,
            'proj_raw': player.get('proj', 0),
            'implied_pts_raw': player.get('implied_pts'),
            'last_n_raw': player.get('last_n', []),
            'games_played': len(player.get('last_n', [])),
            'injury_status': player.get('inj', 'ACTIVE'),
            'model_version': MODEL_VERSION,
            'weights_checksum': weights_checksum,
        },
        
        'flags': flags,
    }


def analyze_players(players: List[Dict], game_details: Dict = None) -> Dict:
    """
    Batch analysis of all players
    
    Args:
        players: List of PlayerData dicts
        game_details: Game context (optional, will extract from players)
    
    Returns:
        Dict mapping player_id → PlayerAnalysis
    """
    # Extract game details if not provided
    if game_details is None:
        game_details = {}
    
    # Analyze each player
    results = {}
    for player in players:
        player_id = player.get('id')
        if not player_id:
            continue
        
        try:
            results[player_id] = analyze_player(player, players, game_details)
        except Exception as e:
            print(f"Error analyzing {player.get('name', 'Unknown')}: {e}")
            continue
    
    return results


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """CLI entry point"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python player_scoring.py <espn-data.json>")
        print("\nExample:")
        print("  python player_scoring.py Fantasy-Data-10-25.JSON")
        sys.exit(1)
    
    filename = sys.argv[1]
    
    print("="*70)
    print("FANTASY FOOTBALL PLAYER ANALYST v1.1")
    print("="*70)
    
    # Load data
    print(f"\nLoading: {filename}")
    with open(filename, 'r') as f:
        data = json.load(f)
    
    print(f"Week: {data['meta']['week']}")
    print(f"League: {data['league']['name']}")
    
    # Combine roster + waivers
    all_players = data['roster'].copy()
    for pos, players in data.get('waivers', {}).items():
        all_players.extend(players)
    
    print(f"Total players: {len(all_players)}")
    
    # Extract game details (already in ESPN data for some players)
    game_details = {}
    for player in all_players:
        if player.get('team') and player.get('opp') and player.get('implied_pts'):
            game_details[player['team']] = {
                'opp': player['opp'],
                'implied_pts': player['implied_pts'],
                'home': player.get('home', False),
            }
    
    # Analyze
    print("\nAnalyzing players...")
    player_scores = analyze_players(all_players, game_details)
    
    print(f"Successfully analyzed: {len(player_scores)} players")
    
    # Export
    output_file = filename.replace('.json', '_player_scores.json').replace('.JSON', '_player_scores.json')
    with open(output_file, 'w') as f:
        json.dump(player_scores, f, indent=2)
    
    print(f"\n✓ Saved: {output_file}")
    
    # Print sample
    print("\n" + "="*70)
    print("SAMPLE SCORES (Your Roster)")
    print("="*70)
    
    roster_ids = [p['id'] for p in data['roster'][:5]]
    for player_id in roster_ids:
        if player_id in player_scores:
            analysis = player_scores[player_id]
            print(f"\n{analysis['name']} ({analysis['position']})")
            print(f"  Starter: {analysis['starter_score']:.1f} | Waiver: {analysis['waiver_score']:.1f} | ROS: {analysis['ros_score']:.1f}")
            print(f"  Risk: {analysis['risk_category']} | Confidence: {analysis['confidence']}")
            print(f"  Top reasons: {', '.join(analysis['starter_reasons'][:2])}")
    
    print("\n" + "="*70)
    print("Analysis complete!")
    print("="*70)


if __name__ == "__main__":
    main()
