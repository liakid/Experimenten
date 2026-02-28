import os
import json
import time
import random


DATA_FILE_PATH = "case3_bad_shop.json"
DEFAULT_DB = {"i": [], "c": [], "o": [], "cfg": {"tax": 19, "disc": 3, "ship": 499, "cap": 999999}}


class Q:
    def __init__(self):
        self.p = DATA_FILE_PATH
        self.db = self._default_db()
        self.st = {"loaded": 0, "dirty": 0, "m": 0, "f1": 0, "f2": 1, "last": ""}
        self.k = 0

        # Legacy / unused fields kept to preserve instance state shape (no behavior change)
        self.tmp = {"a": 0, "b": 0, "c": 0, "d": 0}
        self.n = 7

    def load(self):
        self.st["loaded"] = 1
        self.db = self._load_db_from_file(self.p)
        self.st["last"] = "load"
        return 1

    def save(self):
        try:
            with open(self.p, "w", encoding="utf-8") as f:
                f.write(json.dumps(self.db, ensure_ascii=False, indent=2))
            self.st["dirty"] = 0
            self.st["last"] = "save"
            return 1
        except Exception:
            self.st["last"] = "save_fail"
            return 0

    def _id(self):
        self.k += 1
        timestamp_ms = int(time.time() * 1000)
        return f"{timestamp_ms}-{self.k}-{random.randint(10, 99)}"

    def _ts(self):
        return time.strftime("%Y-%m-%d %H:%M:%S")

    def add_item(self, name, price_cents, stock):
        item_name = self._normalize_item_name(name)
        price = self._normalize_non_negative_int(price_cents, default=0)
        stock_count = self._normalize_non_negative_int(stock, default=0)

        cap = self.db["cfg"].get("cap", 999999)
        if price > cap:
            price = cap

        item_id = self._id()
        item = {
            "id": item_id,
            "n": item_name,
            "p": price,
            "s": stock_count,
            "ts": self._ts(),
            "x": 0,
            "y": 0,
        }

        if len(item_name) > 10:
            item["x"] = 1
        if price % 2 == 0:
            item["y"] = 1

        self.db["i"].append(item)
        self._mark_dirty("add_item")
        return item_id

    def del_item(self, key):
        target = str(key)
        kept, deleted = self._filter_items(target)
        self.db["i"] = kept

        if deleted == 1:
            self._mark_cart_items_dead_for_item(target)
            self.st["dirty"] = 1

        self.st["last"] = "del_item"
        return deleted

    def list_items(self):
        return self.db.get("i", [])

    def add_cart(self, who, item_key, qty):
        user = self._normalize_user(who)
        item = self._find_item(item_key)
        if item is None:
            return 0

        quantity = self._normalize_qty(qty)
        cart_id = self._id()

        cart_entry = {
            "id": cart_id,
            "w": user,
            "iid": item.get("id"),
            "in": item.get("n"),
            "q": quantity,
            "p": item.get("p"),
            "ts": self._ts(),
            "dead": 0,
        }

        if item.get("s", 0) <= 0:
            cart_entry["dead"] = 1

        self.db["c"].append(cart_entry)
        self._mark_dirty("add_cart")
        return cart_id

    def del_cart(self, cid):
        target = str(cid)
        remaining = []
        deleted = 0

        for entry in self.db.get("c", []):
            if str(entry.get("id")) == target:
                deleted = 1
            else:
                remaining.append(entry)

        self.db["c"] = remaining
        if deleted == 1:
            self.st["dirty"] = 1
        self.st["last"] = "del_cart"
        return deleted

    def list_cart(self, who=None):
        user = str(who).strip() if who is not None else ""
        if user == "":
            return self.db.get("c", [])

        return [c for c in self.db.get("c", []) if str(c.get("w")) == user]

    def checkout(self, who):
        user = self._normalize_user(who)
        cart_items = self.list_cart(user)

        if len(cart_items) == 0:
            return {"ok": 0, "msg": "empty"}

        subtotal, dead_count = self._cart_subtotal_and_dead(cart_items)
        tax, discount, shipping = self._price_components(subtotal, dead_count)
        total = self._clamp_total(subtotal + tax + shipping - discount)

        order_id = self._id()
        status = self._order_status(total, dead_count)

        order = {
            "id": order_id,
            "w": user,
            "sub": subtotal,
            "tax": tax,
            "ship": shipping,
            "disc": discount,
            "total": total,
            "dead": dead_count,
            "ts": self._ts(),
            "status": status,
        }

        self.db["o"].append(order)
        self._decrease_stock(cart_items)
        self._clear_cart(user)

        self.st["dirty"] = 1
        self.st["last"] = "checkout"
        return {"ok": 1, "order": order}

    def list_orders(self, who=None):
        user = str(who).strip() if who is not None else ""
        if user == "":
            return self.db.get("o", [])

        return [o for o in self.db.get("o", []) if str(o.get("w")) == user]

    def del_order(self, oid):
        target = str(oid)
        remaining = []
        deleted = 0

        for order in self.db.get("o", []):
            if str(order.get("id")) == target:
                deleted = 1
            else:
                remaining.append(order)

        self.db["o"] = remaining
        if deleted == 1:
            self.st["dirty"] = 1
        self.st["last"] = "del_order"
        return deleted

    def _clear_cart(self, who):
        user = str(who)
        self.db["c"] = [c for c in self.db.get("c", []) if str(c.get("w")) != user]

    def _find_item(self, key):
        lookup = str(key)
        for item in self.db.get("i", []):
            if str(item.get("id")) == lookup or str(item.get("n")) == lookup:
                return item
        return None

    def _decrease_stock(self, cart_items):
        for cart_entry in cart_items:
            item_id = cart_entry.get("iid")
            quantity = cart_entry.get("q", 1)

            for item in self.db.get("i", []):
                if str(item.get("id")) != str(item_id):
                    continue

                try:
                    item["s"] = int(item.get("s", 0)) - int(quantity)
                except Exception:
                    item["s"] = item.get("s", 0)

                if item["s"] < 0:
                    item["s"] = 0

    @staticmethod
    def _default_db():
        return {"i": [], "c": [], "o": [], "cfg": {"tax": 19, "disc": 3, "ship": 499, "cap": 999999}}

    def _load_db_from_file(self, path):
        if not os.path.exists(path):
            return self._default_db()

        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
        except Exception:
            return self._default_db()

        if raw.strip() == "":
            return self._default_db()

        try:
            parsed = json.loads(raw)
        except Exception:
            return self._default_db()

        if isinstance(parsed, dict) and "i" in parsed and "c" in parsed and "o" in parsed and "cfg" in parsed:
            return parsed

        return self._default_db()

    @staticmethod
    def _normalize_item_name(name):
        normalized = str(name).strip() if name is not None else ""
        if normalized == "":
            normalized = "item" + str(random.randint(1, 999))
        return normalized

    @staticmethod
    def _normalize_user(who):
        user = str(who).strip() if who is not None else ""
        return user if user != "" else "guest"

    @staticmethod
    def _normalize_non_negative_int(value, default):
        try:
            number = int(value)
        except Exception:
            number = int(default)

        if number < 0:
            number = -number

        return number

    @staticmethod
    def _normalize_qty(qty):
        try:
            q = int(qty)
        except Exception:
            q = 1

        if q <= 0:
            q = 1
        if q > 999:
            q = 999

        return q

    def _filter_items(self, key):
        kept = []
        deleted = 0
        for item in self.db.get("i", []):
            if str(item.get("id")) == key or str(item.get("n")) == key:
                deleted = 1
            else:
                kept.append(item)
        return kept, deleted

    def _mark_cart_items_dead_for_item(self, key):
        for cart_entry in self.db.get("c", []):
            if str(cart_entry.get("iid")) == str(key):
                cart_entry["dead"] = 1

    @staticmethod
    def _cart_subtotal_and_dead(cart_items):
        subtotal = 0
        dead = 0

        for cart_entry in cart_items:
            if cart_entry.get("dead", 0) == 1:
                dead += 1

            try:
                subtotal += int(cart_entry.get("p", 0)) * int(cart_entry.get("q", 1))
            except Exception:
                subtotal += 0

        return subtotal, dead

    def _price_components(self, subtotal, dead_count):
        cfg = self.db.get("cfg", {})
        tax_percent = cfg.get("tax", 19)
        discount_percent = cfg.get("disc", 3)
        shipping = cfg.get("ship", 499)

        shipping = self._shipping_cost(subtotal, dead_count, shipping)
        tax = int(subtotal * (tax_percent / 100.0))
        discount = int(subtotal * (discount_percent / 100.0)) if subtotal > 10000 else 0

        return tax, discount, shipping

    @staticmethod
    def _shipping_cost(subtotal, dead_count, base_shipping):
        shipping = base_shipping

        if subtotal > 50000:
            shipping = 0
        if subtotal < 1000:
            shipping = shipping + 199
        if dead_count > 0:
            shipping = shipping + (dead_count * 111)

        return shipping

    @staticmethod
    def _clamp_total(total):
        if total < 0:
            return 0
        if total > 999999999:
            return 999999999
        return total

    @staticmethod
    def _order_status(total, dead_count):
        status = "new"
        if total == 0:
            status = "weird"
        if dead_count > 0 and total > 0:
            status = "hold"
        if total > 250000:
            status = "big"
        return status

    def _mark_dirty(self, last_action):
        self.st["dirty"] = 1
        self.st["last"] = last_action


