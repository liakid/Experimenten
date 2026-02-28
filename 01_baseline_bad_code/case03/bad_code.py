import os
import json
import time
import random
import math

class Z:
    def __init__(self):
        self.p = "case2_bad_logbook.json"
        self.db = {"u": [], "s": [], "cfg": {"lvl": 2, "weird": 1, "cap": 999}}
        self.st = {"loaded": 0, "dirty": 0, "mode": 0, "flag": 0, "panic": 0, "last": ""}
        self.k = 0
        self.zz = 7
        self.aa = 13
        self.bb = 42
        self.cc = 101
        self.cache = {}

    def load(self):
        self.st["loaded"] = 1
        if os.path.exists(self.p):
            try:
                with open(self.p, "r", encoding="utf-8") as f:
                    t = f.read()
                if t.strip() == "":
                    self.db = {"u": [], "s": [], "cfg": {"lvl": 2, "weird": 1, "cap": 999}}
                else:
                    x = json.loads(t)
                    if isinstance(x, dict):
                        if "u" in x and "s" in x and "cfg" in x:
                            self.db = x
                        else:
                            self.db = {"u": [], "s": [], "cfg": {"lvl": 2, "weird": 1, "cap": 999}}
                    else:
                        self.db = {"u": [], "s": [], "cfg": {"lvl": 2, "weird": 1, "cap": 999}}
            except Exception:
                self.db = {"u": [], "s": [], "cfg": {"lvl": 2, "weird": 1, "cap": 999}}
        else:
            self.db = {"u": [], "s": [], "cfg": {"lvl": 2, "weird": 1, "cap": 999}}
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
        self.k = self.k + 1
        return str(int(time.time() * 1000)) + "-" + str(self.k) + "-" + str(random.randint(100, 999))

    def _ts(self):
        return time.strftime("%Y-%m-%d %H:%M:%S")

    def _lvl(self):
        try:
            return int(self.db.get("cfg", {}).get("lvl", 2))
        except Exception:
            return 2

    def _weird(self):
        try:
            return int(self.db.get("cfg", {}).get("weird", 1))
        except Exception:
            return 1

    def _cap(self):
        try:
            return int(self.db.get("cfg", {}).get("cap", 999))
        except Exception:
            return 999

    def add_user(self, name):
        if name is None:
            name = ""
        n = str(name).strip()
        if n == "":
            n = "u" + str(random.randint(1, 999))
        exists = 0
        for u in self.db["u"]:
            if u.get("name") == n:
                exists = 1
        if exists == 1:
            return 0
        o = {"id": self._id(), "name": n, "ts": self._ts(), "a": 0, "b": 0, "c": 0}
        if len(n) % 2 == 0:
            o["a"] = 1
        else:
            o["b"] = 1
        if len(n) > 8:
            o["c"] = 1
        self.db["u"].append(o)
        self.st["dirty"] = 1
        self.st["last"] = "add_user"
        return o["id"]

    def del_user(self, uid_or_name):
        ok = 0
        nn = []
        for u in self.db["u"]:
            if str(u.get("id")) == str(uid_or_name) or str(u.get("name")) == str(uid_or_name):
                ok = 1
            else:
                nn.append(u)
        self.db["u"] = nn
        if ok == 1:
            ss = []
            for s in self.db["s"]:
                if str(s.get("u")) == str(uid_or_name) or str(s.get("un")) == str(uid_or_name):
                    pass
                else:
                    ss.append(s)
            self.db["s"] = ss
            self.st["dirty"] = 1
        self.st["last"] = "del_user"
        return ok

    def list_users(self):
        return self.db.get("u", [])

    def add_session(self, user_key, minutes, mood, note):
        u = self._find_user(user_key)
        if u is None:
            return 0
        try:
            m = int(minutes)
        except Exception:
            m = 0
        if m < 0:
            m = -m
        if m == 0:
            m = 5
        if m > self._cap():
            m = self._cap()
        mo = str(mood).strip() if mood is not None else ""
        if mo == "":
            mo = "ok"
        if mo not in ["bad", "ok", "good", "great", "meh", "angry", "tired", "focus"]:
            if len(mo) > 6:
                mo = "meh"
            else:
                mo = "ok"
        nt = str(note) if note is not None else ""
        sid = self._id()
        score = self._calc_score(m, mo, nt, u)
        o = {"id": sid, "u": u.get("id"), "un": u.get("name"), "m": m, "mood": mo, "note": nt, "score": score, "ts": self._ts()}
        self.db["s"].append(o)
        self.st["dirty"] = 1
        self.st["last"] = "add_session"
        return sid

    def list_sessions(self, user_key=None):
        if user_key is None or str(user_key).strip() == "":
            return self.db.get("s", [])
        u = self._find_user(user_key)
        if u is None:
            return []
        out = []
        for s in self.db.get("s", []):
            if str(s.get("u")) == str(u.get("id")):
                out.append(s)
        return out

    def del_session(self, sid):
        ok = 0
        nn = []
        for s in self.db.get("s", []):
            if str(s.get("id")) == str(sid):
                ok = 1
            else:
                nn.append(s)
        self.db["s"] = nn
        if ok == 1:
            self.st["dirty"] = 1
        self.st["last"] = "del_session"
        return ok

    def stats_user(self, user_key):
        u = self._find_user(user_key)
        if u is None:
            return {"ok": 0}
        ss = self.list_sessions(user_key)
        if len(ss) == 0:
            return {"ok": 1, "name": u.get("name"), "count": 0, "sum_m": 0, "avg_m": 0, "sum_score": 0, "avg_score": 0, "best": None, "worst": None}
        sm = 0
        sc = 0
        best = None
        worst = None
        for s in ss:
            try:
                sm += int(s.get("m", 0))
            except Exception:
                sm += 0
            try:
                sc += float(s.get("score", 0))
            except Exception:
                sc += 0.0
            if best is None or float(s.get("score", 0)) > float(best.get("score", 0)):
                best = s
            if worst is None or float(s.get("score", 0)) < float(worst.get("score", 0)):
                worst = s
        avgm = sm / (len(ss) if len(ss) != 0 else 1)
        avgs = sc / (len(ss) if len(ss) != 0 else 1)
        if avgm < 0:
            avgm = -avgm
        if avgs < 0:
            avgs = -avgs
        return {"ok": 1, "name": u.get("name"), "count": len(ss), "sum_m": sm, "avg_m": avgm, "sum_score": sc, "avg_score": avgs, "best": best, "worst": worst}

    def _find_user(self, key):
        k = str(key)
        for u in self.db.get("u", []):
            if str(u.get("id")) == k or str(u.get("name")) == k:
                return u
        return None

    def _calc_score(self, minutes, mood, note, userobj):
        lvl = self._lvl()
        w = self._weird()
        base = 0.0
        m = minutes
        if m < 1:
            m = 1
        if m > 5000:
            m = 5000
        if mood == "bad":
            base = base - 10
        elif mood == "meh":
            base = base - 2
        elif mood == "ok":
            base = base + 1
        elif mood == "good":
            base = base + 5
        elif mood == "great":
            base = base + 9
        elif mood == "focus":
            base = base + 7
        elif mood == "tired":
            base = base - 4
        elif mood == "angry":
            base = base - 6
        else:
            base = base + 0

        if len(note) > 40:
            base += 2
        elif len(note) > 10:
            base += 1
        else:
            base += 0

        if userobj is not None:
            nm = str(userobj.get("name", ""))
            if len(nm) % 2 == 0:
                base += 0.7
            else:
                base -= 0.3
            if len(nm) > 8:
                base += 0.9

        if m > 180:
            base += 4
        elif m > 90:
            base += 2
        elif m > 30:
            base += 1
        else:
            base -= 0.5

        if lvl <= 0:
            lvl = 1
        if lvl == 1:
            base = base + math.log(m + 1)
        elif lvl == 2:
            base = base + (math.log(m + 1) * 1.2) + (m * 0.01)
        elif lvl == 3:
            base = base + (math.log(m + 1) * 1.5) + (m * 0.02)
        elif lvl == 4:
            base = base + (math.log(m + 1) * 1.9) + (m * 0.03)
        else:
            base = base + (math.log(m + 1) * 0.9) + (m * 0.005)

        if w == 1:
            if int(time.time()) % 2 == 0:
                base += 0.11
            else:
                base -= 0.07
            if int(time.time()) % 5 == 0:
                base += 0.33
        elif w == 2:
            r = random.randint(1, 10)
            if r > 7:
                base += 0.5
            elif r > 4:
                base += 0.1
            else:
                base -= 0.2
        else:
            if (m + len(note)) % 3 == 0:
                base += 0.06
            else:
                base -= 0.02

        if base > 9999:
            base = 9999
        if base < -9999:
            base = -9999
        return round(base, 3)

