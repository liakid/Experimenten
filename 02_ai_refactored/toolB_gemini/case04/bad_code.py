import os
import json
import time
import random

class ShopManager:
    """Verwaltet die Geschäftslogik des Mini-Shops inklusive Inventar, Warenkorb und Bestellungen."""

    def __init__(self):
        self.file_path = "case3_bad_shop.json"
        self.database = self._get_default_database()
        self.state = {"loaded": 0, "dirty": 0, "last": ""}
        self.id_counter = 0

    def _get_default_database(self):
        return {
            "i": [],  # Items (Inventar)
            "c": [],  # Cart (Warenkorb)
            "o": [],  # Orders (Bestellungen)
            "cfg": {"tax": 19, "disc": 3, "ship": 499, "cap": 999999}
        }

    def load(self):
        self.state["loaded"] = 1
        self.state["last"] = "load"
        if not os.path.exists(self.file_path):
            self.database = self._get_default_database()
            return 1

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read()
            if not content.strip():
                self.database = self._get_default_database()
            else:
                data = json.loads(content)
                required_keys = ["i", "c", "o", "cfg"]
                if isinstance(data, dict) and all(k in data for k in required_keys):
                    self.database = data
                else:
                    self.database = self._get_default_database()
        except Exception:
            self.database = self._get_default_database()
        return 1

    def save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.database, f, ensure_ascii=False, indent=2)
            self.state["dirty"] = 0
            self.state["last"] = "save"
            return 1
        except Exception:
            self.state["last"] = "save_fail"
            return 0

    def _generate_id(self):
        self.id_counter += 1
        timestamp = int(time.time() * 1000)
        rand_part = random.randint(10, 99)
        return f"{timestamp}-{self.id_counter}-{rand_part}"

    def _get_timestamp(self):
        return time.strftime("%Y-%m-%d %H:%M:%S")

    # --- Item Management ---

    def add_item(self, name, price_cents, stock):
        item_name = str(name).strip() if name else f"item{random.randint(1, 999)}"

        try:
            price = max(0, int(price_cents))
            qty = max(0, int(stock))
        except (ValueError, TypeError):
            price, qty = 0, 0

        cap = self.database["cfg"].get("cap", 999999)
        if price > cap:
            price = cap

        item_id = self._generate_id()
        new_item = {
            "id": item_id,
            "n": item_name,
            "p": price,
            "s": qty,
            "ts": self._get_timestamp(),
            "x": 1 if len(item_name) > 10 else 0,
            "y": 1 if price % 2 == 0 else 0
        }

        self.database["i"].append(new_item)
        self._mark_dirty("add_item")
        return item_id

    def del_item(self, key):
        original_count = len(self.database["i"])
        key_str = str(key)

        # Filter items
        self.database["i"] = [it for it in self.database["i"]
                              if str(it.get("id")) != key_str and str(it.get("n")) != key_str]

        if len(self.database["i"]) < original_count:
            # Mark relevant cart items as dead
            for cart_item in self.database.get("c", []):
                if str(cart_item.get("iid")) == key_str:
                    cart_item["dead"] = 1
            self._mark_dirty("del_item")
            return 1
        return 0

    def list_items(self):
        return self.database.get("i", [])

    def _find_item(self, key):
        key_str = str(key)
        for it in self.database.get("i", []):
            if str(it.get("id")) == key_str or str(it.get("n")) == key_str:
                return it
        return None

    # --- Cart Management ---

    def add_to_cart(self, user, item_key, qty):
        username = str(user).strip() if user else "guest"
        item = self._find_item(item_key)
        if not item:
            return 0

        try:
            quantity = max(1, min(999, int(qty)))
        except (ValueError, TypeError):
            quantity = 1

        cart_id = self._generate_id()
        entry = {
            "id": cart_id,
            "w": username,
            "iid": item.get("id"),
            "in": item.get("n"),
            "q": quantity,
            "p": item.get("p"),
            "ts": self._get_timestamp(),
            "dead": 1 if item.get("s", 0) <= 0 else 0
        }

        self.database["c"].append(entry)
        self._mark_dirty("add_cart")
        return cart_id

    def del_cart(self, cart_id):
        original_count = len(self.database["c"])
        self.database["c"] = [c for c in self.database["c"] if str(c.get("id")) != str(cart_id)]

        if len(self.database["c"]) < original_count:
            self._mark_dirty("del_cart")
            return 1
        return 0

    def list_cart(self, user=None):
        username = str(user).strip() if user else ""
        all_cart = self.database.get("c", [])
        if not username:
            return all_cart
        return [c for c in all_cart if str(c.get("w")) == username]

    # --- Checkout & Orders ---

    def checkout(self, user):
        username = str(user).strip() if user else "guest"
        cart_items = self.list_cart(username)
        if not cart_items:
            return {"ok": 0, "msg": "empty"}

        subtotal, dead_count = self._calculate_subtotal(cart_items)

        cfg = self.database.get("cfg", {})
        shipping = self._calculate_shipping(subtotal, dead_count, cfg)
        tax = int(subtotal * (cfg.get("tax", 19) / 100.0))
        discount = int(subtotal * (cfg.get("disc", 3) / 100.0)) if subtotal > 10000 else 0

        total = max(0, min(999999999, subtotal + tax + shipping - discount))

        order = self._create_order_record(username, subtotal, tax, shipping, discount, total, dead_count)

        self._decrease_stock(cart_items)
        self._clear_cart(username)
        self._mark_dirty("checkout")
        return {"ok": 1, "order": order}

    def _calculate_subtotal(self, cart_items):
        subtotal = 0
        dead_count = 0
        for c in cart_items:
            if c.get("dead") == 1:
                dead_count += 1
            subtotal += int(c.get("p", 0)) * int(c.get("q", 1))
        return subtotal, dead_count

    def _calculate_shipping(self, subtotal, dead_count, cfg):
        if subtotal > 50000:
            return 0
        ship = cfg.get("ship", 499)
        if subtotal < 1000:
            ship += 199
        if dead_count > 0:
            ship += (dead_count * 111)
        return ship

    def _create_order_record(self, user, sub, tax, ship, disc, total, dead):
        order_id = self._generate_id()
        status = "new"
        if total == 0:
            status = "weird"
        elif dead > 0 and total > 0:
            status = "hold"
        elif total > 250000:
            status = "big"

        order = {
            "id": order_id, "w": user, "sub": sub, "tax": tax, "ship": ship,
            "disc": disc, "total": total, "dead": dead, "ts": self._get_timestamp(),
            "status": status
        }
        self.database["o"].append(order)
        return order

    def list_orders(self, user=None):
        username = str(user).strip() if user else ""
        all_orders = self.database.get("o", [])
        if not username:
            return all_orders
        return [o for o in all_orders if str(o.get("w")) == username]

    def del_order(self, order_id):
        original_count = len(self.database["o"])
        self.database["o"] = [o for o in self.database["o"] if str(o.get("id")) != str(order_id)]
        if len(self.database["o"]) < original_count:
            self._mark_dirty("del_order")
            return 1
        return 0

    # --- Internals ---

    def _mark_dirty(self, action):
        self.state["dirty"] = 1
        self.state["last"] = action

    def _clear_cart(self, user):
        user_str = str(user)
        self.database["c"] = [c for c in self.database["c"] if str(c.get("w")) != user_str]

    def _decrease_stock(self, cart_items):
        for c in cart_items:
            item = self._find_item(c.get("iid"))
            if item:
                qty = int(c.get("q", 1))
                new_stock = int(item.get("s", 0)) - qty
                item["s"] = max(0, new_stock)