def _inp(p):
    try:
        return input(p)
    except (EOFError, KeyboardInterrupt):
        return ""


def _m0():
    print("")
    print("=== CASE3: MINI SHOP (BAD) ===")
    print("1) Items")
    print("2) Cart")
    print("3) Checkout")
    print("4) Orders")
    print("5) Config")
    print("6) Save")
    print("7) Load")
    print("0) Exit")
    print("==============================")
    print("")


def _mI():
    print("")
    print("--- ITEMS ---")
    print("1) List")
    print("2) Add")
    print("3) Delete")
    print("0) Back")
    print("------------")
    print("")


def _mC():
    print("")
    print("--- CART ---")
    print("1) List cart (user)")
    print("2) Add to cart")
    print("3) Remove from cart (by cart id)")
    print("0) Back")
    print("-----------")
    print("")


def _mO():
    print("")
    print("--- ORDERS ---")
    print("1) List all")
    print("2) List for user")
    print("3) Delete order")
    print("0) Back")
    print("------------")
    print("")


def _mF():
    print("")
    print("--- CONFIG ---")
    print("1) Show")
    print("2) Set tax (0-50)")
    print("3) Set disc (0-30)")
    print("4) Set ship cents (0-99999)")
    print("0) Back")
    print("------------")
    print("")


