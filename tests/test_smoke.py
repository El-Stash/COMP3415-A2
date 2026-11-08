"""A small starting test suite for the order desk."""

from pathlib import Path
import tempfile
import unittest

from supplydesk.service import OrderService


class OrderSmokeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "state.json"
        self.service = OrderService(self.path)

    def test_regular_pickup_quote(self):
        quote = self.service.quote("regular", [{"product_id": "notebook", "quantity": 2}])
        self.assertEqual(quote["subtotal_cents"], 1000)
        self.assertEqual(quote["discount_cents"], 0)
        self.assertEqual(quote["delivery_cents"], 0)
        self.assertEqual(quote["total_cents"], 1000)

    def test_student_delivery_quote(self):
        quote = self.service.quote("student", [{"product_id": "hoodie", "quantity": 2}], "delivery")
        self.assertEqual(quote["discount_cents"], 800)
        self.assertEqual(quote["delivery_cents"], 600)
        self.assertEqual(quote["total_cents"], 7800)

    def test_order_can_be_reopened(self):
        order = self.service.place_order("regular", [{"product_id": "mug", "quantity": 1}])
        self.assertEqual(order["order_id"], "ORD-0001")
        self.assertEqual(order["status"], "placed")
        self.assertEqual(OrderService(self.path).get_order(order["order_id"]), order)

    def test_cancel_order_restores_stock(self):
        before = self.service.catalog()
        order = self.service.place_order("regular", [{"product_id": "pen-pack", "quantity": 2}])
        cancelled = self.service.cancel_order(order["order_id"])
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(self.service.catalog(), before)

    #beginning of my testing safety net
    def test_regular_pickup_order(self):
        order = self.service.place_order("regular", [{"product_id": "bag", "quantity": 3}])
        self.assertEqual(order["subtotal_cents"], 7500)
        self.assertEqual(order["discount_cents"], 0)
        self.assertEqual(order["delivery_cents"], 0)
        self.assertEqual(order["total_cents"], 7500)

    def test_student_delivery_order_under_discount(self):
        order = self.service.place_order("student", [{"product_id": "pen-pack", "quantity": 3}], "delivery")
        self.assertEqual(order["subtotal_cents"], 2250)
        self.assertEqual(order["discount_cents"], 0)
        self.assertEqual(order["delivery_cents"], 600)
        self.assertEqual(order["total_cents"], 2850)

if __name__ == "__main__":
    unittest.main()