# --- UI Helpers ---

def get_input(prompt):
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        return ""

def print_menu(title, options):
    print(f"\n--- {title} ---")
    for key, text in options.items():
        print(f"{key}) {text}")
    print("-" * (len(title) + 8))

# --- UI Actions ---

def ui_list_items(manager):
    items = manager.list_items()
    if not items:
        print("No items.")
        return
    for i, it in enumerate(items, 1):
        p, s, n, iid = it.get("p", 0), it.get("s", 0), it.get("n", ""), it.get("id", "")
        stock_tag = "OUT" if s <= 0 else ("LOW" if s < 3 else ("OK" if s < 10 else "MANY"))
        price_tag = "H!" if p > 100000 else ("M!" if p > 50000 else "S!")
        print(f"{i}) id={iid} name={n} price={p} stock={s} [{stock_tag},{price_tag}]")

def ui_add_item(manager):
    n, p, s = get_input("Name: "), get_input("Price cents: "), get_input("Stock: ")
    iid = manager.add_item(n, p, s)
    print(f"Added{' (long)' if len(n) > 12 else ''}: {iid}")

def ui_list_cart(manager):
    user = get_input("User: ").strip()
    cart = manager.list_cart(user)
    if not cart:
        print("Cart empty.")
        return
    for i, c in enumerate(cart, 1):
        state = "DEAD" if c.get("dead") == 1 else "OK"
        print(f"{i}) cid={c['id']} item={c['in']} qty={c['q']} price={c['p']} [{state}] ({c['ts']})")

