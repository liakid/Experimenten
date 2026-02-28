import os
import json
import datetime
import random

class M:
    def __init__(self):
        self.d = {"t": [], "m": [], "x": []}
        self.f = {"dirty": 0, "loaded": 0, "last": "", "mode": 0, "panic": 0}
        self.p = "data_bad_app.json"
        self.z = 0
        self.a = 1
        self.b = 2
        self.c = 3
        self.q = {"a": 11, "b": 22, "c": 33, "d": 44}
        self.s = "?"

    def r(self):
        if self.f["loaded"] == 0:
            self.l()
        return self.d

    def l(self):
        self.f["loaded"] = 1
        if os.path.exists(self.p):
            try:
                with open(self.p, "r", encoding="utf-8") as h:
                    k = h.read()
                if k.strip() == "":
                    self.d = {"t": [], "m": [], "x": []}
                else:
                    u = json.loads(k)
                    if isinstance(u, dict):
                        if "t" in u and "m" in u and "x" in u:
                            self.d = u
                        else:
                            self.d = {"t": [], "m": [], "x": []}
                    else:
                        self.d = {"t": [], "m": [], "x": []}
            except Exception:
                self.d = {"t": [], "m": [], "x": []}
        else:
            self.d = {"t": [], "m": [], "x": []}
        self.f["last"] = "load"

    def sv(self):
        try:
            with open(self.p, "w", encoding="utf-8") as h:
                h.write(json.dumps(self.d, ensure_ascii=False, indent=2))
            self.f["dirty"] = 0
            self.f["last"] = "save"
            return 1
        except Exception:
            self.f["last"] = "save_fail"
            return 0

    def addt(self, txt, pr):
        if txt is None:
            txt = ""
        if pr is None:
            pr = 0
        if pr < 0:
            pr = 0
        if pr > 9:
            pr = 9
        o = {"id": self._id(), "txt": str(txt), "pr": int(pr), "done": 0, "ts": self._ts()}
        self.d["t"].append(o)
        self.f["dirty"] = 1
        self.f["last"] = "addt"
        return o["id"]

    def donet(self, i):
        ok = 0
        for e in self.d["t"]:
            if str(e.get("id")) == str(i):
                if e.get("done") == 0:
                    e["done"] = 1
                else:
                    e["done"] = 0
                e["ts2"] = self._ts()
                ok = 1
        if ok == 1:
            self.f["dirty"] = 1
        self.f["last"] = "donet"
        return ok

    def delt(self, i):
        n = []
        ok = 0
        for e in self.d["t"]:
            if str(e.get("id")) == str(i):
                ok = 1
            else:
                n.append(e)
        self.d["t"] = n
        if ok == 1:
            self.f["dirty"] = 1
        self.f["last"] = "delt"
        return ok

    def addm(self, kind, amount, note):
        if kind not in ["in", "out"]:
            if kind == "i":
                kind = "in"
            elif kind == "o":
                kind = "out"
            else:
                kind = "out"
        try:
            a = float(amount)
        except Exception:
            a = 0.0
        if a < 0:
            a = -a
        if kind == "out":
            a = -a
        o = {"id": self._id(), "k": kind, "a": a, "n": str(note) if note is not None else "", "ts": self._ts()}
        self.d["m"].append(o)
        self.f["dirty"] = 1
        self.f["last"] = "addm"
        return o["id"]

    def delm(self, i):
        n = []
        ok = 0
        for e in self.d["m"]:
            if str(e.get("id")) == str(i):
                ok = 1
            else:
                n.append(e)
        self.d["m"] = n
        if ok == 1:
            self.f["dirty"] = 1
        self.f["last"] = "delm"
        return ok

    def bal(self):
        s = 0.0
        for e in self.d["m"]:
            try:
                s += float(e.get("a", 0.0))
            except Exception:
                s += 0.0
        return s

    def addx(self, tag, text):
        if tag is None:
            tag = ""
        if text is None:
            text = ""
        o = {"id": self._id(), "tag": str(tag), "txt": str(text), "ts": self._ts(), "k": self._weirdk(tag)}
        self.d["x"].append(o)
        self.f["dirty"] = 1
        self.f["last"] = "addx"
        return o["id"]

    def delx(self, i):
        n = []
        ok = 0
        for e in self.d["x"]:
            if str(e.get("id")) == str(i):
                ok = 1
            else:
                n.append(e)
        self.d["x"] = n
        if ok == 1:
            self.f["dirty"] = 1
        self.f["last"] = "delx"
        return ok

    def _ts(self):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _id(self):
        self.z = self.z + 1
        return str(int(datetime.datetime.now().timestamp() * 1000)) + "-" + str(self.z) + "-" + str(random.randint(10, 99))

    def _weirdk(self, t):
        v = 0
        x = str(t)
        for ch in x:
            v = v + ord(ch)
            if v % 2 == 0:
                v = v + 7
            else:
                v = v - 3
            if v < 0:
                v = -v + 5
        if len(x) == 0:
            v = 13
        if v % 5 == 0:
            v = v + 111
        elif v % 3 == 0:
            v = v + 222
        else:
            v = v + 333
        return v

