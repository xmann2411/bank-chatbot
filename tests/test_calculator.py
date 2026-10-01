import unittest

from bankbot.calculator import LoanError, annuity, calculate, find_rate


class RateLookupTest(unittest.TestCase):
    def test_cash_citizen_bands(self):
        self.assertEqual(find_rate("gotovinski", "drzavljanin", 10000, 36), 6.49)
        self.assertEqual(find_rate("gotovinski", "drzavljanin", 10001, 36), 5.99)
        self.assertEqual(find_rate("gotovinski", "drzavljanin", 10000, 37), 6.79)
        self.assertEqual(find_rate("gotovinski", "drzavljanin", 40000, 120), 6.69)

    def test_non_citizen_pays_more(self):
        for amount, months in [(5000, 24), (20000, 60), (40000, 120)]:
            self.assertGreater(
                find_rate("gotovinski", "nedrzavljanin", amount, months),
                find_rate("gotovinski", "drzavljanin", amount, months),
            )

    def test_housing_not_for_non_citizens(self):
        with self.assertRaises(LoanError) as ctx:
            find_rate("stambeni", "nedrzavljanin", 100000, 240)
        self.assertEqual(ctx.exception.code, "not_available_for_client")

    def test_limits(self):
        with self.assertRaises(LoanError) as ctx:
            find_rate("gotovinski", "drzavljanin", 50000, 60)
        self.assertEqual(ctx.exception.code, "amount_out_of_range")
        with self.assertRaises(LoanError) as ctx:
            find_rate("stambeni", "drzavljanin", 100000, 480)
        self.assertEqual(ctx.exception.code, "term_out_of_range")


class AnnuityTest(unittest.TestCase):
    def test_known_value(self):
        # 15.000 EUR, 6,29 %, 60 mjeseci
        self.assertAlmostEqual(annuity(15000, 6.29, 60), 292.02, places=2)

    def test_zero_rate(self):
        self.assertEqual(annuity(1200, 0, 12), 100)

    def test_schedule_repays_principal(self):
        r = calculate("stambeni", "drzavljanin", 200000, 240)
        self.assertEqual(len(r.schedule), 240)
        self.assertEqual(r.schedule[-1]["ostatak"], 0)
        self.assertAlmostEqual(sum(x["glavnica"] for x in r.schedule), 200000, places=2)
        self.assertAlmostEqual(r.total_paid, r.amount + r.total_interest, places=2)
        # Sve rate osim zadnje su jednake anuitetu.
        self.assertTrue(all(x["rata"] == r.monthly_payment for x in r.schedule[:-1]))


if __name__ == "__main__":
    unittest.main()
