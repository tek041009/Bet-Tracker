#!/usr/bin/env python3
"""Run against source-verified Panna V14: python -m unittest -v test_panna_coverage_gate.py"""
import collections
import json
import os
import unittest
from pathlib import Path
from panna_coverage_gate import CoverageGate, inferred_stage, summarize_current_snapshot

DB=os.environ.get('PANNA_SQLITE_PATH','/mnt/data/PANNA_V14_APPROVED_27_SCOPE_SQLITE.sqlite')


class TestPannaOwnerCoveragePolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate=CoverageGate(DB)
        cls.early_fa=next(r for r in cls.gate.fixtures.values() if r['competition']=='FA_Cup'
            and r['season']=='2026-2027' and inferred_stage(r['competition'],r['match_date'])=='EARLY_CUP_QUALIFYING_WINDOW'
            and r['player_stat_state']!='MATCH_PLAYER_STATS_PRESENT')
        cls.fa_nov_sparse=next(r for r in cls.gate.fixtures.values() if r['competition']=='FA_Cup'
            and r['season']=='2026-2027' and inferred_stage(r['competition'],r['match_date'])=='NOVEMBER_FIRST_ROUND_WINDOW'
            and r['player_stat_state']=='MATCH_PLAYER_STATS_PRESENT'
            and r['detailed_event_state']!='EVENT_SOURCE_RECORDED'
            and cls.gate.check(r['match_id'],'events')['action']=='EXPECTED_SOURCE_GAP')
        cls.oxford=next(r for r in cls.gate.fixtures.values() if r['competition']=='FA_Cup'
            and r['season']=='2026-2027' and 'Oxford United' in r['home_team'] and 'Stevenage' in r['away_team'])
        cls.fa_oct=next(r for r in cls.gate.fixtures.values() if r['competition']=='FA_Cup'
            and r['season']=='2026-2027' and inferred_stage(r['competition'],r['match_date'])=='OCTOBER_MIXED_CUP_WINDOW'
            and r['player_stat_state']!='MATCH_PLAYER_STATS_PRESENT')
        cls.epl=next(r for r in cls.gate.fixtures.values() if r['competition']=='EPL'
            and r['season']=='2026-2027' and r['detailed_event_state']=='EVENT_SOURCE_RECORDED'
            and cls.gate.check(r['match_id'],'player','shots')['usable_for_metric'])
        cls.uefa_qual=next(r for r in cls.gate.fixtures.values() if r['competition']=='UCL'
            and r['season']=='2026-2027' and r['detailed_event_state']!='EVENT_SOURCE_RECORDED'
            and cls.gate.check(r['match_id'],'events')['action']=='EXPECTED_SOURCE_GAP')
        cls.et=next(r for r in cls.gate.fixtures.values() if r['match_id'] in cls.gate.safety
            and cls.gate.safety[r['match_id']]['extra_time_events']==1
            and r['player_stat_state']=='MATCH_PLAYER_STATS_PRESENT')

    @classmethod
    def tearDownClass(cls):cls.gate.close()

    def test_scope_preserved(self):
        self.assertEqual(self.gate.db.execute('SELECT COUNT(*) FROM competition_catalogue').fetchone()[0],27)
        self.assertEqual(len(self.gate.fixtures),8443)

    def test_fa_preliminary_player_missing_approved(self):
        v=self.gate.check(self.early_fa['match_id'],'player')
        self.assertEqual((v['action'],v['usable_for_metric']),('EXPECTED_SOURCE_GAP',False))

    def test_fa_november_event_gap_expected_but_player_usable(self):
        e=self.gate.check(self.fa_nov_sparse['match_id'],'events')
        p=self.gate.check(self.fa_nov_sparse['match_id'],'player','shots')
        self.assertEqual(e['action'],'EXPECTED_SOURCE_GAP')
        self.assertFalse(e['usable_for_metric'])
        self.assertEqual(p['source_status'],'AVAILABLE')
        self.assertTrue(p['usable_for_metric'])

    def test_fa_big_professional_fixture_escalates(self):
        e=self.gate.check(self.oxford['match_id'],'events')
        self.assertEqual(e['action'],'INVESTIGATE_MISSING')
        self.assertTrue(e['investigation_required'])
        self.assertEqual(self.gate.check(self.oxford['match_id'],'player')['source_status'],'AVAILABLE')

    def test_october_mixed_stage_not_automatically_waived(self):
        v=self.gate.check(self.fa_oct['match_id'],'player')
        self.assertEqual(v['action'],'REVIEW_MISSING')

    def test_uefa_qualifier_event_absence_expected_but_player_data_kept(self):
        e=self.gate.check(self.uefa_qual['match_id'],'events')
        self.assertEqual(e['action'],'EXPECTED_SOURCE_GAP')
        self.assertEqual(self.gate.check(self.uefa_qual['match_id'],'player')['source_status'],'AVAILABLE')

    def test_premier_league_source_has_no_gaps(self):
        for r in self.gate.fixtures.values():
            if r['competition']=='EPL':
                self.assertEqual(self.gate.check(r['match_id'],'player')['source_status'],'AVAILABLE')
                self.assertEqual(self.gate.check(r['match_id'],'events')['source_status'],'AVAILABLE')

    def test_premier_league_missing_source_would_be_investigated(self):
        mid=self.epl['match_id'];before=dict(self.gate.fixtures[mid]);self.gate.fixtures[mid]['detailed_event_state']='EVENT_SOURCE_NOT_AVAILABLE_OR_UNVERIFIED'
        try:self.assertEqual(self.gate.check(mid,'events')['action'],'INVESTIGATE_MISSING')
        finally:self.gate.fixtures[mid]=before

    def test_important_club_overrides_qualifier_exception(self):
        mid=self.uefa_qual['match_id'];before=dict(self.gate.fixtures[mid]);self.gate.fixtures[mid]['home_team_id']=next(iter(self.gate.top2))
        try:self.assertEqual(self.gate.check(mid,'events')['action'],'INVESTIGATE_MISSING')
        finally:self.gate.fixtures[mid]=before

    def test_extra_time_player_aggregates_cannot_be_90min_sample(self):
        v=self.gate.check(self.et['match_id'],'player','shots')
        self.assertEqual(v['source_status'],'AVAILABLE')
        self.assertFalse(v['usable_for_metric'])

    def test_zero_is_real_value_missing_is_not(self):
        mid=self.epl['match_id']
        r=self.gate.sample([{'match_id':mid,'value':0}],layer='player',metric='shots',min_eligible=1)
        self.assertEqual((r['eligible_count'],r['excluded_count'],r['state']),(1,0,'READY_RESEARCH_ONLY'))
        no=self.gate.sample([{'match_id':mid,'value':None}],layer='player',metric='shots',min_eligible=1)
        self.assertEqual((no['eligible_count'],no['excluded_count'],no['state']),(0,1,'INSUFFICIENT_DATA'))

    def test_bad_numeric_values_not_counted(self):
        mid=self.epl['match_id']
        for val in (float('nan'),float('inf'),-1,True,'0'):
            r=self.gate.sample([{'match_id':mid,'value':val}],layer='player',metric='shots',min_eligible=1)
            self.assertEqual(r['eligible_count'],0)

    def test_duplicate_matches_cannot_inflate_sample(self):
        mid=self.epl['match_id']
        r=self.gate.sample([{'match_id':mid,'value':0},{'match_id':mid,'value':1}],layer='player',metric='shots',min_eligible=2)
        self.assertEqual((r['eligible_count'],r['excluded_count'],r['state']),(1,1,'INSUFFICIENT_DATA'))

    def test_missing_event_not_zero_or_silent_eligible(self):
        mid=self.fa_nov_sparse['match_id']
        r=self.gate.sample([{'match_id':mid,'value':0}],layer='events',metric='shots',min_eligible=1)
        self.assertEqual((r['eligible_count'],r['excluded_count'],r['state']),(0,1,'INSUFFICIENT_DATA'))

    def test_unknown_fixture_does_not_crash_or_count(self):
        r=self.gate.check('made-up-unknown-fixture','events')
        self.assertEqual(r['action'],'UNKNOWN_FIXTURE')
        self.assertTrue(r['investigation_required'])
        self.assertFalse(r['usable_for_metric'])

    def test_invalid_layer_or_metric_rejected(self):
        with self.assertRaises(ValueError):self.gate.check(self.epl['match_id'],'imaginary')
        with self.assertRaises(ValueError):self.gate.check(self.epl['match_id'],'player','alien_metric')

    def test_min_sample_prevents_empty_probability(self):
        mid=self.epl['match_id']
        r=self.gate.sample([{'match_id':mid,'value':3}],layer='player',metric='shots',min_eligible=5)
        self.assertEqual(r['state'],'INSUFFICIENT_DATA')
        self.assertFalse(r['betting_recommendation'])

    def test_current_season_every_missing_source_classified(self):
        report=summarize_current_snapshot(DB)
        self.assertEqual(len(report['missing_cases']),1733)
        self.assertEqual(report['counts']['player']['EXPECTED_SOURCE_GAP'],655)
        self.assertEqual(report['counts']['events']['EXPECTED_SOURCE_GAP'],916)
        self.assertEqual(report['counts']['events']['INVESTIGATE_MISSING'],1)
        self.assertEqual(report['counts']['events']['USE_SOURCE'],1307)
        self.assertEqual(report['counts']['player']['USE_SOURCE'],1640)
        self.assertTrue(all(not x['usable_for_metric'] for x in report['missing_cases']))


if __name__=='__main__':unittest.main(verbosity=2)