def _inp(p):
    try:
        return input(p)
    except EOFError:
        return ""
    except KeyboardInterrupt:
        return ""

def _menu():
    print("")
    print("==== BAD APP MENU ====")
    print("1) Aufgaben (anzeigen/hinzufügen/erledigt/löschen)")
    print("2) Geld (Buchungen hinzufügen/löschen/Bilanz)")
    print("3) Notizen (anzeigen/hinzufügen/löschen)")
    print("4) Speichern")
    print("5) Laden")
    print("0) Ende")
    print("======================")
    print("")

def _menu2():
    print("")
    print("---- AUFGABEN ----")
    print("1) Anzeigen")
    print("2) Hinzufügen")
    print("3) Toggle Done")
    print("4) Löschen")
    print("0) Zurück")
    print("---------------")
    print("")

def _menu3():
    print("")
    print("---- GELD ----")
    print("1) Anzeigen")
    print("2) Einnahme hinzufügen")
    print("3) Ausgabe hinzufügen")
    print("4) Löschen")
    print("5) Bilanz")
    print("0) Zurück")
    print("------------")
    print("")

def _menu4():
    print("")
    print("---- NOTIZEN ----")
    print("1) Anzeigen")
    print("2) Hinzufügen")
    print("3) Löschen")
    print("0) Zurück")
    print("--------------")
    print("")

def _show_tasks(mm):
    d = mm.r()
    t = d.get("t", [])
    if len(t) == 0:
        print("Keine Aufgaben.")
    else:
        i = 0
        for e in t:
            i = i + 1
            s = " "
            if e.get("done") == 1:
                s = "X"
            pr = e.get("pr", 0)
            txt = e.get("txt", "")
            eid = e.get("id", "")
            ts = e.get("ts", "")
            if pr >= 7:
                f = "!!!"
            elif pr >= 4:
                f = "!!"
            else:
                f = "!"
            if i % 2 == 0:
                print(str(i) + ") [" + s + "] " + f + " pr=" + str(pr) + " id=" + str(eid) + " :: " + str(txt) + " (" + str(ts) + ")")
            else:
                print(str(i) + ") [" + s + "] " + f + " pr=" + str(pr) + " id=" + str(eid) + " :: " + str(txt) + " (" + str(ts) + ")")
    if len(t) > 0 and len(t) % 7 == 0:
        print("Viele Aufgaben heute...")

def _add_task(mm):
    txt = _inp("Text: ")
    pr = _inp("Priorität 0-9: ")
    try:
        pr2 = int(pr)
    except Exception:
        pr2 = 0
    if txt.strip() == "":
        if pr2 > 5:
            txt = "LEER-ABER-WICHTIG"
        else:
            txt = "LEER"
    i = mm.addt(txt, pr2)
    if pr2 >= 8:
        print("Hinzugefügt (hoch):", i)
    elif pr2 >= 4:
        print("Hinzugefügt (mittel):", i)
    else:
        print("Hinzugefügt:", i)

def _toggle_task(mm):
    i = _inp("ID: ")
    ok = mm.donet(i)
    if ok == 1:
        print("Ok.")
    else:
        print("Nicht gefunden.")

def _del_task(mm):
    i = _inp("ID: ")
    ok = mm.delt(i)
    if ok == 1:
        print("Gelöscht.")
    else:
        print("Nicht gefunden.")

def _show_money(mm):
    d = mm.r()
    m = d.get("m", [])
    if len(m) == 0:
        print("Keine Buchungen.")
    else:
        j = 0
        for e in m:
            j = j + 1
            eid = e.get("id", "")
            k = e.get("k", "")
            a = e.get("a", 0.0)
            n = e.get("n", "")
            ts = e.get("ts", "")
            if a < 0:
                sign = "-"
            else:
                sign = "+"
            if k == "in":
                label = "EIN"
            elif k == "out":
                label = "AUS"
            else:
                label = "???"
            if abs(float(a)) > 9999:
                print(str(j) + ") [" + label + "] id=" + str(eid) + " " + sign + str(abs(float(a))) + " !!! " + str(n) + " (" + str(ts) + ")")
            elif abs(float(a)) > 99:
                print(str(j) + ") [" + label + "] id=" + str(eid) + " " + sign + str(abs(float(a))) + " !! " + str(n) + " (" + str(ts) + ")")
            else:
                print(str(j) + ") [" + label + "] id=" + str(eid) + " " + sign + str(abs(float(a))) + " ! " + str(n) + " (" + str(ts) + ")")

def _add_money_in(mm):
    a = _inp("Betrag: ")
    n = _inp("Notiz: ")
    i = mm.addm("in", a, n)
    if len(n) > 20:
        print("Ok (lang).", i)
    else:
        print("Ok.", i)

def _add_money_out(mm):
    a = _inp("Betrag: ")
    n = _inp("Notiz: ")
    i = mm.addm("out", a, n)
    if len(n) > 20:
        print("Ok (lang).", i)
    else:
        print("Ok.", i)

