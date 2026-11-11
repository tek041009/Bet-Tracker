#!/usr/bin/env python3
"""Owner-approved Panna coverage exceptions for Bet Picker + Sports Simulation Lab.

Source snapshot: Panna V14, approved 27 competitions; owner approval 2026-11-11.
Read-only; never changes original Panna records, never converts unavailable to zero.

Usage:
    with CoverageGate('/path/to/PANNA_V14_APPROVED_27_SCOPE_SQLITE.sqlite') as gate:
        decision = gate.check(match_id, layer='events') # or 'player'
        if decision['source_status'] == 'AVAILABLE':
            # Apply per-market quality gates, select original observations.
            ...
        elif decision['action'] == 'EXPECTED_SOURCE_GAP':
            # Record missing; skip affected observation, continue other work.
            ...
        else:
            # Record review/investigate; never hide a significant missing feed.
            ...

Stage windows are HEURISTICS by calendar month, not official round metadata.
"""
from __future__ import annotations

import collections
import json
import math
import sqlite3
from pathlib import Path

MAJOR = {'EPL','Championship','La_Liga','Bundesliga','Serie_A','Ligue_1','League_Cup'}
EUROPE = {'UCL','UEL','Conference_League'}
VALID_LAYERS = {'player','events'}
PREVIOUS_SEASON = '2025-2026'
SPARSE_MAX = 0.50           # Explicitly conservative relative to last-season coverage
BENCHMARK_MIN_FIXTURES = 20  # Small samples cannot authorize an automatic exception


def inferred_stage(competition: str, date: str) -> str:
    """Stage inference, never an official cup round assertion."""
    month = int(str(date)[5:7]) if len(str(date)) >= 7 and str(date)[5:7].isdigit() else None
    if competition == 'FA_Cup':
        if month in (8, 9): return 'EARLY_CUP_QUALIFYING_WINDOW'
        if month == 10: return 'OCTOBER_MIXED_CUP_WINDOW'
        if month == 11: return 'NOVEMBER_FIRST_ROUND_WINDOW'
        if month == 12: return 'DECEMBER_SECOND_ROUND_WINDOW'
        if month in (1, 2, 3, 4, 5, 6): return 'MAIN_CUP_WINDOW'
    if competition in EUROPE:
        if month in (7, 8): return 'UEFA_QUALIFYING_WINDOW'
        return 'UEFA_MAIN_OR_KNOCKOUT_WINDOW'
    if competition in MAJOR: return 'MAIN_DOMESTIC_COMPETITION'
    return 'UNVERIFIED_STAGE'


