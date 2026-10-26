import unittest

from src.statement_service import Order, StatementRequest, eligible_orders, statement_html


class StatementDecisionTest(unittest.TestCase):
    def test_only_fulfilled_orders_with_issued_receipts_are_billed(self):
        request = StatementRequest("customer-1", "2026-10", (
            Order("ready", "Preset", 1, 10, "fulfilled", "issued"),
            Order("moving", "Print", 1, 20, "packed", "issued"),
            Order("unpaid", "Strap", 1, 30, "fulfilled", "pending"),
        ))

        self.assertEqual([order.order_id for order in eligible_orders(request)], ["ready"])
        html = statement_html(request)
        self.assertIn("$10.00", html)
        self.assertNotIn("moving", html)
        self.assertNotIn("unpaid", html)


if __name__ == "__main__":
    unittest.main()