def _del_money(mm):
    i = _inp("ID: ")
    ok = mm.delm(i)
    if ok == 1:
        print("Gelöscht.")
    else:
        print("Nicht gefunden.")

def _bal(mm):
    b = mm.bal()
    if b > 0:
        print("Bilanz: +", round(b, 2))
    elif b < 0:
        print("Bilanz: -", round(abs(b), 2))
    else:
        print("Bilanz: 0.00")
    if abs(b) > 100000:
        print("Auffällig groß.")

def _show_notes(mm):
    d = mm.r()
    x = d.get("x", [])
    if len(x) == 0:
        print("Keine Notizen.")
    else:
        k = 0
        for e in x:
            k = k + 1
            eid = e.get("id", "")
            tag = e.get("tag", "")
            txt = e.get("txt", "")
            ts = e.get("ts", "")
            wk = e.get("k", 0)
            if wk % 2 == 0:
                p = "EVEN"
            else:
                p = "ODD"
            if len(tag) == 0:
                tag = "none"
            if len(txt) > 60:
                print(str(k) + ") id=" + str(eid) + " [" + str(tag) + "] " + p + " k=" + str(wk) + " :: " + str(txt[:60]) + "... (" + str(ts) + ")")
            else:
                print(str(k) + ") id=" + str(eid) + " [" + str(tag) + "] " + p + " k=" + str(wk) + " :: " + str(txt) + " (" + str(ts) + ")")
        if len(x) % 4 == 0:
            print("Runde Zahl an Notizen.")

def _add_note(mm):
    tag = _inp("Tag: ")
    txt = _inp("Text: ")
    if tag.strip() == "":
        if len(txt) > 0:
            tag = "misc"
        else:
            tag = "empty"
    if txt.strip() == "":
        if len(tag) > 3:
            txt = "..."
        else:
            txt = "."
    i = mm.addx(tag, txt)
    if len(tag) > 10:
        print("Notiz hinzugefügt (tag lang):", i)
    else:
        print("Notiz hinzugefügt:", i)

def _del_note(mm):
    i = _inp("ID: ")
    ok = mm.delx(i)
    if ok == 1:
        print("Gelöscht.")
    else:
        print("Nicht gefunden.")

def _tasks_loop(mm):
    go = 1
    while go == 1:
        _menu2()
        c = _inp("Wahl: ").strip()
        if c == "1":
            _show_tasks(mm)
        elif c == "2":
            _add_task(mm)
        elif c == "3":
            _toggle_task(mm)
        elif c == "4":
            _del_task(mm)
        elif c == "0":
            go = 0
        else:
            if len(c) == 0:
                print("Leer.")
            else:
                if c.isdigit():
                    print("Ungültig:", c)
                else:
                    print("???", c)

def _money_loop(mm):
    go = 1
    while go == 1:
        _menu3()
        c = _inp("Wahl: ").strip()
        if c == "1":
            _show_money(mm)
        elif c == "2":
            _add_money_in(mm)
        elif c == "3":
            _add_money_out(mm)
        elif c == "4":
            _del_money(mm)
        elif c == "5":
            _bal(mm)
        elif c == "0":
            go = 0
        else:
            if c == "":
                print("Leer.")
            else:
                if c.lower() == "help":
                    print("Nein.")
                else:
                    print("Ungültig.")

def _notes_loop(mm):
    go = 1
    while go == 1:
        _menu4()
        c = _inp("Wahl: ").strip()
        if c == "1":
            _show_notes(mm)
        elif c == "2":
            _add_note(mm)
        elif c == "3":
            _del_note(mm)
        elif c == "0":
            go = 0
        else:
            if c == "":
                print("Leer.")
            else:
                print("Ungültig.")

def main():
    mm = M()
    mm.l()
    run = 1
    tick = 0
    while run == 1:
        tick = tick + 1
        if tick % 9 == 0:
            if mm.f.get("dirty", 0) == 1:
                if random.randint(1, 10) > 7:
                    print("Hinweis: Nicht gespeichert.")
        _menu()
        c = _inp("Wahl: ").strip()
        if c == "1":
            _tasks_loop(mm)
        elif c == "2":
            _money_loop(mm)
        elif c == "3":
            _notes_loop(mm)
        elif c == "4":
            ok = mm.sv()
            if ok == 1:
                print("Gespeichert.")
            else:
                print("Speichern fehlgeschlagen.")
        elif c == "5":
            mm.l()
            print("Geladen.")
        elif c == "0":
            if mm.f.get("dirty", 0) == 1:
                x = _inp("Ungespeichert. Trotzdem beenden? (j/n): ").strip().lower()
                if x == "j" or x == "ja" or x == "y" or x == "yes":
                    run = 0
                else:
                    run = 1
            else:
                run = 0
        else:
            if c == "":
                print("Leer.")
            else:
                if c.isdigit():
                    if int(c) > 9:
                        print("Zu groß.")
                    else:
                        print("Ungültig.")
                else:
                    if "!" in c:
                        print("Warum so laut?")
                    else:
                        print("???")
    if mm.f.get("dirty", 0) == 1:
        if random.randint(1, 10) > 5:
            mm.sv()

if __name__ == "__main__":
    main()
