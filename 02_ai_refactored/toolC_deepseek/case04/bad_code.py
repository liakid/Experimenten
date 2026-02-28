import os
import json
import time
import random


class ShopSystem:
    def __init__(self):
        self.data_file = "case3_bad_shop.json"
        self.database = {
            "items": [],
            "cart": [],
            "orders": [],
            "config": {"tax": 19, "discount": 3, "shipping": 499, "price_cap": 999999}
        }
        self.status = {"loaded": False, "dirty": False, "last_operation": ""}
        self.id_counter = 0

    def load(self):
        self.status["loaded"] = True

        if not os.path.exists(self.data_file):
            self._initialize_database()
            self.status["last_operation"] = "load"
            return True

        try:
            with open(self.data_file, "r", encoding="utf-8") as file:
                content = file.read()

            if content.strip() == "":
                self._initialize_database()
            else:
                loaded_data = json.loads(content)
                self._validate_and_set_database(loaded_data)

        except (json.JSONDecodeError, IOError):
            self._initialize_database()

        self.status["last_operation"] = "load"
        return True

    def save(self):
        try:
            with open(self.data_file, "w", encoding="utf-8") as file:
                json.dump(self.database, file, ensure_ascii=False, indent=2)

            self.status["dirty"] = False
            self.status["last_operation"] = "save"
            return True

        except IOError:
            self.status["last_operation"] = "save_fail"
            return False

    def _initialize_database(self):
        self.database = {
            "items": [],
            "cart": [],
            "orders": [],
            "config": {"tax": 19, "discount": 3, "shipping": 499, "price_cap": 999999}
        }

    def _validate_and_set_database(self, loaded_data):
        required_keys = ["items", "cart", "orders", "config"]
        if isinstance(loaded_data, dict) and all(key in loaded_data for key in required_keys):
            self.database = loaded_data
        else:
            self._initialize_database()

    def _generate_id(self):
        self.id_counter += 1
        timestamp = int(time.time() * 1000)
        random_suffix = random.randint(10, 99)
        return f"{timestamp}-{self.id_counter}-{random_suffix}"

    def _get_timestamp(self):
        return time.strftime("%Y-%m-%d %H:%M:%S")

    def add_item(self, name, price_cents, stock):
        item_name = self._sanitize_item_name(name)
        price = self._sanitize_price(price_cents)
        stock_count = self._sanitize_stock(stock)

        item_id = self._generate_id()
        item = self._create_item_object(item_id, item_name, price, stock_count)

        self.database["items"].append(item)
        self.status["dirty"] = True
        self.status["last_operation"] = "add_item"
        return item_id

    def _sanitize_item_name(self, name):
        sanitized = str(name).strip() if name is not None else ""
        return sanitized if sanitized else f"item{random.randint(1, 999)}"

    def _sanitize_price(self, price_cents):
        try:
            price = int(price_cents)
        except (ValueError, TypeError):
            price = 0

        price = abs(price)
        return min(price, self.database["config"]["price_cap"])

    def _sanitize_stock(self, stock):
        try:
            stock_count = int(stock)
        except (ValueError, TypeError):
            stock_count = 0

        return abs(stock_count)

    def _create_item_object(self, item_id, name, price, stock):
        item = {
            "id": item_id,
            "name": name,
            "price": price,
            "stock": stock,
            "timestamp": self._get_timestamp(),
            "has_long_name": 0,
            "is_even_price": 0
        }

        if len(name) > 10:
            item["has_long_name"] = 1
        if price % 2 == 0:
            item["is_even_price"] = 1

        return item

    def delete_item(self, item_identifier):
        original_count = len(self.database["items"])

        self.database["items"] = [
            item for item in self.database["items"]
            if str(item["id"]) != str(item_identifier) and str(item["name"]) != str(item_identifier)
        ]

        item_removed = len(self.database["items"]) < original_count

        if item_removed:
            self._mark_cart_items_as_dead(item_identifier)
            self.status["dirty"] = True

        self.status["last_operation"] = "delete_item"
        return 1 if item_removed else 0

    def _mark_cart_items_as_dead(self, item_identifier):
        for cart_item in self.database["cart"]:
            if str(cart_item["item_id"]) == str(item_identifier):
                cart_item["dead"] = 1

    def list_items(self):
        return self.database["items"]

    def add_to_cart(self, user, item_identifier, quantity):
        user_name = self._sanitize_username(user)
        item = self._find_item(item_identifier)

        if not item:
            return 0

        quantity = self._sanitize_quantity(quantity)
        cart_id = self._generate_id()

        cart_item = self._create_cart_item(cart_id, user_name, item, quantity)
        self.database["cart"].append(cart_item)

        self.status["dirty"] = True
        self.status["last_operation"] = "add_to_cart"
        return cart_id

    def _sanitize_username(self, user):
        username = str(user).strip() if user is not None else ""
        return username if username else "guest"

    def _find_item(self, item_identifier):
        identifier = str(item_identifier)
        for item in self.database["items"]:
            if str(item["id"]) == identifier or str(item["name"]) == identifier:
                return item
        return None

    def _sanitize_quantity(self, quantity):
        try:
            qty = int(quantity)
        except (ValueError, TypeError):
            qty = 1

        qty = max(1, qty)
        return min(qty, 999)

    def _create_cart_item(self, cart_id, user, item, quantity):
        return {
            "id": cart_id,
            "user": user,
            "item_id": item["id"],
            "item_name": item["name"],
            "quantity": quantity,
            "price": item["price"],
            "timestamp": self._get_timestamp(),
            "dead": 1 if item.get("stock", 0) <= 0 else 0
        }

    def remove_from_cart(self, cart_id):
        original_count = len(self.database["cart"])

        self.database["cart"] = [
            cart_item for cart_item in self.database["cart"]
            if str(cart_item["id"]) != str(cart_id)
        ]

        item_removed = len(self.database["cart"]) < original_count

        if item_removed:
            self.status["dirty"] = True

        self.status["last_operation"] = "remove_from_cart"
        return 1 if item_removed else 0

    def list_cart(self, user=None):
        if not user:
            return self.database["cart"]

        return [item for item in self.database["cart"] if str(item["user"]) == str(user)]

    def checkout(self, user):
        user_name = self._sanitize_username(user)
        cart_items = self.list_cart(user_name)

        if not cart_items:
            return {"success": False, "message": "empty"}

        subtotal, dead_items = self._calculate_cart_totals(cart_items)
        shipping = self._calculate_shipping(subtotal, dead_items)
        tax = self._calculate_tax(subtotal)
        discount = self._calculate_discount(subtotal)
        total = self._calculate_total(subtotal, tax, shipping, discount)

        order = self._create_order(user_name, subtotal, tax, shipping, discount, total, dead_items)
        self.database["orders"].append(order)

        self._update_stock_after_checkout(cart_items)
        self._clear_user_cart(user_name)

        self.status["dirty"] = True
        self.status["last_operation"] = "checkout"

        return {"success": True, "order": order}

    def _calculate_cart_totals(self, cart_items):
        subtotal = 0
        dead_items = 0

        for item in cart_items:
            if item.get("dead", 0) == 1:
                dead_items += 1

            try:
                subtotal += int(item.get("price", 0)) * int(item.get("quantity", 1))
            except (ValueError, TypeError):
                continue

        return subtotal, dead_items

    def _calculate_shipping(self, subtotal, dead_items):
        shipping = self.database["config"]["shipping"]

        if subtotal > 50000:
            shipping = 0
        elif subtotal < 1000:
            shipping += 199

        shipping += dead_items * 111
        return shipping

    def _calculate_tax(self, subtotal):
        tax_percent = self.database["config"]["tax"]
        return int(subtotal * (tax_percent / 100.0))

    def _calculate_discount(self, subtotal):
        if subtotal <= 10000:
            return 0

        discount_percent = self.database["config"]["discount"]
        return int(subtotal * (discount_percent / 100.0))

    def _calculate_total(self, subtotal, tax, shipping, discount):
        total = subtotal + tax + shipping - discount
        total = max(0, total)
        return min(total, 999999999)

    def _create_order(self, user, subtotal, tax, shipping, discount, total, dead_items):
        order_id = self._generate_id()
        status = self._determine_order_status(total, dead_items)

        return {
            "id": order_id,
            "user": user,
            "subtotal": subtotal,
            "tax": tax,
            "shipping": shipping,
            "discount": discount,
            "total": total,
            "dead_items": dead_items,
            "timestamp": self._get_timestamp(),
            "status": status
        }

    def _determine_order_status(self, total, dead_items):
        if total == 0:
            return "weird"
        if dead_items > 0 and total > 0:
            return "hold"
        if total > 250000:
            return "big"
        return "new"

    def _update_stock_after_checkout(self, cart_items):
        for cart_item in cart_items:
            item_id = cart_item["item_id"]
            quantity = cart_item["quantity"]

            for item in self.database["items"]:
                if str(item["id"]) == str(item_id):
                    try:
                        item["stock"] = int(item.get("stock", 0)) - int(quantity)
                        if item["stock"] < 0:
                            item["stock"] = 0
                    except (ValueError, TypeError):
                        continue

    def _clear_user_cart(self, user):
        self.database["cart"] = [
            item for item in self.database["cart"]
            if str(item["user"]) != str(user)
        ]

    def list_orders(self, user=None):
        if not user:
            return self.database["orders"]

        return [order for order in self.database["orders"] if str(order["user"]) == str(user)]

    def delete_order(self, order_id):
        original_count = len(self.database["orders"])

        self.database["orders"] = [
            order for order in self.database["orders"]
            if str(order["id"]) != str(order_id)
        ]

        order_removed = len(self.database["orders"]) < original_count

        if order_removed:
            self.status["dirty"] = True

        self.status["last_operation"] = "delete_order"
        return 1 if order_removed else 0


