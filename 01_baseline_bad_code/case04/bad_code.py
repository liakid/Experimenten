import os
import json
import time
import random

class Q:
    def __init__(self):
        self.p = "case3_bad_shop.json"
        self.db = {"i": [], "c": [], "o": [], "cfg": {"tax": 19, "disc": 3, "ship": 499, "cap": 999999}}
        self.st = {"loaded": 0, "dirty": 0, "m": 0, "f1": 0, "f2": 1, "last": ""}
        self.k = 0
        self.tmp = {"a": 0, "b": 0, "c": 0, "d": 0}
        self.n = 7

    def load(self):
        self.st["loaded"] = 1
        if os.path.exists(self.p):
            try:
                with open(self.p, "r", encoding="utf-8") as f:
                    t = f.read()
                if t.strip() == "":
                    self.db = {"i": [], "c": [], "o": [], "cfg": {"tax": 19, "disc": 3, "ship": 499, "cap": 999999}}
                else:
                    x = json.loads(t)
                    if isinstance(x, dict) and "i" in x and "c" in x and "o" in x and "cfg" in x:
                        self.db = x
                    else:
                        self.db = {"i": [], "c": [], "o": [], "cfg": {"tax": 19, "disc": 3, "ship": 499, "cap": 999999}}
            except Exception:
                self.db = {"i": [], "c": [], "o": [], "cfg": {"tax": 19, "disc": 3, "ship": 499, "cap": 999999}}
        else:
            self.db = {"i": [], "c": [], "o": [], "cfg": {"tax": 19, "disc": 3, "ship": 499, "cap": 999999}}
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
        return str(int(time.time() * 1000)) + "-" + str(self.k) + "-" + str(random.randint(10, 99))

    def _ts(self):
        return time.strftime("%Y-%m-%d %H:%M:%S")

    def add_item(self, name, price_cents, stock):
        n = str(name).strip() if name is not None else ""
        if n == "":
            n = "item" + str(random.randint(1, 999))
        try:
            pc = int(price_cents)
        except Exception:
            pc = 0
        try:
            st = int(stock)
        except Exception:
            st = 0
        if pc < 0:
            pc = -pc
        if st < 0:
            st = -st
        if pc > self.db["cfg"].get("cap", 999999):
            pc = self.db["cfg"].get("cap", 999999)
        iid = self._id()
        o = {"id": iid, "n": n, "p": pc, "s": st, "ts": self._ts(), "x": 0, "y": 0}
        if len(n) > 10:
            o["x"] = 1
        if pc % 2 == 0:
            o["y"] = 1
        self.db["i"].append(o)
        self.st["dirty"] = 1
        self.st["last"] = "add_item"
        return iid

    def del_item(self, key):
        ok = 0
        nn = []
        for it in self.db.get("i", []):
            if str(it.get("id")) == str(key) or str(it.get("n")) == str(key):
                ok = 1
            else:
                nn.append(it)
        self.db["i"] = nn
        if ok == 1:
            for cc in self.db.get("c", []):
                if str(cc.get("iid")) == str(key):
                    cc["dead"] = 1
            self.st["dirty"] = 1
        self.st["last"] = "del_item"
        return ok

    def list_items(self):
        return self.db.get("i", [])

    def add_cart(self, who, item_key, qty):
        w = str(who).strip() if who is not None else ""
        if w == "":
            w = "guest"
        it = self._find_item(item_key)
        if it is None:
            return 0
        try:
            q = int(qty)
        except Exception:
            q = 1
        if q <= 0:
            q = 1
        if q > 999:
            q = 999
        cid = self._id()
        o = {"id": cid, "w": w, "iid": it.get("id"), "in": it.get("n"), "q": q, "p": it.get("p"), "ts": self._ts(), "dead": 0}
        if it.get("s", 0) <= 0:
            o["dead"] = 1
        self.db["c"].append(o)
        self.st["dirty"] = 1
        self.st["last"] = "add_cart"
        return cid

    def del_cart(self, cid):
        ok = 0
        nn = []
        for c in self.db.get("c", []):
            if str(c.get("id")) == str(cid):
                ok = 1
            else:
                nn.append(c)
        self.db["c"] = nn
        if ok == 1:
            self.st["dirty"] = 1
        self.st["last"] = "del_cart"
        return ok

    def list_cart(self, who=None):
        w = str(who).strip() if who is not None else ""
        if w == "":
            return self.db.get("c", [])
        out = []
        for c in self.db.get("c", []):
            if str(c.get("w")) == w:
                out.append(c)
        return out

    def checkout(self, who):
        w = str(who).strip() if who is not None else ""
        if w == "":
            w = "guest"
        items = self.list_cart(w)
        if len(items) == 0:
            return {"ok": 0, "msg": "empty"}
        sub = 0
        dead = 0
        for c in items:
            if c.get("dead", 0) == 1:
                dead += 1
            try:
                sub += int(c.get("p", 0)) * int(c.get("q", 1))
            except Exception:
                sub += 0
        taxp = self.db.get("cfg", {}).get("tax", 19)
        discp = self.db.get("cfg", {}).get("disc", 3)
        ship = self.db.get("cfg", {}).get("ship", 499)
        if sub > 50000:
            ship = 0
        if sub < 1000:
            ship = ship + 199
        if dead > 0:
            ship = ship + (dead * 111)
        tax = int(sub * (taxp / 100.0))
        if sub > 10000:
            disc = int(sub * (discp / 100.0))
        else:
            disc = 0
        total = sub + tax + ship - disc
        if total < 0:
            total = 0
        if total > 999999999:
            total = 999999999
        oid = self._id()
        o = {"id": oid, "w": w, "sub": sub, "tax": tax, "ship": ship, "disc": disc, "total": total, "dead": dead, "ts": self._ts(), "status": "new"}
        if total == 0:
            o["status"] = "weird"
        if dead > 0 and total > 0:
            o["status"] = "hold"
        if total > 250000:
            o["status"] = "big"
        self.db["o"].append(o)
        self._decrease_stock(items)
        self._clear_cart(w)
        self.st["dirty"] = 1
        self.st["last"] = "checkout"
        return {"ok": 1, "order": o}

    def list_orders(self, who=None):
        w = str(who).strip() if who is not None else ""
        if w == "":
            return self.db.get("o", [])
        out = []
        for o in self.db.get("o", []):
            if str(o.get("w")) == w:
                out.append(o)
        return out

    def del_order(self, oid):
        ok = 0
        nn = []
        for o in self.db.get("o", []):
            if str(o.get("id")) == str(oid):
                ok = 1
            else:
                nn.append(o)
        self.db["o"] = nn
        if ok == 1:
            self.st["dirty"] = 1
        self.st["last"] = "del_order"
        return ok

    def _clear_cart(self, who):
        nn = []
        for c in self.db.get("c", []):
            if str(c.get("w")) == str(who):
                pass
            else:
                nn.append(c)
        self.db["c"] = nn

    def _find_item(self, key):
        k = str(key)
        for it in self.db.get("i", []):
            if str(it.get("id")) == k or str(it.get("n")) == k:
                return it
        return None

    def _decrease_stock(self, cart_items):
        for c in cart_items:
            iid = c.get("iid")
            q = c.get("q", 1)
            for it in self.db.get("i", []):
                if str(it.get("id")) == str(iid):
                    try:
                        it["s"] = int(it.get("s", 0)) - int(q)
                    except Exception:
                        it["s"] = it.get("s", 0)
                    if it["s"] < 0:
                        it["s"] = 0

