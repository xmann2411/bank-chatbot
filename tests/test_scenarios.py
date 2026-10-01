"""Svi razgovori iz scripts/run_scenarios.py kao test (simulirani mod, lažna tečajna lista)."""

import unittest
from unittest import mock

from bankbot import fx, llm
from scripts.run_scenarios import SCENARIOS, run_scenario
from tests.test_agent import FAKE_RATES


@mock.patch.object(llm, "MODE", "simulated")
@mock.patch.object(fx, "get_rates", lambda day=None: FAKE_RATES)
class ScenarioTest(unittest.TestCase):
    def test_all_scenarios(self):
        for group, name, turns in SCENARIOS:
            with self.subTest(f"{group}: {name}"):
                _, failures = run_scenario(turns)
                self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