def _stock_tag(stock):
    if stock <= 0:
        return "OUT"
    if stock < 3:
        return "LOW"
    if stock < 10:
        return "OK"
    return "MANY"


def _price_tag(price):
    if price > 100000:
        return "H!"
    if price > 50000:
        return "M!"
    return "S!"


def _list_items(q):
    items = q.list_items()
    if len(items) == 0:
        print("No items.")
        return

    index = 0
    for item in items:
        index += 1
        price = item.get("p", 0)
        stock = item.get("s", 0)
        name = item.get("n", "")
        item_id = item.get("id", "")

        tag = _stock_tag(stock)
        tag2 = _price_tag(price)

        print(f"{index}) id={item_id} name={name} price={price} stock={stock} [{tag},{tag2}]")


def _add_item(q):
    name = _inp("Name: ")
    price = _inp("Price cents: ")
    stock = _inp("Stock: ")

    item_id = q.add_item(name, price, stock)
    if item_id == 0:
        print("Fail.")
    elif len(name) > 12:
        print("Added (long):", item_id)
    else:
        print("Added:", item_id)


def _del_item(q):
    key = _inp("Item id or name: ")
    ok = q.del_item(key)
    print("Deleted." if ok == 1 else "Not found.")


def _list_cart(q):
    user = _inp("User: ").strip()
    cart = q.list_cart(user)

    if len(cart) == 0:
        print("Cart empty.")
        return

    index = 0
    for entry in cart:
        index += 1
        dead_tag = "DEAD" if entry.get("dead", 0) == 1 else "OK"
        print(
            f"{index}) cid={entry.get('id')} item={entry.get('in')} qty={entry.get('q')} "
            f"price={entry.get('p')} [{dead_tag}] ({entry.get('ts')})"
        )