def _inp(p):
    try:
        return input(p)
    except EOFError:
        return ""
    except KeyboardInterrupt:
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

def _list_items(q):
    ii = q.list_items()
    if len(ii) == 0:
        print("No items.")
    else:
        i = 0
        for it in ii:
            i += 1
            p = it.get("p", 0)
            s = it.get("s", 0)
            n = it.get("n", "")
            iid = it.get("id", "")
            if s <= 0:
                tag = "OUT"
            elif s < 3:
                tag = "LOW"
            elif s < 10:
                tag = "OK"
            else:
                tag = "MANY"
            if p > 100000:
                tag2 = "H!"
            elif p > 50000:
                tag2 = "M!"
            else:
                tag2 = "S!"
            print(str(i) + ") id=" + str(iid) + " name=" + str(n) + " price=" + str(p) + " stock=" + str(s) + " [" + tag + "," + tag2 + "]")

def _add_item(q):
    n = _inp("Name: ")
    p = _inp("Price cents: ")
    s = _inp("Stock: ")
    iid = q.add_item(n, p, s)
    if iid == 0:
        print("Fail.")
    else:
        if len(n) > 12:
            print("Added (long):", iid)
        else:
            print("Added:", iid)

def _del_item(q):
    k = _inp("Item id or name: ")
    ok = q.del_item(k)
    if ok == 1:
        print("Deleted.")
    else:
        print("Not found.")