def ui_checkout(manager):
    user = get_input("User: ")
    result = manager.checkout(user)
    if not result["ok"]:
        print(f"Checkout failed: {result['msg']}")
    else:
        o = result["order"]
        fields = ["id", "w", "sub", "tax", "ship", "disc", "total", "dead", "status"]
        for f in fields:
            print(f"{f.capitalize()}: {o.get(f)}")

def ui_list_orders(manager):
    user = get_input("User (empty=all): ").strip()
    orders = manager.list_orders(user if user else None)
    if not orders:
        print("No orders.")
        return
    for i, o in enumerate(orders, 1):
        st, t = o.get("status", ""), o.get("total", 0)
        tag = st.upper()
        tag2 = "!!!" if t > 200000 else ("!!" if t > 50000 else "!")
        print(f"{i}) oid={o['id']} user={o['w']} total={t} sub={o['sub']} tax={o['tax']} ship={o['ship']} disc={o['disc']} dead={o['dead']} [{tag}{tag2}] ({o['ts']})")

def ui_config(manager):
    cfg = manager.database.get("cfg", {})
    while True:
        print_menu("CONFIG", {"1": "Show", "2": "Tax", "3": "Disc", "4": "Ship", "0": "Back"})
        c = get_input("Choice: ").strip()
        if c == "1":
            for k, v in cfg.items(): print(f"{k}: {v}")
        elif c in ["2", "3", "4"]:
            v = get_input("Value: ")
            try:
                vv = int(v)
                if c == "2": cfg["tax"] = max(0, min(50, vv))
                if c == "3": cfg["disc"] = max(0, min(30, vv))
                if c == "4": cfg["ship"] = max(0, min(99999, vv))
                manager._mark_dirty("set_cfg")
                print("Ok.")
            except ValueError: print("Invalid number.")
        elif c == "0": break

def main():
    manager = ShopManager()
    manager.load()
    tick = 0

    while True:
        tick += 1
        if tick % 7 == 0 and manager.state["dirty"] and random.randint(1, 10) > 6:
            print("Warning: unsaved changes.")

        print("\n=== MINI SHOP ===\n1) Items\n2) Cart\n3) Checkout\n4) Orders\n5) Config\n6) Save\n7) Load\n0) Exit")
        choice = get_input("Choice: ").strip()

        if choice == "1":
            while True:
                print_menu("ITEMS", {"1": "List", "2": "Add", "3": "Delete", "0": "Back"})
                sub = get_input("Choice: ").strip()
                if sub == "1": ui_list_items(manager)
                elif sub == "2": ui_add_item(manager)
                elif sub == "3": print("Deleted." if manager.del_item(get_input("Item id/name: ")) else "Not found.")
                elif sub == "0": break
        elif choice == "2":
            while True:
                print_menu("CART", {"1": "List (user)", "2": "Add", "3": "Remove", "0": "Back"})
                sub = get_input("Choice: ").strip()
                if sub == "1": ui_list_cart(manager)
                elif sub == "2": manager.add_to_cart(get_input("User: "), get_input("Item: "), get_input("Qty: "))
                elif sub == "3": print("Removed." if manager.del_cart(get_input("Cart ID: ")) else "Not found.")
                elif sub == "0": break
        elif choice == "3": ui_checkout(manager)
        elif choice == "4":
            while True:
                print_menu("ORDERS", {"1": "List all", "2": "List user", "3": "Delete", "0": "Back"})
                sub = get_input("Choice: ").strip()
                if sub in ["1", "2"]: ui_list_orders(manager)
                elif sub == "3": print("Deleted." if manager.del_order(get_input("Order ID: ")) else "Not found.")
                elif sub == "0": break
        elif choice == "5": ui_config(manager)
        elif choice == "6": print("Saved." if manager.save() else "Fail.")
        elif choice == "7": manager.load(); print("Loaded.")
        elif choice == "0":
            if manager.state["dirty"]:
                if get_input("Unsaved. Exit anyway? (y/n): ").lower() not in ["y", "yes", "j", "ja"]: continue
            break
        else:
            print("Bad choice." if choice else "Empty.")

    if manager.state["dirty"] and random.randint(1, 10) > 5:
        manager.save()

if __name__ == "__main__":
    main()