def _add_cart(q):
    user = _inp("User: ")
    key = _inp("Item id or name: ")
    qty = _inp("Qty: ")

    cart_id = q.add_cart(user, key, qty)
    if cart_id == 0:
        print("Item not found.")
    elif str(user).strip() == "":
        print("Added for guest:", cart_id)
    else:
        print("Added:", cart_id)


def _del_cart(q):
    cart_id = _inp("Cart id: ")
    ok = q.del_cart(cart_id)
    print("Removed." if ok == 1 else "Not found.")


def _checkout(q):
    user = _inp("User: ")
    result = q.checkout(user)

    if result.get("ok") != 1:
        print("Checkout failed:", result.get("msg"))
        return

    order = result.get("order", {})
    print("Order id:", order.get("id"))
    print("User:", order.get("w"))
    print("Subtotal:", order.get("sub"))
    print("Tax:", order.get("tax"))
    print("Ship:", order.get("ship"))
    print("Disc:", order.get("disc"))
    print("Total:", order.get("total"))
    print("Dead items:", order.get("dead"))
    print("Status:", order.get("status"))


def _order_status_tag(status):
    if status == "hold":
        return "HOLD"
    if status == "big":
        return "BIG"
    if status == "weird":
        return "WEIRD"
    return "OK"


def _order_amount_tag(total):
    if total > 200000:
        return "!!!"
    if total > 50000:
        return "!!"
    return "!"


def _list_orders(q):
    user = _inp("User (empty=all): ").strip()
    orders = q.list_orders(user if user != "" else None)

    if len(orders) == 0:
        print("No orders.")
        return

    index = 0
    for order in orders:
        index += 1
        status = order.get("status", "")
        total = order.get("total", 0)

        tag = _order_status_tag(status)
        tag2 = _order_amount_tag(total)

        print(
            f"{index}) oid={order.get('id')} user={order.get('w')} total={total} sub={order.get('sub')} "
            f"tax={order.get('tax')} ship={order.get('ship')} disc={order.get('disc')} dead={order.get('dead')} "
            f"[{tag}{tag2}] ({order.get('ts')})"
        )


def _del_order(q):
    order_id = _inp("Order id: ")
    ok = q.del_order(order_id)
    print("Deleted." if ok == 1 else "Not found.")


def _show_cfg(q):
    cfg = q.db.get("cfg", {})
    print("tax:", cfg.get("tax"), "%")
    print("disc:", cfg.get("disc"), "%")
    print("ship:", cfg.get("ship"), "cents")
    print("cap:", cfg.get("cap"))


def _clamp_int(value, default, minimum, maximum):
    try:
        number = int(value)
    except Exception:
        number = int(default)

    if number < minimum:
        return int(minimum)
    if number > maximum:
        return int(maximum)
    return int(number)


def _set_tax(q):
    raw = _inp("Tax 0-50: ")
    tax = _clamp_int(raw, default=19, minimum=0, maximum=50)

    q.db["cfg"]["tax"] = tax
    q.st["dirty"] = 1

    print("Tax off." if tax == 0 else "Ok.")


