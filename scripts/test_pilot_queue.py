import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pilot_queue as queue


class TransitionTests(unittest.TestCase):
    def setUp(self):
        self.record={'old_scheduler_pid':1,'old_scheduler_start':'10',
                     'training_pid':2,'training_start':'20','training_run':'adapter_lr0.0001_seed42'}
        self.scheduler={'state':'T','start':'10','command':'scripts/pipeline.py --stage core'}

    def check_sequence(self,sequence,completed=True):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            run=root/'runs'/self.record['training_run']
            run.mkdir(parents=True)
            (run/'status.json').write_text(json.dumps({'status':'complete' if completed else 'training','epoch':3 if completed else 2}))
            with patch.object(queue,'ROOT',root), patch.object(queue,'STATUS',root/'pipeline_status.json'), \
                 patch.object(queue,'identity',side_effect=[self.scheduler,*sequence]), \
                 patch.object(queue,'retire_scheduler') as retire, patch.object(queue.time,'sleep'):
                if completed:
                    queue.wait_for_adapter(self.record)
                    retire.assert_called_once_with(self.record)
                else:
                    with self.assertRaisesRegex(RuntimeError,'before completing three epochs'):
                        queue.wait_for_adapter(self.record)
                    retire.assert_called_once_with(self.record)

    def test_empty_cmdline_during_exit(self):
        self.check_sequence([{'state':'R','start':'20','command':''},
                             {'state':'Z','start':'20','command':''}])

    def test_failed_child_still_retires_old_scheduler(self):
        self.check_sequence([None],completed=False)

    def test_live_wrong_identity_is_rejected(self):
        with patch.object(queue,'identity',side_effect=[self.scheduler,{'state':'R','start':'20','command':'unexpected command'}]):
            with self.assertRaisesRegex(RuntimeError,'identity changed'):
                queue.wait_for_adapter(self.record)


if __name__=='__main__':
    unittest.main()
