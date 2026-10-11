import subprocess
import unittest
from unittest import mock
import ci_kernel_66_probe as kernel
import ci_allocator_implementation as allocator

class GateIntegrationTests(unittest.TestCase):
    def test_successful_preflight_calls_only_audit(self):
        with mock.patch.object(kernel.subprocess,'run',return_value=subprocess.CompletedProcess([],0)) as command:
            kernel.require_board_preflight()
            self.assertEqual(command.call_count,1)
            self.assertEqual(command.call_args.args[0][1],str(kernel.ROOT/'tools/audit_6_6_firstboot.py'))
    def test_real_rejection_propagates_exit_two(self):
        with mock.patch.object(kernel.subprocess,'run',return_value=subprocess.CompletedProcess([],2)):
            with self.assertRaises(SystemExit) as error:kernel.require_board_preflight()
            self.assertEqual(error.exception.code,2)
    def test_all_python_entries_reject_before_side_effects(self):
        for module,entry in ((kernel,kernel.main),(kernel,kernel.build),(allocator,allocator.main)):
            with self.subTest(entry=entry.__qualname__,module=module.__name__),mock.patch.object(module,'require_board_preflight',side_effect=SystemExit(2)) as gate,mock.patch.object(module,'run') as run,mock.patch.object(module.subprocess,'run') as command,mock.patch.object(module.os,'chdir') as chdir:
                with self.assertRaises(SystemExit):entry()
                gate.assert_called_once_with();run.assert_not_called();command.assert_not_called();chdir.assert_not_called()
