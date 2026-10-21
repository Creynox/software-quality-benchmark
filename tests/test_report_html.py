import copy
import importlib
import json
import re
import tempfile
import unittest
from pathlib import Path

from test_report_spec import build, effort, every_stage, manifest, review

module = importlib.import_module('projects.ble-elva.tools.report_html')
spec_module = importlib.import_module('projects.ble-elva.tools.report_spec')
GOLDEN = Path(__file__).parent / 'golden' / ('nsn014-bericht-%s.html' % spec_module.load_spec()['spec_version'])


def run8_like():
    """Shape of live run 824fa661: report stage blocked by the Oracle, RIGHTS not run, partly passed measurement stages."""
    records = every_stage('INCONCLUSIVE', 'INCOMPLETE')
    records[0]['result'] = records[1]['result'] = 'PASS'
    records[3]['position_results'][5].update(result='PASS', **{'class': None})
    records[3]['position_results'][4].update(**{'class': 'EXECUTOR_REQUEST_FAILED'})
    records[10] = {'case_id': 'NSN014-REPORT', 'result': 'BLOCKED', 'reason': 'REPORT_ORACLE_UNAVAILABLE'}
    records[11] = {'case_id': 'NSN014-RIGHTS', 'result': 'NOT_RUN', 'reason': 'UPSTREAM_CRITICAL_STOP'}
    rows = [{'case': 'SIEVE', 'position': 'P01', 'kind': 'sieve', 'reached': 'ja', 'status': 'BLOCKED', 'origin': 'MODELL', 'effort': effort(), 'save': 'NOT_SAVED_AFTER_ENTRY'},
            {'case': 'SIEVE', 'position': 'P06', 'kind': 'sieve', 'reached': 'ja', 'status': 'DONE', 'origin': '—', 'effort': effort(), 'save': 'SAVED'}]
    finding = {'category': 'UX_IMPROVEMENT', 'severity': 'major', 'observed': 'x', 'expected': 'y', 'suggestion': 'z', 'evidence': '1'}
    return build(manifest(technical_status='BLOCKED', run_id='run-8'), records, rows, [review('PASS', (3, 4, 5, None), [finding])])


DECISIONS = [{'id': 'D-1', 'status': 'OPEN', 'title': 'Lauf 9 freigeben', 'options': ['jetzt', 'später'], 'next_step': 'PO entscheidet'},
             {'id': 'D-2', 'status': 'DECIDED', 'title': 'schon entschieden', 'decision': 'x'}]


