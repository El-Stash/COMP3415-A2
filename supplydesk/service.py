"""Operations used by the command-line order desk."""

from supplydesk.storage import JsonStore


class OrderService:
    def __init__(self, state_path=".supplydesk/state.json"):
        self.store = JsonStore(state_path)

    def catalog(self):
        return self.store.load()["catalog"]

    def quote(self, customer_type, items, fulfillment="pickup"):
        partial_quote = self.items_and_price_calc(customer_type, items, fulfillment)
        return {
            "customer_type": customer_type,
            "fulfillment": fulfillment,
            "items": partial_quote["items"],
            "subtotal_cents": partial_quote["subtotal_cents"],
            "discount_cents": partial_quote["discount_cents"],
            "delivery_cents": partial_quote["delivery_cents"],
            "total_cents": partial_quote["total_cents"],
        }

    def place_order(self, customer_type, items, fulfillment="pickup"):
        state = self.store.load()
        partial_quote = self.items_and_price_calc(customer_type, items, fulfillment)
        order = {
            "order_id": "ORD-" + str(state["next_order_number"]).zfill(4),
            "status": "placed",
            "customer_type": customer_type,
            "fulfillment": fulfillment,
            "items": partial_quote["items"],
            "subtotal_cents": partial_quote["subtotal_cents"],
            "discount_cents": partial_quote["discount_cents"],
            "delivery_cents": partial_quote["delivery_cents"],
            "total_cents": partial_quote["total_cents"],
        }
        for line in partial_quote["items"]:
            for product in state["catalog"]:
                if product["product_id"] == line["product_id"]:
                    product["stock"] -= line["quantity"]
        state["next_order_number"] += 1
        state["orders"].append(order)
        self.store.save(state)
        return order

    def list_orders(self):
        return self.store.load()["orders"]

    def get_order(self, order_id):
        state = self.store.load()
        for order in state["orders"]:
            if order["order_id"] == order_id:
                return order
        if order_id == None:
            order_id = ""
        raise ValueError("Unknown order: " + order_id)

    def cancel_order(self, order_id):
        state = self.store.load()
        order = None
        for candidate in state["orders"]:
            if candidate["order_id"] == order_id:
                order = candidate
                break
        if order is None:
            if order_id == None:
                order_id = ""
            raise ValueError("Unknown order: " + order_id)
        if order["status"] != "cancelled":
            for line in order["items"]:
                for product in state["catalog"]:
                    if product["product_id"] == line["product_id"]:
                        product["stock"] += line["quantity"]
            order["status"] = "cancelled"
            self.store.save(state)
        return order

    def items_and_price_calc(self, customer_type, items, fulfillment="pickup"):
        state = self.store.load()
        #invalid input catching
        if customer_type not in ("regular", "student"):
            raise ValueError("Customer type must be regular or student.")
        if fulfillment not in ("pickup", "delivery", "express"):
            #change here probably breaks multiple tests, update for correct message later
            raise ValueError("Fulfillment must be pickup, delivery, or express.")
        if not isinstance(items, list) or not items:
            raise ValueError("An order must contain at least one item.")
        #declaration of lines list and subtotal
        lines = []
        subtotal = 0
        #loop for each input item
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("Each item must contain a product_id and quantity.")
            product = None
            #match item to catalog item
            for candidate in state["catalog"]:
                if candidate["product_id"] == item.get("product_id"):
                    product = candidate
                    break
            #invalid item catching
            if product is None:
                raise ValueError("Unknown product.")
            #quantity declaration
            quantity = item.get("quantity")
            #invalid quantity catching
            if type(quantity) is not int or quantity < 1 or quantity > 99:
                raise ValueError("Quantity must be an integer from 1 to 99.")
            if quantity > product["stock"]:
                raise ValueError("Not enough stock for " + product["product_id"] + ".")
            #add total price of line item to subtotal, add price to lines list
            line_total = product["unit_price_cents"] * quantity
            subtotal += line_total
            lines.append({
                "product_id": product["product_id"],
                "name": product["name"],
                "unit_price_cents": product["unit_price_cents"],
                "quantity": quantity,
                "line_total_cents": line_total,
            })
        #calculate student discount & free delivery when applicable
        discount = 0
        if customer_type == "student" and subtotal > 5000:
            discount = (subtotal * 10 + 50) // 100
        delivery = 0
        if fulfillment == "delivery" and subtotal - discount < 10000:
            delivery = 600
        elif fulfillment == "express":
            delivery = 1200
        #place all results into dict for return
        #customer type & fulfillment not returned since neither has changed
        listAndCosts = {
            "items": lines,
            "subtotal_cents": subtotal,
            "discount_cents": discount,
            "delivery_cents": delivery,
            "total_cents": subtotal - discount + delivery,
        }
        return listAndCosts 