class CoverageGate:
    """Lightweight cached policy view over immutable Panna V14. No write operations."""

    def __init__(self, sqlite_path: str | Path):
        self.path = Path(sqlite_path).resolve()
        if not self.path.is_file():
            raise FileNotFoundError(f'Panna V14 database not found: {self.path}')
        self.db = sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True)
        self.db.row_factory = sqlite3.Row
        required = ('panna_v11_fixture_snapshot','panna_v14_market_safety','panna_match_quality_gates')
        tables = {r[0] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type IN ('view','table')")}
        absent = set(required) - tables
        if absent:
            self.db.close()
            raise ValueError(f'Panna V14 required tables absent: {sorted(absent)}')
        # 27 is a scope lock, not the count of competition categories found in source uploads.
        if self.db.execute('SELECT COUNT(*) FROM competition_catalogue').fetchone()[0] != 27:
            self.db.close()
            raise ValueError('Unexpected Panna competition scope; do not auto-approve exceptions')
        self.fixtures = {r['match_id']: dict(r) for r in self.db.execute(
            'SELECT match_id,competition,season,match_date,home_team,away_team,home_team_id,away_team_id,'
            'player_stat_state,detailed_event_state FROM panna_v11_fixture_snapshot')}
        self.safety = {r['match_id']: dict(r) for r in self.db.execute(
            'SELECT match_id,quality_status,safe_native_player_90min_aggregate,native_event_coverage,'
            'extra_time_events,penalty_shootout_events,missing_substitute_scorer_events FROM panna_v14_market_safety')}
        self.quality = {r['match_id']: dict(r) for r in self.db.execute(
            'SELECT match_id,overall_status,shots_quality,tackles_quality,dribbles_quality,fouls_quality,minutes_quality '
            'FROM panna_match_quality_gates')}
        self.top2 = set()
        self.professional_proxy = set()
        counts = collections.defaultdict(lambda: {'n':0,'player':0,'events':0})
        for row in self.fixtures.values():
            comp,season = row['competition'],row['season']
            ids = {row['home_team_id'],row['away_team_id']} - {None}
            if comp in ('EPL','Championship'): self.top2.update(ids)
            if comp in ('EPL','Championship','League_Cup'): self.professional_proxy.update(ids)
            if season == PREVIOUS_SEASON:
                s = inferred_stage(comp,row['match_date'])
                c = counts[comp,s]
                c['n'] += 1
                c['player'] += row['player_stat_state'] == 'MATCH_PLAYER_STATS_PRESENT'
                c['events'] += row['detailed_event_state'] == 'EVENT_SOURCE_RECORDED'
        self.baselines = {key:dict(val) for key,val in counts.items()}

    def close(self): self.db.close()
    def __enter__(self): return self
    def __exit__(self, *_): self.close()

    def check(self, match_id: str, layer: str, metric: str | None = None) -> dict:
        """Separate coverage from downstream quality; always returns a structured decision.

        action:
          USE_SOURCE: source exists; still obey metric-specific / V14 quality checks.
          EXPECTED_SOURCE_GAP: missing layer acceptable for coverage QA only; skip sample.
          REVIEW_MISSING: uncertain stage or important professional fixture; review.
          INVESTIGATE_MISSING: significant game or historically expected source absent.
          UNKNOWN_FIXTURE: no source fixture; do not infer a zero or approved exception.
        """
        if layer not in VALID_LAYERS:
            raise ValueError(f'Unsupported Panna source layer {layer!r}; select player/events')
        if metric not in (None,'shots','tackles','fouls','dribbles','minutes'):
            raise ValueError('Unknown metric. Use the source field quality gate as appropriate.')
        r = self.fixtures.get(match_id)
        if not r:
            return dict(match_id=match_id,layer=layer,source_status='UNAVAILABLE',action='UNKNOWN_FIXTURE',
                        usable_for_metric=False,reason='No verified fixture registry row',
                        investigation_required=True,prior_fixtures=None,prior_coverage=None,
                        stage='UNKNOWN',stage_verified=False,quality_status=None)
        stage = inferred_stage(r['competition'],r['match_date'])
        source = ((r['player_stat_state'] == 'MATCH_PLAYER_STATS_PRESENT') if layer == 'player'
                  else (r['detailed_event_state'] == 'EVENT_SOURCE_RECORDED'))
        benchmark = self.baselines.get((r['competition'],stage))
        previous_n = benchmark['n'] if benchmark else None
        previous_fraction = (benchmark[layer] / previous_n) if previous_n else None
        ids = {r['home_team_id'],r['away_team_id']} - {None}
        any_top2 = bool(ids & self.top2)
        pro_count = sum(i in self.professional_proxy for i in ids)
        safe = self.safety.get(match_id)
        quality = self.quality.get(match_id)
        quality_status = quality['overall_status'] if quality else None
        result = dict(match_id=match_id,competition=r['competition'],season=r['season'],date=r['match_date'],
                      teams=[r['home_team'],r['away_team']],layer=layer,stage=stage,stage_verified=False,
                      prior_fixtures=previous_n,prior_coverage=round(previous_fraction,4) if previous_fraction is not None else None,
                      high_profile_team=any_top2,professional_proxy_team_count=pro_count,
                      quality_status=quality_status,source_status='AVAILABLE' if source else 'UNAVAILABLE',
                      action='',usable_for_metric=False,investigation_required=False,reason='')
        if source:
            result['action']='USE_SOURCE'
            result['metric_only_exception']=False
            # No unconditional override of V14 overall status: metric-specific acceptance
            # is ONLY permitted where the native metric AND minutes pass their own gates,
            # and phase/scorer safeguards pass. Other metrics in that match remain blocked.
            eligible = quality_status == 'PASS'
            if layer == 'player':
                phase_ok = bool(safe and not safe['extra_time_events'] and
                                not safe['missing_substitute_scorer_events'])
                if metric is None:
                    eligible = eligible and bool(safe and safe['safe_native_player_90min_aggregate'])
                elif quality:
                    col = {'shots':'shots_quality','tackles':'tackles_quality','fouls':'fouls_quality',
                           'dribbles':'dribbles_quality','minutes':'minutes_quality'}[metric]
                    eligible = phase_ok and quality[col] == 'PASS' and quality['minutes_quality'] == 'PASS'
                    result['metric_only_exception'] = bool(eligible and quality_status != 'PASS')
                else:
                    eligible = False
            else:
                # Events MUST be selected from V14's period-filtered views, never raw source.
                eligible = eligible and bool(safe and safe['native_event_coverage'])
            result['usable_for_metric'] = bool(eligible)
            result['reason'] = (
                'Metric-specific Panna boxscore passes its own V14 quality+minutes gate; '
                'other failing metrics remain blocked' if result['metric_only_exception'] else
                'Layer present; use V14 phase-filtered and validated source rows' if eligible else
                'Layer present but relevant V14 quality/phase gate requires review or block')
            return result
        result['source_status']='UNAVAILABLE'
        # Most crucial invariant: no missing layer can ever be added to statistical denominators.
        if stage in ('MAIN_DOMESTIC_COMPETITION','UEFA_MAIN_OR_KNOCKOUT_WINDOW','MAIN_CUP_WINDOW'):
            action,reason='INVESTIGATE_MISSING','Source expected at this important main competition/stage'
        elif any_top2:
            action,reason='INVESTIGATE_MISSING','Top professional club overrides any early-round exemption'
        elif layer == 'player' and stage == 'OCTOBER_MIXED_CUP_WINDOW':
            action,reason='REVIEW_MISSING','FA Cup October has mixed round coverage; no automatic exemption'
        elif layer == 'events' and stage == 'OCTOBER_MIXED_CUP_WINDOW':
            action,reason='REVIEW_MISSING','FA Cup October round/stage is inferred and mixed; manual review'
        elif pro_count == 2:
            action,reason='REVIEW_MISSING','Professional pair must be checked, even in qualifiers'
        elif stage not in ('EARLY_CUP_QUALIFYING_WINDOW','NOVEMBER_FIRST_ROUND_WINDOW',
                           'DECEMBER_SECOND_ROUND_WINDOW','UEFA_QUALIFYING_WINDOW'):
            action,reason='REVIEW_MISSING','No approved stage-specific source-absence exemption'
        elif (previous_n is None or previous_n < BENCHMARK_MIN_FIXTURES or previous_fraction is None):
            action,reason='REVIEW_MISSING','Insufficient historical matches to justify expected gap'
        elif previous_fraction >= SPARSE_MAX:
            action,reason='INVESTIGATE_MISSING','Last season normally had this layer in this stage window'
        elif pro_count == 1:
            action,reason='REVIEW_MISSING','Professional club involved; confirm importance before acceptance'
        else:
            action,reason='EXPECTED_SOURCE_GAP','Historically sparse layer in low-profile early/qualifying fixture'
        result.update(action=action,reason=reason,investigation_required=action!='EXPECTED_SOURCE_GAP')
        return result

    def sample(self, observations: list[dict], layer: str, min_eligible: int = 5,
               metric: str | None = None) -> dict:
        """Research-side fail-safe for caller-provided verified appearances.

        Observations: [{'match_id':..., 'value':int/float/None}]. Entries must be
        actual player/market observations; NEVER infer player appearances from team fixtures.
        Unavailable None != 0. Do not emit probabilities when sample insufficient.
        """
        if not isinstance(min_eligible,int) or min_eligible < 1:
            raise ValueError('min_eligible must be a positive integer')
        eligible=[];skipped=[];seen=set()
        for row in observations:
            mid = row['match_id']
            if mid in seen:
                skipped.append({'match_id':mid,'action':'SKIP_DUPLICATE','reason':'DUPLICATE_MATCH_ID'})
                continue
            seen.add(mid)
            verdict=self.check(mid,layer,metric)
            value=row.get('value')
            numeric=(type(value) in (int,float) and math.isfinite(value) and value >= 0)
            if verdict['usable_for_metric'] and numeric:
                eligible.append({'match_id':mid,'value':value})
            else:
                skipped.append({'match_id':mid,'action':verdict['action'],
                                'reason':('VALUE_UNAVAILABLE_OR_INVALID' if not numeric else verdict['reason'])})
        return {'state':'READY_RESEARCH_ONLY' if len(eligible)>=min_eligible else 'INSUFFICIENT_DATA',
                'eligible_count':len(eligible),'excluded_count':len(skipped),'eligible':eligible,
                'excluded':skipped,'betting_recommendation':False}


def summarize_current_snapshot(database: str) -> dict:
    """Stable audit summary; explicitly separates known gaps from alerts."""
    with CoverageGate(database) as gate:
        counts=collections.Counter()
        details=[]
        for mid,row in gate.fixtures.items():
            if row['season']!='2026-2027':continue
            for layer in ('player','events'):
                d=gate.check(mid,layer)
                counts[(layer,d['action'])]+=1
                if d['source_status']=='UNAVAILABLE':details.append(d)
        return {'database':str(database),'approved_competitions':27,'season':'2026-2027',
                'counts':{layer:{a:n for (l,a),n in counts.items() if l==layer}
                          for layer in ('player','events')},
                'missing_cases':details,'policy':{'previous_season':PREVIOUS_SEASON,
                  'historical_sparse_threshold':SPARSE_MAX,'min_historical_fixtures':BENCHMARK_MIN_FIXTURES,
                  'stage_inferred_from_date':True,'betting_recommendations_enabled':False}}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',required=True)
    p.add_argument('--match-id')
    p.add_argument('--layer',choices=('player','events'),default='events')
    p.add_argument('--metric',choices=('shots','tackles','fouls','dribbles','minutes'))
    p.add_argument('--audit',action='store_true')
    p.add_argument('--output')
    args=p.parse_args()
    if args.audit: data=summarize_current_snapshot(args.database)
    else:
        if not args.match_id:p.error('--match-id is required without --audit')
        with CoverageGate(args.database) as g:data=g.check(args.match_id,args.layer,args.metric)
    value=json.dumps(data,indent=2)+'\n'
    if args.output:Path(args.output).write_text(value)
    else:print(value)