def _set_disc(q):
    raw = _inp("Disc 0-30: ")
    disc = _clamp_int(raw, default=3, minimum=0, maximum=30)

    q.db["cfg"]["disc"] = disc
    q.st["dirty"] = 1

    print("High disc." if disc > 20 else "Ok.")


def _set_ship(q):
    raw = _inp("Ship cents 0-99999: ")
    ship = _clamp_int(raw, default=499, minimum=0, maximum=99999)

    q.db["cfg"]["ship"] = ship
    q.st["dirty"] = 1

    print("Free ship." if ship == 0 else "Ok.")


def _maybe_warn_unsaved(q, tick):
    if tick % 7 != 0:
        return
    if q.st.get("dirty", 0) != 1:
        return
    if random.randint(1, 10) > 6:
        print("Warning: unsaved changes.")


def _should_exit(q):
    if q.st.get("dirty", 0) != 1:
        return True

    answer = _inp("Unsaved. Exit anyway? (y/n): ").strip().lower()
    return answer in ("y", "yes", "j", "ja")


def _handle_main_bad_choice(choice):
    if choice == "":
        print("Empty.")
    elif "!" in choice:
        print("Nope.")
    else:
        print("Bad choice.")


def _loop_items(q):
    go = 1
    while go == 1:
        _mI()
        choice = _inp("Choice: ").strip()

        if choice == "1":
            _list_items(q)
        elif choice == "2":
            _add_item(q)
        elif choice == "3":
            _del_item(q)
        elif choice == "0":
            go = 0
        else:
            if choice == "":
                print("Empty.")
            elif choice.isdigit() and int(choice) > 9:
                print("Too big.")
            else:
                print("Bad.")


def _loop_cart(q):
    go = 1
    while go == 1:
        _mC()
        choice = _inp("Choice: ").strip()

        if choice == "1":
            _list_cart(q)
        elif choice == "2":
            _add_cart(q)
        elif choice == "3":
            _del_cart(q)
        elif choice == "0":
            go = 0
        else:
            print("Empty." if choice == "" else "Bad.")


def _loop_orders(q):
    go = 1
    while go == 1:
        _mO()
        choice = _inp("Choice: ").strip()

        if choice == "1":
            _list_orders(q)
        elif choice == "2":
            _list_orders(q)
        elif choice == "3":
            _del_order(q)
        elif choice == "0":
            go = 0
        else:
            print("Empty." if choice == "" else "Bad.")


def _loop_config(q):
    go = 1
    while go == 1:
        _mF()
        choice = _inp("Choice: ").strip()

        if choice == "1":
            _show_cfg(q)
        elif choice == "2":
            _set_tax(q)
        elif choice == "3":
            _set_disc(q)
        elif choice == "4":
            _set_ship(q)
        elif choice == "0":
            go = 0
        else:
            print("Empty." if choice == "" else "Bad.")


def main():
    q = Q()
    q.load()

    run = 1
    tick = 0

    while run == 1:
        tick += 1
        _maybe_warn_unsaved(q, tick)

        _m0()
        choice = _inp("Choice: ").strip()

        if choice == "1":
            _loop_items(q)
        elif choice == "2":
            _loop_cart(q)
        elif choice == "3":
            _checkout(q)
        elif choice == "4":
            _loop_orders(q)
        elif choice == "5":
            _loop_config(q)
        elif choice == "6":
            ok = q.save()
            print("Saved." if ok == 1 else "Save failed.")
        elif choice == "7":
            q.load()
            print("Loaded.")
        elif choice == "0":
            run = 0 if _should_exit(q) else 1
        else:
            _handle_main_bad_choice(choice)

    if q.st.get("dirty", 0) == 1 and random.randint(1, 10) > 5:
        q.save()


if __name__ == "__main__":
    main()