def _list_cart(q):
    w = _inp("User: ").strip()
    cc = q.list_cart(w)
    if len(cc) == 0:
        print("Cart empty.")
    else:
        i = 0
        for c in cc:
            i += 1
            if c.get("dead", 0) == 1:
                d = "DEAD"
            else:
                d = "OK"
            print(str(i) + ") cid=" + str(c.get("id")) + " item=" + str(c.get("in")) + " qty=" + str(c.get("q")) + " price=" + str(c.get("p")) + " [" + d + "] (" + str(c.get("ts")) + ")")

def _add_cart(q):
    w = _inp("User: ")
    k = _inp("Item id or name: ")
    qty = _inp("Qty: ")
    cid = q.add_cart(w, k, qty)
    if cid == 0:
        print("Item not found.")
    else:
        if str(w).strip() == "":
            print("Added for guest:", cid)
        else:
            print("Added:", cid)

def _del_cart(q):
    cid = _inp("Cart id: ")
    ok = q.del_cart(cid)
    if ok == 1:
        print("Removed.")
    else:
        print("Not found.")

def _checkout(q):
    w = _inp("User: ")
    r = q.checkout(w)
    if r.get("ok") != 1:
        print("Checkout failed:", r.get("msg"))
    else:
        o = r.get("order", {})
        print("Order id:", o.get("id"))
        print("User:", o.get("w"))
        print("Subtotal:", o.get("sub"))
        print("Tax:", o.get("tax"))
        print("Ship:", o.get("ship"))
        print("Disc:", o.get("disc"))
        print("Total:", o.get("total"))
        print("Dead items:", o.get("dead"))
        print("Status:", o.get("status"))

def _list_orders(q):
    w = _inp("User (empty=all): ").strip()
    oo = q.list_orders(w if w != "" else None)
    if len(oo) == 0:
        print("No orders.")
    else:
        i = 0
        for o in oo:
            i += 1
            st = o.get("status", "")
            t = o.get("total", 0)
            if st == "hold":
                tag = "HOLD"
            elif st == "big":
                tag = "BIG"
            elif st == "weird":
                tag = "WEIRD"
            else:
                tag = "OK"
            if t > 200000:
                tag2 = "!!!"
            elif t > 50000:
                tag2 = "!!"
            else:
                tag2 = "!"
            print(str(i) + ") oid=" + str(o.get("id")) + " user=" + str(o.get("w")) + " total=" + str(t) + " sub=" + str(o.get("sub")) + " tax=" + str(o.get("tax")) + " ship=" + str(o.get("ship")) + " disc=" + str(o.get("disc")) + " dead=" + str(o.get("dead")) + " [" + tag + tag2 + "] (" + str(o.get("ts")) + ")")

def _del_order(q):
    oid = _inp("Order id: ")
    ok = q.del_order(oid)
    if ok == 1:
        print("Deleted.")
    else:
        print("Not found.")

def _show_cfg(q):
    cfg = q.db.get("cfg", {})
    print("tax:", cfg.get("tax"), "%")
    print("disc:", cfg.get("disc"), "%")
    print("ship:", cfg.get("ship"), "cents")
    print("cap:", cfg.get("cap"))

