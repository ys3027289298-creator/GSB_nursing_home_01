import unittest

import core


class TestCore(unittest.TestCase):
    def test_01_no_duplicate_admit(self):
        state = core.new_game()
        self.assertTrue(core.admit(state, "E1"))
        self.assertFalse(core.admit(state, "E1"))

    def test_02_no_admit_when_full(self):
        state = core.new_game()
        core.admit(state, "E1")
        core.admit(state, "E2")
        result = core.admit(state, "E3")
        self.assertFalse(result)

    def test_03_fee_exact(self):
        state = core.new_game()
        self.assertEqual(core.fee(state, "E1", 4), 3)

    def test_04_cancel_care_refunds_medicine(self):
        state = core.new_game()
        state["medicine"] = 40
        core.cancel_care(state, "E1")
        self.assertEqual(state["medicine"], 50)

    def test_05_no_schedule_with_absent_nurse(self):
        state = core.new_game()
        result = core.schedule(state, "E1", "N2")
        self.assertFalse(result)

    def test_06_medicate_failure_no_cost(self):
        state = core.new_game()
        state["medicine"] = 0
        result = core.medicate(state, "E1")
        self.assertFalse(result)
        self.assertEqual(state["medicine"], 0)

    def test_07_fall_deducts_health_once(self):
        state = core.new_game()
        core.admit(state, "E1")
        state["elders"]["E1"]["health"] = 80
        core.fall(state, "E1")
        self.assertEqual(state["elders"]["E1"]["health"], 70)

    def test_08_load_preserves_shift(self):
        state = core.new_game()
        state["shift_id"] = 3
        loaded = core.load_state(core.save_state(state))
        self.assertEqual(loaded["shift_id"], 3)


if __name__ == "__main__":
    unittest.main()
