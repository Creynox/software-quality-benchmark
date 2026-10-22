import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sqbf.registry import filter_runs


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.rows=[{'run_id':str(i),'result':result,'scenario_id':'CORE-SMOKE-01',
                    'date':'2026-10-13T20:17:41Z','software_version':'prefix-build-sha',
                    'persona':'Laborleitung','executor':'chatgpt_plan:gpt-6-luna',
                    'reviewer':'gpt-6.1-sol','scores':{'clarity':4}}
                   for i,result in enumerate(['GO','NO-GO','PARTIAL GO'])]

    def test_each_verdict_is_exact_and_disjoint(self):
        for result in ('GO','NO-GO','PARTIAL GO'):
            with self.subTest(result=result):
                rows=filter_runs(self.rows,result=result)
                self.assertEqual(len(rows),1)
                self.assertEqual(rows[0]['result'],result)

    def test_combined_filters(self):
        other=copy.deepcopy(self.rows[0]);other.update(run_id='other',scenario_id='other',date='2026-10-14')
        self.assertEqual([r['run_id'] for r in filter_runs(self.rows+[other],result='GO',test_id='CORE',date='2026-10-13')],['0'])
        self.assertEqual(filter_runs(self.rows,result='GO',date='2026-10-14'),[])

    def test_text_and_role_semantics_preserved(self):
        self.assertEqual(len(filter_runs(self.rows,test_id='SMOKE',date='2026-10',software_version='build',role='LUNA')),3)
        self.assertEqual(filter_runs(self.rows,test_id='smoke'),[])
        self.assertEqual(len(filter_runs(self.rows,role='labor')),3)

    def test_run_id_is_exact(self):
        extra=copy.deepcopy(self.rows[0]);extra['run_id']='0-extra'
        self.assertEqual([r['run_id'] for r in filter_runs(self.rows+[extra],run_id='0')],['0'])
        self.assertEqual(filter_runs(self.rows,run_id='missing'),[])

    def test_unknown_partial_or_differently_cased_results_no_false_matches(self):
        for result in ('UNKNOWN','G','GO ','go','PARTIAL',''):
            self.assertEqual(filter_runs(self.rows+[{'run_id':'missing'}],result=result),[])

    def test_pass_count_and_rate_not_inflated(self):
        passes=filter_runs(self.rows,result='GO')
        self.assertEqual(len(passes),1)
        self.assertEqual(len(passes)/len(self.rows),1/3)
        self.assertEqual(sum(len(filter_runs(self.rows,result=x)) for x in ('GO','NO-GO','PARTIAL GO')),len(self.rows))

    def test_filter_does_not_mutate_records(self):
        before=copy.deepcopy(self.rows)
        filter_runs(self.rows,result='GO',min_score=3)
        self.assertEqual(self.rows,before)
        self.assertEqual(filter_runs(self.rows,result='GO',min_score=5),[])

    def test_cli_exact_results_and_run_id_without_file_changes(self):
        from sqbf.cli import main
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'index.jsonl'
            path.write_text('\n'.join(json.dumps(r) for r in self.rows),encoding='utf-8')
            baseline=path.read_bytes()
            for result in ('GO','NO-GO','PARTIAL GO','unknown'):
                output=io.StringIO()
                with patch('sys.stdout',output):
                    code=main(['list-runs','--output',d,'--test-id','CORE','--date','2026-10-13','--result',result])
                self.assertEqual(code,0)
                self.assertEqual([r['result'] for r in json.loads(output.getvalue())],[] if result=='unknown' else [result])
            output=io.StringIO()
            with patch('sys.stdout',output):
                self.assertEqual(main(['list-runs','--output',d,'--run-id','1']),0)
            self.assertEqual([r['run_id'] for r in json.loads(output.getvalue())],['1'])
            self.assertEqual(path.read_bytes(),baseline)

    def test_missing_index_is_empty(self):
        from sqbf.cli import main
        with tempfile.TemporaryDirectory() as d,patch('sys.stdout',new_callable=io.StringIO) as output:
            self.assertEqual(main(['list-runs','--output',d,'--result','GO']),0)
            self.assertEqual(json.loads(output.getvalue()),[])
