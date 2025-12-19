import sys
from pathlib import Path
import unittest
from unittest.mock import patch

# Ensure dashboard package is importable when tests are run from repo root.
TEST_ROOT = Path(__file__).resolve().parents[1]
if str(TEST_ROOT) not in sys.path:
    sys.path.append(str(TEST_ROOT))

from backend.command_state import CommandState, ControlMode


class CommandStateTests(unittest.TestCase):
    def test_teleop_timeout_transitions_to_idle(self):
        cs = CommandState(teleop_timeout=0.5)
        with patch("backend.command_state.time.monotonic", side_effect=[100.0, 100.4, 100.6]):
            cs.update_teleop(0.5, 0.1)  # t=100.0

            v, w, mode = cs.get_current_command()  # t=100.4
            self.assertEqual(mode, ControlMode.TELEOP)
            self.assertAlmostEqual(v, 0.5)
            self.assertAlmostEqual(w, 0.1)

            v, w, mode = cs.get_current_command()  # t=100.6 -> teleop timed out
            self.assertEqual(mode, ControlMode.IDLE)
            self.assertEqual((v, w), (0.0, 0.0))

    def test_teleop_overrides_auto_then_falls_back(self):
        cs = CommandState(teleop_timeout=0.5, auto_timeout=1.0)
        # Calls: update_auto, update_teleop, get (teleop), get (auto), get (idle)
        with patch("backend.command_state.time.monotonic", side_effect=[200.0, 200.1, 200.2, 200.9, 201.1]):
            cs.update_auto(0.2, 0.0)      # t=200.0
            cs.update_teleop(0.5, 0.1)    # t=200.1

            _, _, mode = cs.get_current_command()  # t=200.2
            self.assertEqual(mode, ControlMode.TELEOP)

            v, w, mode = cs.get_current_command()  # t=200.9 -> teleop timed out, auto active
            self.assertEqual(mode, ControlMode.AUTO)
            self.assertAlmostEqual(v, 0.2)
            self.assertAlmostEqual(w, 0.0)

            v, w, mode = cs.get_current_command()  # t=201.1 -> both timed out
            self.assertEqual(mode, ControlMode.IDLE)
            self.assertEqual((v, w), (0.0, 0.0))

    def test_auto_source_used_when_available(self):
        cs = CommandState(teleop_timeout=0.5, auto_timeout=1.0)
        with patch("backend.command_state.time.monotonic", side_effect=[300.0, 300.1, 300.2]):
            cs.update_auto(0.3, -0.05)  # t=300.0

            v, w, mode = cs.get_current_command()  # t=300.1
            self.assertEqual(mode, ControlMode.AUTO)
            self.assertAlmostEqual(v, 0.3)
            self.assertAlmostEqual(w, -0.05)

            snap = cs.get_status_snapshot()  # t=300.2
            self.assertEqual(snap["mode"], ControlMode.AUTO.value)
            self.assertTrue(snap["auto"]["active"])


if __name__ == "__main__":
    unittest.main()