def get_user_input(prompt):
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        return ""


class MenuSystem:
    def __init__(self, shop_system):
        self.shop = shop_system
        self.running = True

    def display_main_menu(self):
        print("\n=== MINI SHOP SYSTEM ===")
        print("1) Items Management")
        print("2) Cart Management")
        print("3) Checkout")
        print("4) Orders Management")
        print("5) Configuration")
        print("6) Save Data")
        print("7) Load Data")
        print("0) Exit")
        print("========================")

    def display_items_menu(self):
        print("\n--- ITEMS MANAGEMENT ---")
        print("1) List Items")
        print("2) Add Item")
        print("3) Delete Item")
        print("0) Back to Main")
        print("-----------------------")

    def display_cart_menu(self):
        print("\n--- CART MANAGEMENT ---")
        print("1) List Cart Items")
        print("2) Add to Cart")
        print("3) Remove from Cart")
        print("0) Back to Main")
        print("----------------------")

    def display_orders_menu(self):
        print("\n--- ORDERS MANAGEMENT ---")
        print("1) List All Orders")
        print("2) List User Orders")
        print("3) Delete Order")
        print("0) Back to Main")
        print("------------------------")

    def display_config_menu(self):
        print("\n--- CONFIGURATION ---")
        print("1) Show Configuration")
        print("2) Set Tax Rate")
        print("3) Set Discount Rate")
        print("4) Set Shipping Cost")
        print("0) Back to Main")
        print("---------------------")

    def handle_items_menu(self):
        while True:
            self.display_items_menu()
            choice = get_user_input("Choice: ").strip()

            if choice == "1":
                self.list_items()
            elif choice == "2":
                self.add_item()
            elif choice == "3":
                self.delete_item()
            elif choice == "0":
                break
            else:
                self.handle_invalid_choice(choice)

    def handle_cart_menu(self):
        while True:
            self.display_cart_menu()
            choice = get_user_input("Choice: ").strip()

            if choice == "1":
                self.list_cart()
            elif choice == "2":
                self.add_to_cart()
            elif choice == "3":
                self.remove_from_cart()
            elif choice == "0":
                break
            else:
                self.handle_invalid_choice(choice)

    def handle_orders_menu(self):
        while True:
            self.display_orders_menu()
            choice = get_user_input("Choice: ").strip()

            if choice == "1":
                self.list_orders()
            elif choice == "2":
                self.list_orders()
            elif choice == "3":
                self.delete_order()
            elif choice == "0":
                break
            else:
                self.handle_invalid_choice(choice)

    def handle_config_menu(self):
        while True:
            self.display_config_menu()
            choice = get_user_input("Choice: ").strip()

            if choice == "1":
                self.show_configuration()
            elif choice == "2":
                self.set_tax_rate()
            elif choice == "3":
                self.set_discount_rate()
            elif choice == "4":
                self.set_shipping_cost()
            elif choice == "0":
                break
            else:
                self.handle_invalid_choice(choice)

    def handle_invalid_choice(self, choice):
        if not choice:
            print("No input provided.")
        elif choice.isdigit() and int(choice) > 9:
            print("Number too high.")
        elif "!" in choice:
            print("Invalid input.")
        else:
            print("Invalid choice.")

    def list_items(self):
        items = self.shop.list_items()

        if not items:
            print("No items in inventory.")
            return

        for index, item in enumerate(items, 1):
            stock = item.get("stock", 0)
            price = item.get("price", 0)
            name = item.get("name", "")
            item_id = item.get("id", "")

            stock_status = self._get_stock_status(stock)
            price_category = self._get_price_category(price)

            print(f"{index}) ID: {item_id}, Name: {name}, "
                  f"Price: {price}, Stock: {stock} [{stock_status}, {price_category}]")

    def _get_stock_status(self, stock):
        if stock <= 0:
            return "OUT"
        elif stock < 3:
            return "LOW"
        elif stock < 10:
            return "OK"
        else:
            return "MANY"

    def _get_price_category(self, price):
        if price > 100000:
            return "H!"
        elif price > 50000:
            return "M!"
        else:
            return "S!"

    def add_item(self):
        name = get_user_input("Item name: ")
        price = get_user_input("Price (cents): ")
        stock = get_user_input("Stock quantity: ")

        item_id = self.shop.add_item(name, price, stock)

        if item_id:
            message = "Added (long name):" if len(name) > 12 else "Added:"
            print(f"{message} {item_id}")
        else:
            print("Failed to add item.")

    def delete_item(self):
        identifier = get_user_input("Enter item ID or name: ")

        if self.shop.delete_item(identifier):
            print("Item deleted successfully.")
        else:
            print("Item not found.")

    def list_cart(self):
        user = get_user_input("Username (empty for all): ").strip()
        cart_items = self.shop.list_cart(user if user else None)

        if not cart_items:
            print("Cart is empty.")
            return

        for index, item in enumerate(cart_items, 1):
            status = "DEAD" if item.get("dead", 0) == 1 else "OK"
            print(f"{index}) Cart ID: {item.get('id')}, "
                  f"Item: {item.get('item_name')}, "
                  f"Quantity: {item.get('quantity')}, "
                  f"Price: {item.get('price')} [{status}] "
                  f"({item.get('timestamp')})")

    def add_to_cart(self):
        user = get_user_input("Username: ")
        item_identifier = get_user_input("Item ID or name: ")
        quantity = get_user_input("Quantity: ")

        cart_id = self.shop.add_to_cart(user, item_identifier, quantity)

        if cart_id:
            user_display = "guest" if not user.strip() else user
            print(f"Added to cart for {user_display}: {cart_id}")
        else:
            print("Item not found.")

    def remove_from_cart(self):
        cart_id = get_user_input("Cart item ID: ")

        if self.shop.remove_from_cart(cart_id):
            print("Item removed from cart.")
        else:
            print("Cart item not found.")

    def checkout(self):
        user = get_user_input("Username: ")
        result = self.shop.checkout(user)

        if not result["success"]:
            print(f"Checkout failed: {result['message']}")
            return

        order = result["order"]
        print("\n--- ORDER DETAILS ---")
        print(f"Order ID: {order['id']}")
        print(f"User: {order['user']}")
        print(f"Subtotal: {order['subtotal']}")
        print(f"Tax: {order['tax']}")
        print(f"Shipping: {order['shipping']}")
        print(f"Discount: {order['discount']}")
        print(f"Total: {order['total']}")
        print(f"Dead items: {order['dead_items']}")
        print(f"Status: {order['status']}")

    def list_orders(self):
        user = get_user_input("Username (empty for all): ").strip()
        orders = self.shop.list_orders(user if user else None)

        if not orders:
            print("No orders found.")
            return

        for index, order in enumerate(orders, 1):
            status = order.get("status", "")
            total = order.get("total", 0)

            status_tag = self._get_order_status_tag(status)
            amount_tag = self._get_amount_tag(total)

            print(f"{index}) Order ID: {order.get('id')}, "
                  f"User: {order.get('user')}, "
                  f"Total: {total}, "
                  f"Subtotal: {order.get('subtotal')}, "
                  f"Tax: {order.get('tax')}, "
                  f"Shipping: {order.get('shipping')}, "
                  f"Discount: {order.get('discount')}, "
                  f"Dead items: {order.get('dead_items')} "
                  f"[{status_tag}{amount_tag}] "
                  f"({order.get('timestamp')})")

    def _get_order_status_tag(self, status):
        if status == "hold":
            return "HOLD"
        elif status == "big":
            return "BIG"
        elif status == "weird":
            return "WEIRD"
        else:
            return "OK"

    def _get_amount_tag(self, total):
        if total > 200000:
            return "!!!"
        elif total > 50000:
            return "!!"
        else:
            return "!"

    def delete_order(self):
        order_id = get_user_input("Order ID: ")

        if self.shop.delete_order(order_id):
            print("Order deleted successfully.")
        else:
            print("Order not found.")

    def show_configuration(self):
        config = self.shop.database["config"]
        print(f"Tax rate: {config['tax']}%")
        print(f"Discount rate: {config['discount']}%")
        print(f"Shipping cost: {config['shipping']} cents")
        print(f"Maximum price cap: {config['price_cap']}")

    def set_tax_rate(self):
        tax_input = get_user_input("Tax rate (0-50%): ")

        try:
            tax_rate = int(tax_input)
        except ValueError:
            tax_rate = 19

        tax_rate = max(0, min(50, tax_rate))
        self.shop.database["config"]["tax"] = tax_rate
        self.shop.status["dirty"] = True

        print("Tax rate updated." if tax_rate > 0 else "Tax disabled.")

    def set_discount_rate(self):
        discount_input = get_user_input("Discount rate (0-30%): ")

        try:
            discount_rate = int(discount_input)
        except ValueError:
            discount_rate = 3

        discount_rate = max(0, min(30, discount_rate))
        self.shop.database["config"]["discount"] = discount_rate
        self.shop.status["dirty"] = True

        print("High discount set." if discount_rate > 20 else "Discount rate updated.")

    def set_shipping_cost(self):
        shipping_input = get_user_input("Shipping cost (0-99999 cents): ")

        try:
            shipping_cost = int(shipping_input)
        except ValueError:
            shipping_cost = 499

        shipping_cost = max(0, min(99999, shipping_cost))
        self.shop.database["config"]["shipping"] = shipping_cost
        self.shop.status["dirty"] = True

        print("Free shipping enabled." if shipping_cost == 0 else "Shipping cost updated.")

    def run(self):
        while self.running:
            self.display_main_menu()
            choice = get_user_input("Choice: ").strip()

            if choice == "1":
                self.handle_items_menu()
            elif choice == "2":
                self.handle_cart_menu()
            elif choice == "3":
                self.checkout()
            elif choice == "4":
                self.handle_orders_menu()
            elif choice == "5":
                self.handle_config_menu()
            elif choice == "6":
                self.save_data()
            elif choice == "7":
                self.load_data()
            elif choice == "0":
                self.exit_program()
            else:
                self.handle_invalid_choice(choice)

    def save_data(self):
        if self.shop.save():
            print("Data saved successfully.")
        else:
            print("Failed to save data.")

    def load_data(self):
        self.shop.load()
        print("Data loaded successfully.")

    def exit_program(self):
        if self.shop.status["dirty"]:
            confirmation = get_user_input("Unsaved changes. Exit anyway? (y/n): ").strip().lower()
            if confirmation not in ["y", "yes", "j", "ja"]:
                return

        self.running = False


def main():
    shop = ShopSystem()
    shop.load()

    menu = MenuSystem(shop)
    menu.run()


if __name__ == "__main__":
    main()