class ReportHtmlTests(unittest.TestCase):
    def test_the_report_is_email_safe_html_built_only_from_the_scorecard(self):
        card = run8_like()
        text = module.render_report(card, decisions=DECISIONS)
        self.assertTrue(text.startswith('<!DOCTYPE html>'))
        for forbidden in ('<script', '<link', '<style', 'class=', 'http://', 'https://', '@import'):
            self.assertNotIn(forbidden, text, 'inline styles only, nothing external, nothing executable')
        self.assertEqual(text, module.render_report(copy.deepcopy(card), decisions=DECISIONS), 'the same scorecard gives the same page')
        for title in spec_module.load_spec()['html']['section_titles'].values():
            if title != 'ein Segment je Prüfpunkt':
                self.assertIn(title, text)
        self.assertIn('&#9679; ABGEBROCHEN', text)
        self.assertIn('Kritischer Stopp: Prüfberichte erzeugen (REPORT_ORACLE_UNAVAILABLE).', text)
        self.assertIn('Belegte BLE-Abweichungen: 0.', text)
        self.assertIn('Lauf 9 freigeben', text);self.assertNotIn('schon entschieden', text)
        segments = re.findall(r'height:8px;background:(#[0-9a-f]{6})', text)
        self.assertEqual(len(segments), 46, 'one segment per check')
        self.assertEqual(segments.count(module.STATUS_COLORS['PASSED']), card['counts']['PASSED'])
        self.assertEqual(segments.count(module.STATUS_COLORS['NOT_RUN']), card['counts']['NOT_RUN'])

    def test_open_checks_are_grouped_by_cause_in_the_fixed_priority(self):
        card = run8_like()
        text = module.render_report(card, decisions=[])
        suite, provider, model = text.index('>Suite<'), text.index('>Provider<'), text.index('>Modell<')
        self.assertLess(suite, provider);self.assertLess(provider, model)
        self.assertIn('10 Prüfpunkte · Prüfberichte erzeugen', text)
        self.assertIn('1 Prüfpunkt · Siebanalyse erfassen', text)
        self.assertIn('Keine offenen Entscheidungen.', text)

    def test_next_steps_and_checklist_follow_fixed_rules(self):
        card = run8_like()
        steps = module.next_steps(spec_module.load_spec(), card)
        self.assertEqual(steps[0], 'Suite-Fehler beheben: Prüfberichte erzeugen – REPORT_ORACLE_UNAVAILABLE (10 Prüfpunkte).')
        self.assertIn('Provider-Ausfälle prüfen: 1 Prüfpunkt.', steps)
        self.assertIn('Nicht ausgeführte Stufen: Rechte der Werksleitung prüfen.', steps)
        self.assertIn('Speichern klären: 1 Aufgabe mit vollständiger Eingabe ohne Speichern.', steps)
        self.assertTrue(steps[-1].startswith('Nächster Benchmark-Lauf'))
        items = {key: done for key, done, _, _ in module.checklist(spec_module.load_spec(), card)}
        self.assertEqual((items['all_stages_run'], items['no_suite_fault'], items['no_provider_fault'], items['consistent']), (False, False, False, True))
        self.assertIsNone(items['comparable']);self.assertIsNone(items['dry_runs'])
        items = {key: done for key, done, _, _ in module.checklist(spec_module.load_spec(), card, gates={'dry_runs': True})}
        self.assertTrue(items['dry_runs'])
        passed = build(manifest(verdict='GO'))
        self.assertEqual(module.next_steps(spec_module.load_spec(), passed), [], 'a passed benchmark run has no next step')
        self.assertIn('&#9679; BESTANDEN', module.render_report(passed, decisions=[]))

    def test_a_rehearsal_is_labelled_and_has_no_reviewer_figures(self):
        card = build(manifest(run_kind='REHEARSAL', executor_model='claude-haiku-5-5'), every_stage('INCONCLUSIVE', 'INCOMPLETE'))
        self.assertEqual(card['run']['kind'], 'REHEARSAL')
        text = module.render_report(card, decisions=[])
        self.assertIn('Probelauf mit Claude-Executor (kein Benchmark-Ergebnis)', text)
        self.assertIn('kein Reviewer', text)
        self.assertEqual(module.next_steps(spec_module.load_spec(), card)[-1], 'Befunde des Probelaufs vor dem nächsten Benchmark-Lauf auswerten.')
        markdown = '\n'.join(spec_module.render(card))
        self.assertIn('| Art des Laufs | Probelauf mit Claude-Executor (kein Benchmark-Ergebnis) |', markdown)
        self.assertIn('keinen Reviewer', markdown)

    def test_changes_compare_with_the_previous_run_and_name_what_differs(self):
        before = build(manifest(run_id='run-7', completed_at='2026-10-19T10:00:00Z'), every_stage('INCONCLUSIVE', 'INCOMPLETE'))
        records = every_stage('INCONCLUSIVE', 'INCOMPLETE')
        records[2]['position_results'][0].update(result='PASS', **{'class': None})
        after = build(manifest(run_id='run-8', completed_at='2026-10-20T10:00:00Z'), records)
        text = module.render_report(after, previous=before, decisions=[])
        self.assertIn('Abschlämmung und Entnahmen erfassen P01', text)
        self.assertIn('Vergleich mit run-7: vergleichbar', text)
        other = build(manifest(run_id='run-9', completed_at='2026-10-21T10:00:00Z', guard_rules_sha256=None), records)
        text = module.render_report(other, previous=before, decisions=[])
        self.assertIn('nicht direkt vergleichbar, abweichend: guard_rules_sha256', text, 'a value that was not recorded is not equal')
        self.assertEqual(module.comparability_group(other), 'unvollständig')
        self.assertRegex(module.comparability_group(before), r'^[0-9a-f]{8}$')
        self.assertIn('Kein früherer Lauf dieser Art', module.render_report(before, decisions=[]))

    def test_values_are_escaped(self):
        card = build(manifest(run_id='<script>alert(1)</script>', executor_model='"><img src=x>'))
        text = module.render_report(card, decisions=[{'status': 'OPEN', 'title': '<b>x</b>', 'options': [], 'next_step': '&'}])
        self.assertNotIn('<script>alert', text);self.assertNotIn('<img src=x>', text);self.assertNotIn('<b>x</b>', text)

    def test_files_overview_and_previous_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cards = []
            for name, done, kind in (('a', '2026-10-18T10:00:00Z', 'BENCHMARK'), ('b', '2026-10-19T10:00:00Z', 'BENCHMARK'), ('c', '2026-10-20T10:00:00Z', 'REHEARSAL')):
                folder = root / name
                folder.mkdir()
                card = build(manifest(run_id=name, completed_at=done, run_kind=kind))
                (folder / 'scorecard.json').write_text(json.dumps(card), encoding='utf-8')
                cards.append(card)
            older = dict(cards[0], spec_version='1.0.0')
            (root / 'a' / 'scorecard-old.json').write_text(json.dumps(older), encoding='utf-8')
            runs = module.find_runs(root)
            self.assertEqual([folder.name for folder, _ in runs], ['a', 'b', 'c'])
            self.assertEqual(module.newest_scorecard(root / 'a')['spec_version'], cards[0]['spec_version'])
            self.assertEqual(module.previous_run(cards[1], runs)['run']['run_id'], 'a')
            self.assertIsNone(module.previous_run(cards[2], runs), 'a rehearsal is compared only with rehearsals')
            target = module.write_report(root / 'b', cards[1], history_roots=(root,), decisions=[])
            self.assertIn('Vergleich mit a', target.read_text(encoding='utf-8'))
            overview = module.write_overview(root).read_text(encoding='utf-8')
            self.assertLess(overview.index('>c<'), overview.index('>b<'));self.assertLess(overview.index('>b<'), overview.index('>a<'))
            self.assertIn('href="b/bericht.html"', overview);self.assertIn('Probelauf', overview)

    def test_the_rendered_report_equals_the_golden_file_of_this_version(self):
        text = module.render_report(run8_like(), decisions=DECISIONS, gates={'dry_runs': True})
        if not GOLDEN.exists():
            GOLDEN.parent.mkdir(exist_ok=True)
            GOLDEN.write_text(text, encoding='utf-8', newline='')
        self.assertEqual(text, GOLDEN.read_text(encoding='utf-8'), 'layout or wording changed: that needs a new version of the specification')


if __name__ == '__main__':
    unittest.main()