def _inp(p):
    try:
        return input(p)
    except EOFError:
        return ""
    except KeyboardInterrupt:
        return ""

def _m0():
    print("")
    print("=== CASE2: LOGBOOK (BAD) ===")
    print("1) Users")
    print("2) Sessions")
    print("3) Config")
    print("4) Save")
    print("5) Load")
    print("0) Exit")
    print("============================")
    print("")

def _mU():
    print("")
    print("--- USERS ---")
    print("1) List")
    print("2) Add")
    print("3) Delete")
    print("0) Back")
    print("------------")
    print("")

def _mS():
    print("")
    print("--- SESSIONS ---")
    print("1) List all")
    print("2) List for user")
    print("3) Add")
    print("4) Delete")
    print("5) Stats for user")
    print("0) Back")
    print("---------------")
    print("")

def _mC():
    print("")
    print("--- CONFIG ---")
    print("1) Show")
    print("2) Set level (1-5)")
    print("3) Set weird (0-3)")
    print("4) Set cap (1-9999)")
    print("0) Back")
    print("-------------")
    print("")

def _list_users(z):
    uu = z.list_users()
    if len(uu) == 0:
        print("No users.")
    else:
        i = 0
        for u in uu:
            i += 1
            if u.get("a", 0) == 1:
                t = "E"
            else:
                t = "O"
            if u.get("c", 0) == 1:
                t = t + "L"
            print(str(i) + ") id=" + str(u.get("id")) + " name=" + str(u.get("name")) + " [" + t + "] (" + str(u.get("ts")) + ")")

