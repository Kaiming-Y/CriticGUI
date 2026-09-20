import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from human_demo.plan.parse_plan import parse_plan_to_triplets, validate_plan
from human_demo.recorder.action_parser import preprocess_actions
from human_demo.action.action_translater import translate_write
from human_demo.action_process import export_samples

class WorkflowTests(unittest.TestCase):
    def test_three_levels_and_scoped_ids(self):
        rows = parse_plan_to_triplets('h0: A\nl0: B\na0: C\nl1: D\na0: E\nh1: F\nl0: G\na0: H')
        self.assertEqual([r['id'] for r in validate_plan(rows)], ['h0l0a0','h0l1a0','h1l0a0'])
        self.assertEqual(rows[2]['low-level'], 'G')

    def test_reject_malformed_and_stale_parent(self):
        for plan in ('h0: A\nl0: B\na0: C\nh1: D\na0: E',
                     'h0: A\nl0: B\na0: C\na0: D', 'h0: A\nl0: B',
                     'h0: A\nl0: B\na0: C\nl0: D\na0: E', 'something invalid'):
            with self.subTest(plan=plan), self.assertRaises(ValueError):
                parse_plan_to_triplets(plan)

    def test_text_code_escaping(self):
        text = "C:\\new\\test\nIt's quoted"
        code = '\n'.join(translate_write({'value': text}))
        class Fake:
            def write(self, value): self.value=value
        fake=Fake()
        exec(code, {'pyautogui':fake})
        self.assertEqual(fake.value,text)

    def test_click_parse_and_reviewed_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); folder=root/'recordings'/'step'; capture=folder/'capture';capture.mkdir(parents=True)
            log=capture/'events.log'
            log.write_text('ignored log header\n2026-01-01 12-00-00-000000 - Mouse click at (100, 200)\n2026-01-01 12-00-00-100000 - Mouse release at (100, 200)\n')
            with contextlib.redirect_stdout(io.StringIO()): parsed=preprocess_actions(str(log))
            self.assertTrue(any(r['Action']=='click' for r in parsed))
            (capture/'actions.json').write_text(json.dumps(parsed))
            for name in ('before.png','after.png','video.mkv'): (capture/name).write_bytes(b'test fixture')
            sample={'uid':'test_positive_h0l0a0','capture':'capture','meta':{'variant':'positive'},
                    'instructions':{'high-level':'Goal','low-level':'Subtask','atomic-level':'Click'}}
            (folder/'sample.json').write_text(json.dumps(sample));(folder/'complete.json').write_text('{}')
            self.assertEqual(export_samples(root/'recordings',root/'out1'),0)
            (folder/'annotation.json').write_text(json.dumps({'label':'success','reason':'Field focused'}))
            self.assertEqual(export_samples(root/'recordings',root/'out2'),1)
            result=json.loads((root/'out2'/'samples.jsonl').read_text())
            self.assertIn('pyautogui.click(100, 200)',result['action_code'])
            self.assertTrue((root/'out2'/result['media']['before']).is_file())
            self.assertEqual(result['review']['label'],'success')

if __name__ == '__main__': unittest.main()
