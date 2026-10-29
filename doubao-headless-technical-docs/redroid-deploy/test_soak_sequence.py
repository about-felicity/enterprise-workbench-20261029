import unittest
from unittest.mock import patch,MagicMock
import soak_sequence as seq

class AcceptanceGateTests(unittest.TestCase):
    def short(self,**changes):
        state={'status':'passed','duration':3600,'interval':180,'planned':20,
               'enqueued':20,'observed_seconds':3601,'tasks':{'completed':20}}
        state.update(changes)
        return state

    def test_complete_short_run_passes(self):
        self.assertTrue(seq.accepted(self.short(),3600))

    def test_failed_partial_or_wrong_frequency_never_passes(self):
        for change in ({'status':'failed'},{'tasks':{'completed':19,'needs_attention':1}},
                       {'interval':600},{'observed_seconds':3599},{'enqueued':19}):
            with self.subTest(change=change):
                self.assertFalse(seq.accepted(self.short(**change),3600))

    def test_short_results_cannot_pass_long_gate(self):
        self.assertFalse(seq.accepted(self.short(),86400))

    def test_failed_short_stage_does_not_launch_long(self):
        folder=MagicMock()
        folder.__truediv__.return_value=folder
        with patch.object(seq,'ROOT',folder),patch.object(seq,'STAGES',[('short',3600,folder),('long',86400,folder)]), \
             patch.object(seq.json,'loads',return_value={'status':'failed','error':'native fault'}), \
             patch.object(seq,'atomic_json'),patch.object(seq.subprocess,'run') as run:
            self.assertEqual(seq.main(),0)
            run.assert_not_called()

if __name__=='__main__':
    unittest.main()