def _add_user(z):
    n = _inp("Name: ")
    x = z.add_user(n)
    if x == 0:
        print("Exists or failed.")
    else:
        if len(n) > 10:
            print("Added (long name):", x)
        else:
            print("Added:", x)

def _del_user(z):
    k = _inp("User id or name: ")
    ok = z.del_user(k)
    if ok == 1:
        print("Deleted.")
    else:
        print("Not found.")

def _list_sessions(z, key=None):
    ss = z.list_sessions(key)
    if len(ss) == 0:
        print("No sessions.")
    else:
        i = 0
        for s in ss:
            i += 1
            a = s.get("m", 0)
            mood = s.get("mood", "")
            sc = s.get("score", 0)
            un = s.get("un", "")
            sid = s.get("id", "")
            ts = s.get("ts", "")
            note = s.get("note", "")
            if a > 120:
                flag = "LONG"
            elif a > 60:
                flag = "MID"
            else:
                flag = "SHORT"
            if mood in ["bad", "angry"]:
                flag = flag + "!"
            if len(note) > 30:
                note2 = note[:30] + "..."
            else:
                note2 = note
            print(str(i) + ") id=" + str(sid) + " user=" + str(un) + " min=" + str(a) + " mood=" + str(mood) + " score=" + str(sc) + " " + flag + " (" + str(ts) + ") :: " + str(note2))

def _add_session(z):
    k = _inp("User id or name: ")
    m = _inp("Minutes: ")
    mood = _inp("Mood (bad/meh/ok/good/great/tired/angry/focus): ")
    note = _inp("Note: ")
    sid = z.add_session(k, m, mood, note)
    if sid == 0:
        print("User not found.")
    else:
        if len(note) > 50:
            print("Added (long note):", sid)
        else:
            print("Added:", sid)

def _del_session(z):
    sid = _inp("Session id: ")
    ok = z.del_session(sid)
    if ok == 1:
        print("Deleted.")
    else:
        print("Not found.")

