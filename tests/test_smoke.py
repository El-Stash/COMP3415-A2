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

    def test_student_delivery_order_over_discount(self):
        order = self.service.place_order("student", [{"product_id": "notebook", "quantity": 11}], "delivery")
        self.assertEqual(order["subtotal_cents"], 5500)
        self.assertEqual(order["discount_cents"], 550)
        self.assertEqual(order["delivery_cents"], 600)
        self.assertEqual(order["total_cents"], 5550)

    def test_regular_pickup_order_multiple_items(self):
        order = self.service.place_order("regular", [{"product_id": "notebook", "quantity": 1}, {"product_id": "hoodie", "quantity": 1}])
        self.assertEqual(order["subtotal_cents"], 4500)
        self.assertEqual(order["discount_cents"], 0)
        self.assertEqual(order["delivery_cents"], 0)
        self.assertEqual(order["total_cents"], 4500)
        self.assertEqual(order["items"][0]["product_id"], "notebook")
        self.assertEqual(order["items"][1]["product_id"], "hoodie")

    def test_student_delivery_order_multiple_items(self):
        order = self.service.place_order("student", [{"product_id": "pen-pack", "quantity": 4}, {"product_id": "mug", "quantity": 2}], "delivery")
        self.assertEqual(order["subtotal_cents"], 6000)
        self.assertEqual(order["discount_cents"], 600)
        self.assertEqual(order["delivery_cents"], 600)
        self.assertEqual(order["total_cents"], 6000)
        self.assertEqual(order["items"][0]["product_id"], "pen-pack")
        self.assertEqual(order["items"][1]["product_id"], "mug")

    def test_regular_delivery_order_free_delivery_qualified(self):
        order = self.service.place_order("regular", [{"product_id": "hoodie", "quantity": 3}], "delivery")
        self.assertEqual(order["subtotal_cents"], 12000)
        self.assertEqual(order["discount_cents"], 0)
        self.assertEqual(order["delivery_cents"], 0)
        self.assertEqual(order["total_cents"], 12000)

    def test_regular_pickup_none_quote(self):
        with self.assertRaises(ValueError) as context:
            self.service.quote("regular", None)
        self.assertEqual(str(context.exception), "An order must contain at least one item.")

    def test_regular_pickup_empty_quote(self):
        with self.assertRaises(ValueError) as context:
            self.service.quote("regular", [])
        self.assertEqual(str(context.exception), "An order must contain at least one item.")

    def test_regular_pickup_zero_quote(self):
        with self.assertRaises(ValueError) as context:
            self.service.quote("regular", [{"product_id": "notebook", "quantity": 0}])
        self.assertEqual(str(context.exception), "Quantity must be an integer from 1 to 99.")

    def test_regular_pickup_none_order(self):
        with self.assertRaises(ValueError) as context:
            self.service.place_order("regular", None)
        self.assertEqual(str(context.exception), "An order must contain at least one item.")

    def test_regular_pickup_empty_order(self):
        with self.assertRaises(ValueError) as context:
            self.service.place_order("regular", [])
        self.assertEqual(str(context.exception), "An order must contain at least one item.")

    def test_regular_pickup_zero_order(self):
        with self.assertRaises(ValueError) as context:
            self.service.place_order("regular", [{"product_id": "notebook", "quantity": 0}])
        self.assertEqual(str(context.exception), "Quantity must be an integer from 1 to 99.")

    def test_regular_pickup_max_of_an_item_quote(self):
        quote = self.service.quote("regular", [{"product_id": "notebook", "quantity": 20}])
        self.assertEqual(quote["items"][0]["product_id"], "notebook")

    def test_regular_pickup_max_of_an_item_order(self):
        order = self.service.place_order("regular", [{"product_id": "notebook", "quantity": 20}])
        self.assertEqual(order["order_id"], "ORD-0001")
        self.assertEqual(order["status"], "placed")

    def test_student_pickup_just_below_discount_quote(self):
        order = self.service.quote("regular", [{"product_id": "bag", "quantity": 2}])
        self.assertEqual(order["subtotal_cents"], 5000)
        self.assertEqual(order["discount_cents"], 0)
        self.assertEqual(order["delivery_cents"], 0)
        self.assertEqual(order["total_cents"], 5000)

    def test_student_pickup_just_below_discount_order(self):
        order = self.service.place_order("regular", [{"product_id": "bag", "quantity": 2}])
        self.assertEqual(order["subtotal_cents"], 5000)
        self.assertEqual(order["discount_cents"], 0)
        self.assertEqual(order["delivery_cents"], 0)
        self.assertEqual(order["total_cents"], 5000)

    def test_regular_delivery_order_just_barely_free_delivery(self):
        order = self.service.place_order("regular", [{"product_id": "bag", "quantity": 4}], "delivery")
        self.assertEqual(order["subtotal_cents"], 10000)
        self.assertEqual(order["discount_cents"], 0)
        self.assertEqual(order["delivery_cents"], 0)
        self.assertEqual(order["total_cents"], 10000)

    def test_none_customer_type_quote(self):
        with self.assertRaises(ValueError) as context:
            self.service.quote(None, [{"product_id": "notebook", "quantity": 5}])
        self.assertEqual(str(context.exception), "Customer type must be regular or student.")

    def test_invalid_customer_type_quote(self):
        with self.assertRaises(ValueError) as context:
            self.service.quote("theif", [{"product_id": "notebook", "quantity": 5}])
        self.assertEqual(str(context.exception), "Customer type must be regular or student.")

    def test_none_customer_type_order(self):
        with self.assertRaises(ValueError) as context:
            self.service.place_order(None, [{"product_id": "notebook", "quantity": 5}])
        self.assertEqual(str(context.exception), "Customer type must be regular or student.")

    def test_invalid_customer_type_order(self):
        with self.assertRaises(ValueError) as context:
            self.service.place_order("theif", [{"product_id": "notebook", "quantity": 5}])
        self.assertEqual(str(context.exception), "Customer type must be regular or student.")

    def test_none_fulfillment_quote(self):
        with self.assertRaises(ValueError) as context:
            self.service.quote("regular", [{"product_id": "notebook", "quantity": 5}], None)
        self.assertEqual(str(context.exception), "Fulfillment must be pickup or delivery.")

    def test_invalid_fulfillment_order(self):
        with self.assertRaises(ValueError) as context:
            self.service.place_order("regular", [{"product_id": "notebook", "quantity": 5}], "air-drop")
        self.assertEqual(str(context.exception), "Fulfillment must be pickup or delivery.")

    def test_none_items_quote(self):
        with self.assertRaises(ValueError) as context:
            self.service.quote("regular", [None])
        self.assertEqual(str(context.exception), "Each item must contain a product_id and quantity.")

    def test_invalid_items_quote(self):
        with self.assertRaises(ValueError) as context:
            self.service.quote("regular", ["not_a_shopping_list"])
        self.assertEqual(str(context.exception), "Each item must contain a product_id and quantity.")

    def test_none_items_order(self):
        with self.assertRaises(ValueError) as context:
            self.service.place_order("regular", [None])
        self.assertEqual(str(context.exception), "Each item must contain a product_id and quantity.")

    def test_invalid_items_order(self):
        with self.assertRaises(ValueError) as context:
            self.service.place_order("regular", ["not_a_shopping_list"])
        self.assertEqual(str(context.exception), "Each item must contain a product_id and quantity.")

    def test_empty_product_quote(self):
        with self.assertRaises(ValueError) as context:
            self.service.quote("regular", [{}])
        self.assertEqual(str(context.exception), "Unknown product.")

    def test_none_product_quote(self):
        with self.assertRaises(ValueError) as context:
            self.service.quote("regular", [{None}])
        self.assertEqual(str(context.exception), "Each item must contain a product_id and quantity.")

    def test_invalid_product_quote(self):
        with self.assertRaises(ValueError) as context:
            self.service.quote("regular", [{"product": "laptop"}])
        self.assertEqual(str(context.exception), "Unknown product.")

    def test_empty_product_order(self):
        with self.assertRaises(ValueError) as context:
            self.service.place_order("regular", [{}])
        self.assertEqual(str(context.exception), "Unknown product.")

    def test_none_product_order(self):
        with self.assertRaises(ValueError) as context:
            self.service.place_order("regular", [{None}])
        self.assertEqual(str(context.exception), "Each item must contain a product_id and quantity.")

    def test_invalid_product_order(self):
        with self.assertRaises(ValueError) as context:
            self.service.place_order("regular", [{"product_id": "laptop"}])
        self.assertEqual(str(context.exception), "Unknown product.")

    def test_empty_quantity_quote(self):
        with self.assertRaises(ValueError) as context:
            self.service.quote("regular", [{"product_id": "notebook"}])
        self.assertEqual(str(context.exception), "Quantity must be an integer from 1 to 99.")

    def test_none_quantity_quote(self):
        with self.assertRaises(ValueError) as context:
            self.service.quote("regular", [{"product_id": "notebook", "quantity": None}])
        self.assertEqual(str(context.exception), "Quantity must be an integer from 1 to 99.")

    def test_invalid_type_quantity_quote(self):
        with self.assertRaises(ValueError) as context:
            self.service.quote("regular", [{"product_id": "notebook", "quantity": "one"}])
        self.assertEqual(str(context.exception), "Quantity must be an integer from 1 to 99.")

    def test_invalid_low_quantity_quote(self):
        with self.assertRaises(ValueError) as context:
            self.service.quote("regular", [{"product_id": "notebook", "quantity": -1}])
        self.assertEqual(str(context.exception), "Quantity must be an integer from 1 to 99.")

    def test_invalid_high_quantity_quote(self):
        with self.assertRaises(ValueError) as context:
            self.service.quote("regular", [{"product_id": "notebook", "quantity": 100}])
        self.assertEqual(str(context.exception), "Quantity must be an integer from 1 to 99.")

    def test_empty_quantity_order(self):
        with self.assertRaises(ValueError) as context:
            self.service.place_order("regular", [{"product_id": "notebook"}])
        self.assertEqual(str(context.exception), "Quantity must be an integer from 1 to 99.")

    def test_none_quantity_order(self):
        with self.assertRaises(ValueError) as context:
            self.service.place_order("regular", [{"product_id": "notebook", "quantity": None}])
        self.assertEqual(str(context.exception), "Quantity must be an integer from 1 to 99.")

    def test_invalid_type_quantity_order(self):
        with self.assertRaises(ValueError) as context:
            self.service.place_order("regular", [{"product_id": "notebook", "quantity": "one"}])
        self.assertEqual(str(context.exception), "Quantity must be an integer from 1 to 99.")

    def test_invalid_low_quantity_order(self):
        with self.assertRaises(ValueError) as context:
            self.service.place_order("regular", [{"product_id": "notebook", "quantity": -1}])
        self.assertEqual(str(context.exception), "Quantity must be an integer from 1 to 99.")

    def test_invalid_high_quantity_order(self):
        with self.assertRaises(ValueError) as context:
            self.service.place_order("regular", [{"product_id": "notebook", "quantity": 100}])
        self.assertEqual(str(context.exception), "Quantity must be an integer from 1 to 99.")

    def test_insifficient_stock_quote(self):
        with self.assertRaises(ValueError) as context:
            self.service.quote("regular", [{"product_id": "notebook", "quantity": 21}])
        self.assertEqual(str(context.exception), "Not enough stock for notebook.")

    def test_insifficient_stock_quote(self):
        with self.assertRaises(ValueError) as context:
            self.service.place_order("regular", [{"product_id": "notebook", "quantity": 21}])
        self.assertEqual(str(context.exception), "Not enough stock for notebook.")

    #this test fails, because None cannot be concatenated to a string, possible edge case issue detected
    def test_get_none_order(self):
        with self.assertRaises(ValueError) as context:
            OrderService(self.path).get_order(None)
        self.assertEqual(str(context.exception), "Unknown order: ")

    def test_get_invalid_order(self):
        with self.assertRaises(ValueError) as context:
            OrderService(self.path).get_order("")
        self.assertEqual(str(context.exception), "Unknown order: ")

    def test_get_invalid_order(self):
        with self.assertRaises(ValueError) as context:
            OrderService(self.path).get_order("ORD-0128")
        self.assertEqual(str(context.exception), "Unknown order: ORD-0128")

    #this test fails, because None cannot be concatenated to a string, possible edge case issue detected
    def test_cancel_none_order(self):
        with self.assertRaises(ValueError) as context:
            OrderService(self.path).cancel_order(None)
        self.assertEqual(str(context.exception), "Unknown order: ")

    def test_cancel_invalid_order(self):
        with self.assertRaises(ValueError) as context:
            OrderService(self.path).cancel_order("ORD-0128")
        self.assertEqual(str(context.exception), "Unknown order: ORD-0128")

    #test fails, orders cancelled twice create extra stock from nothing
    #critical flaw that must be resolved
    def test_cancelling_order_twice_does_not_create_extra_stock(self):
        before = self.service.catalog()
        order = self.service.place_order("regular", [{"product_id": "pen-pack", "quantity": 2}])
        cancelled = self.service.cancel_order(order["order_id"])
        self.assertEqual(cancelled["status"], "cancelled")
        self.service.cancel_order(order["order_id"])
        self.assertEqual(self.service.catalog(), before)

if __name__ == "__main__":
    unittest.main()
