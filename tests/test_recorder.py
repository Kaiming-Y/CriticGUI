"""Exercise capture lifecycle with fake desktop/OBS services, without controlling a GUI."""
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from human_demo.recorder.action_monitor import start_listening

class RecorderLifecycleTests(unittest.TestCase):
    def run_capture(self, fail_screenshot=False):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        root=Path(tmp.name); source=root/'obs-recording.mkv';source.write_bytes(b'video')
        calls=[]
        class Listener:
            def __init__(self,*args,**kwargs): self.callback=args[0] if args else None;self.active=False
            def start(self):
                self.active=True
                if self.callback:
                    next(iter(self.callback.values()))()
            def stop(self): self.active=False
            def join(self,timeout=None): pass
            def is_alive(self): return self.active
        keyboard=types.SimpleNamespace(Listener=Listener,GlobalHotKeys=Listener,Key=types.SimpleNamespace(ctrl_l='left',ctrl_r='right'))
        mouse=types.SimpleNamespace(Listener=Listener,Button=types.SimpleNamespace(left='left',right='right'))
        class Screenshot:
            def save(self,path):
                if fail_screenshot and Path(path).name=='after.png':raise RuntimeError('capture failed')
                Path(path).write_bytes(b'image')
        obs=types.ModuleType('human_demo.recorder.obs_util')
        obs.connect_to_obs=lambda: 'client'
        obs.start_recording=lambda client:calls.append('start')
        def stop(client):calls.append('stop');return source
        obs.stop_recording=stop
        obs.disconnect=lambda client:calls.append('disconnect')
        modules={'pynput':types.SimpleNamespace(mouse=mouse,keyboard=keyboard),
                 'pyautogui':types.SimpleNamespace(screenshot=Screenshot),
                 'human_demo.recorder.obs_util':obs}
        with patch.dict(sys.modules,modules),patch('human_demo.recorder.action_monitor.time.sleep'):
            if fail_screenshot:
                with self.assertRaisesRegex(RuntimeError,'capture failed'):start_listening(root/'recordings')
                self.assertEqual(calls,['start','stop','disconnect'])
                return
            log=Path(start_listening(root/'recordings'))
        self.assertEqual(calls,['start','stop','disconnect'])
        self.assertTrue(source.exists())
        self.assertEqual((log.parent/'video.mkv').read_bytes(),b'video')
        self.assertTrue((log.parent/'before.png').exists())
        self.assertTrue((log.parent/'after.png').exists())

    def test_copy_exact_clip_and_keep_original(self):self.run_capture()
    def test_stop_recording_on_capture_error(self):self.run_capture(True)

if __name__ == '__main__':unittest.main()