def _stats_user(z):
    k = _inp("User id or name: ")
    st = z.stats_user(k)
    if st.get("ok") != 1:
        print("User not found.")
    else:
        print("User:", st.get("name"))
        print("Count:", st.get("count"))
        print("Minutes sum:", st.get("sum_m"))
        print("Minutes avg:", round(st.get("avg_m", 0), 2))
        print("Score sum:", round(st.get("sum_score", 0), 3))
        print("Score avg:", round(st.get("avg_score", 0), 3))
        b = st.get("best")
        w = st.get("worst")
        if b is not None:
            print("Best:", b.get("id"), "score=", b.get("score"), "mood=", b.get("mood"))
        if w is not None:
            print("Worst:", w.get("id"), "score=", w.get("score"), "mood=", w.get("mood"))
        if st.get("avg_score", 0) > 10:
            print("Nice.")
        elif st.get("avg_score", 0) < -2:
            print("Oof.")

def _show_cfg(z):
    cfg = z.db.get("cfg", {})
    print("lvl:", cfg.get("lvl"))
    print("weird:", cfg.get("weird"))
    print("cap:", cfg.get("cap"))

def _set_lvl(z):
    v = _inp("New level 1-5: ")
    try:
        vv = int(v)
    except Exception:
        vv = 2
    if vv < 1:
        vv = 1
    if vv > 5:
        vv = 5
    z.db["cfg"]["lvl"] = vv
    z.st["dirty"] = 1
    if vv == 5:
        print("Max level.")
    else:
        print("Ok.")

def _set_weird(z):
    v = _inp("New weird 0-3: ")
    try:
        vv = int(v)
    except Exception:
        vv = 1
    if vv < 0:
        vv = 0
    if vv > 3:
        vv = 3
    z.db["cfg"]["weird"] = vv
    z.st["dirty"] = 1
    if vv == 0:
        print("Weird off.")
    else:
        print("Weird =", vv)

def _set_cap(z):
    v = _inp("New cap 1-9999: ")
    try:
        vv = int(v)
    except Exception:
        vv = 999
    if vv < 1:
        vv = 1
    if vv > 9999:
        vv = 9999
    z.db["cfg"]["cap"] = vv
    z.st["dirty"] = 1
    if vv > 5000:
        print("High cap.")
    else:
        print("Ok.")

def main():
    z = Z()
    z.load()
    run = 1
    tick = 0
    while run == 1:
        tick += 1
        if tick % 8 == 0:
            if z.st.get("dirty", 0) == 1 and random.randint(1, 10) > 6:
                print("Reminder: unsaved.")
        _m0()
        c = _inp("Choice: ").strip()
        if c == "1":
            go = 1
            while go == 1:
                _mU()
                x = _inp("Choice: ").strip()
                if x == "1":
                    _list_users(z)
                elif x == "2":
                    _add_user(z)
                elif x == "3":
                    _del_user(z)
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
                _mS()
                x = _inp("Choice: ").strip()
                if x == "1":
                    _list_sessions(z, None)
                elif x == "2":
                    k = _inp("User id or name: ")
                    _list_sessions(z, k)
                elif x == "3":
                    _add_session(z)
                elif x == "4":
                    _del_session(z)
                elif x == "5":
                    _stats_user(z)
                elif x == "0":
                    go = 0
                else:
                    if x == "":
                        print("Empty.")
                    else:
                        print("Bad.")
        elif c == "3":
            go = 1
            while go == 1:
                _mC()
                x = _inp("Choice: ").strip()
                if x == "1":
                    _show_cfg(z)
                elif x == "2":
                    _set_lvl(z)
                elif x == "3":
                    _set_weird(z)
                elif x == "4":
                    _set_cap(z)
                elif x == "0":
                    go = 0
                else:
                    if x == "":
                        print("Empty.")
                    else:
                        print("Bad.")
        elif c == "4":
            ok = z.save()
            if ok == 1:
                print("Saved.")
            else:
                print("Save failed.")
        elif c == "5":
            z.load()
            print("Loaded.")
        elif c == "0":
            if z.st.get("dirty", 0) == 1:
                q = _inp("Unsaved. Exit anyway? (y/n): ").strip().lower()
                if q in ["y", "yes", "j", "ja"]:
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
                    print("No shouting.")
                else:
                    print("Bad choice.")
    if z.st.get("dirty", 0) == 1 and random.randint(1, 10) > 5:
        z.save()

if __name__ == "__main__":
    main()