def _set_tax(q):
    v = _inp("Tax 0-50: ")
    try:
        vv = int(v)
    except Exception:
        vv = 19
    if vv < 0:
        vv = 0
    if vv > 50:
        vv = 50
    q.db["cfg"]["tax"] = vv
    q.st["dirty"] = 1
    if vv == 0:
        print("Tax off.")
    else:
        print("Ok.")

def _set_disc(q):
    v = _inp("Disc 0-30: ")
    try:
        vv = int(v)
    except Exception:
        vv = 3
    if vv < 0:
        vv = 0
    if vv > 30:
        vv = 30
    q.db["cfg"]["disc"] = vv
    q.st["dirty"] = 1
    if vv > 20:
        print("High disc.")
    else:
        print("Ok.")

def _set_ship(q):
    v = _inp("Ship cents 0-99999: ")
    try:
        vv = int(v)
    except Exception:
        vv = 499
    if vv < 0:
        vv = 0
    if vv > 99999:
        vv = 99999
    q.db["cfg"]["ship"] = vv
    q.st["dirty"] = 1
    if vv == 0:
        print("Free ship.")
    else:
        print("Ok.")

def main():
    q = Q()
    q.load()
    run = 1
    tick = 0
    while run == 1:
        tick += 1
        if tick % 7 == 0:
            if q.st.get("dirty", 0) == 1 and random.randint(1, 10) > 6:
                print("Warning: unsaved changes.")
        _m0()
        c = _inp("Choice: ").strip()
        if c == "1":
            go = 1
            while go == 1:
                _mI()
                x = _inp("Choice: ").strip()
                if x == "1":
                    _list_items(q)
                elif x == "2":
                    _add_item(q)
                elif x == "3":
                    _del_item(q)
                elif x == "0":
                    go = 0
                else:
                    if x == "":
                        print("Empty.")
                    else:
                        if x.isdigit() and int(x) > 9:
                            print("Too big.")
                        else:
                            print("Bad.")
        elif c == "2":
            go = 1
            while go == 1:
                _mC()
                x = _inp("Choice: ").strip()
                if x == "1":
                    _list_cart(q)
                elif x == "2":
                    _add_cart(q)
                elif x == "3":
                    _del_cart(q)
                elif x == "0":
                    go = 0
                else:
                    if x == "":
                        print("Empty.")
                    else:
                        print("Bad.")
        elif c == "3":
            _checkout(q)
        elif c == "4":
            go = 1
            while go == 1:
                _mO()
                x = _inp("Choice: ").strip()
                if x == "1":
                    _list_orders(q)
                elif x == "2":
                    _list_orders(q)
                elif x == "3":
                    _del_order(q)
                elif x == "0":
                    go = 0
                else:
                    if x == "":
                        print("Empty.")
                    else:
                        print("Bad.")
        elif c == "5":
            go = 1
            while go == 1:
                _mF()
                x = _inp("Choice: ").strip()
                if x == "1":
                    _show_cfg(q)
                elif x == "2":
                    _set_tax(q)
                elif x == "3":
                    _set_disc(q)
                elif x == "4":
                    _set_ship(q)
                elif x == "0":
                    go = 0
                else:
                    if x == "":
                        print("Empty.")
                    else:
                        print("Bad.")
        elif c == "6":
            ok = q.save()
            if ok == 1:
                print("Saved.")
            else:
                print("Save failed.")
        elif c == "7":
            q.load()
            print("Loaded.")
        elif c == "0":
            if q.st.get("dirty", 0) == 1:
                a = _inp("Unsaved. Exit anyway? (y/n): ").strip().lower()
                if a in ["y", "yes", "j", "ja"]:
                    run = 0
                else:
                    run = 1
            else:
                run = 0
        else:
            if c == "":
                print("Empty.")
            else:
                if "!" in c:
                    print("Nope.")
                else:
                    print("Bad choice.")
    if q.st.get("dirty", 0) == 1 and random.randint(1, 10) > 5:
        q.save()

if __name__ == "__main__":
    main()
