import os
import json
import time
import random
import math

class LogbookManager:
    """Verwaltet Benutzer, Sitzungen und die Berechnung von Aktivitäts-Scores."""

    DEFAULT_DB = {
        "u": [],
        "s": [],
        "cfg": {"lvl": 2, "weird": 1, "cap": 999}
    }

    MOOD_SCORES = {
        "bad": -10, "meh": -2, "ok": 1, "good": 5,
        "great": 9, "focus": 7, "tired": -4, "angry": -6
    }

    def __init__(self):
        self.file_path = "case2_bad_logbook.json"
        self.db = self.DEFAULT_DB.copy()
        self.state = {"loaded": 0, "dirty": 0, "last": ""}
        self.id_counter = 0

    # --- Persistenz ---

    def load(self):
        self.state["loaded"] = 1
        self.state["last"] = "load"

        if not os.path.exists(self.file_path):
            self.db = self.DEFAULT_DB.copy()
            return 1

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if not content.strip():
                self.db = self.DEFAULT_DB.copy()
                return 1

            data = json.loads(content)
            if self._is_valid_db(data):
                self.db = data
            else:
                self.db = self.DEFAULT_DB.copy()
        except Exception:
            self.db = self.DEFAULT_DB.copy()
        return 1

    def save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.db, f, ensure_ascii=False, indent=2)
            self.state["dirty"] = 0
            self.state["last"] = "save"
            return 1
        except Exception:
            self.state["last"] = "save_fail"
            return 0

    def _is_valid_db(self, data):
        return isinstance(data, dict) and all(k in data for k in ("u", "s", "cfg"))

    # --- Hilfsmethoden ---

    def _generate_id(self):
        self.id_counter += 1
        timestamp = int(time.time() * 1000)
        random_suffix = random.randint(100, 999)
        return f"{timestamp}-{self.id_counter}-{random_suffix}"

    def _get_timestamp(self):
        return time.strftime("%Y-%m-%d %H:%M:%S")

    def _get_cfg(self, key, default):
        return self.db.get("cfg", {}).get(key, default)

    def _find_user(self, key):
        search_key = str(key)
        for user in self.db.get("u", []):
            if str(user.get("id")) == search_key or str(user.get("name")) == search_key:
                return user
        return None

    def _set_dirty(self, action_name):
        self.state["dirty"] = 1
        self.state["last"] = action_name

    # --- Benutzer-Verwaltung ---

    def add_user(self, name):
        clean_name = str(name or "").strip()
        if not clean_name:
            clean_name = f"u{random.randint(1, 999)}"

        if self._find_user(clean_name):
            return 0

        user = {
            "id": self._generate_id(),
            "name": clean_name,
            "ts": self._get_timestamp(),
            "a": 1 if len(clean_name) % 2 == 0 else 0,
            "b": 1 if len(clean_name) % 2 != 0 else 0,
            "c": 1 if len(clean_name) > 8 else 0
        }

        self.db["u"].append(user)
        self._set_dirty("add_user")
        return user["id"]

    def del_user(self, identifier):
        target_user = self._find_user(identifier)
        if not target_user:
            return 0

        uid = str(target_user["id"])
        uname = str(target_user["name"])

        # User entfernen
        self.db["u"] = [u for u in self.db["u"] if str(u["id"]) != uid]

        # Zugehörige Sessions entfernen
        self.db["s"] = [
            s for s in self.db["s"]
            if str(s.get("u")) != uid and str(s.get("un")) != uname
        ]

        self._set_dirty("del_user")
        return 1

    def list_users(self):
        return self.db.get("u", [])

    # --- Sitzungs-Verwaltung ---

    def add_session(self, user_key, minutes, mood, note):
        user = self._find_user(user_key)
        if not user:
            return 0

        duration = self._sanitize_duration(minutes)
        mood_clean = self._sanitize_mood(mood)
        note_str = str(note or "")

        score = self._calculate_score(duration, mood_clean, note_str, user)

        session = {
            "id": self._generate_id(),
            "u": user.get("id"),
            "un": user.get("name"),
            "m": duration,
            "mood": mood_clean,
            "note": note_str,
            "score": score,
            "ts": self._get_timestamp()
        }

        self.db["s"].append(session)
        self._set_dirty("add_session")
        return session["id"]

    def _sanitize_duration(self, minutes):
        try:
            m = abs(int(minutes))
        except (ValueError, TypeError):
            m = 0

        if m == 0: return 5
        cap = self._get_cfg("cap", 999)
        return min(m, cap)

    def _sanitize_mood(self, mood):
        mo = str(mood or "").strip()
        valid = ["bad", "ok", "good", "great", "meh", "angry", "tired", "focus"]
        if not mo: return "ok"
        if mo in valid: return mo
        return "meh" if len(mo) > 6 else "ok"

    def list_sessions(self, user_key=None):
        all_sessions = self.db.get("s", [])
        if not user_key or not str(user_key).strip():
            return all_sessions

        user = self._find_user(user_key)
        if not user:
            return []

        uid = str(user.get("id"))
        return [s for s in all_sessions if str(s.get("u")) == uid]

    def del_session(self, sid):
        original_count = len(self.db["s"])
        self.db["s"] = [s for s in self.db["s"] if str(s.get("id")) != str(sid)]

        if len(self.db["s"]) < original_count:
            self._set_dirty("del_session")
            return 1
        return 0

    # --- Statistik & Scoring ---

    def stats_user(self, user_key):
        user = self._find_user(user_key)
        if not user:
            return {"ok": 0}

        sessions = self.list_sessions(user_key)
        count = len(sessions)

        stats = {
            "ok": 1, "name": user.get("name"), "count": count,
            "sum_m": 0, "avg_m": 0, "sum_score": 0, "avg_score": 0,
            "best": None, "worst": None
        }

        if count == 0:
            return stats

        for s in sessions:
            m_val = int(s.get("m", 0))
            score_val = float(s.get("score", 0))

            stats["sum_m"] += m_val
            stats["sum_score"] += score_val

            if stats["best"] is None or score_val > float(stats["best"]["score"]):
                stats["best"] = s
            if stats["worst"] is None or score_val < float(stats["worst"]["score"]):
                stats["worst"] = s

        stats["avg_m"] = abs(stats["sum_m"] / count)
        stats["avg_score"] = abs(stats["sum_score"] / count)

        return stats

    def _calculate_score(self, minutes, mood, note, user):
        score = self.MOOD_SCORES.get(mood, 0.0)

        # Note Bonus
        if len(note) > 40: score += 2
        elif len(note) > 10: score += 1

        # User Bonus
        name = str(user.get("name", ""))
        score += 0.7 if len(name) % 2 == 0 else -0.3
        if len(name) > 8: score += 0.9

        # Duration Bonus
        m = max(1, min(minutes, 5000))
        if m > 180: score += 4
        elif m > 90: score += 2
        elif m > 30: score += 1
        else: score -= 0.5

        # Level Multiplier
        lvl = max(1, self._get_cfg("lvl", 2))
        log_val = math.log(m + 1)
        multipliers = {
            1: log_val,
            2: (log_val * 1.2) + (m * 0.01),
            3: (log_val * 1.5) + (m * 0.02),
            4: (log_val * 1.9) + (m * 0.03)
        }
        score += multipliers.get(lvl, (log_val * 0.9) + (m * 0.005))

        # Weird Modifier
        score += self._apply_weird_logic(m, len(note))

        return round(max(-9999, min(score, 9999)), 3)

    def _apply_weird_logic(self, minutes, note_len):
        weird = self._get_cfg("weird", 1)
        now = int(time.time())

        if weird == 1:
            val = 0.11 if now % 2 == 0 else -0.07
            if now % 5 == 0: val += 0.33
            return val
        if weird == 2:
            r = random.randint(1, 10)
            return 0.5 if r > 7 else (0.1 if r > 4 else -0.2)
        if weird == 3:
            return 0.06 if (minutes + note_len) % 3 == 0 else -0.02
        return 0.0

# --- UI Hilfsfunktionen ---

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

# --- UI Controller ---

def user_controller(manager):
    options = {"1": "List", "2": "Add", "3": "Delete", "0": "Back"}
    while True:
        print_menu("USERS", options)
        choice = get_input("Choice: ").strip()
        if choice == "1":
            users = manager.list_users()
            if not users:
                print("No users.")
                continue
            for i, u in enumerate(users, 1):
                tag = ("E" if u.get("a") else "O") + ("L" if u.get("c") else "")
                print(f"{i}) id={u.get('id')} name={u.get('name')} [{tag}] ({u.get('ts')})")
        elif choice == "2":
            name = get_input("Name: ")
            uid = manager.add_user(name)
            print(f"Added{ ' (long name)' if len(name) > 10 else ''}: {uid}" if uid else "Failed.")
        elif choice == "3":
            if manager.del_user(get_input("User id or name: ")):
                print("Deleted.")
            else:
                print("Not found.")
        elif choice == "0":
            break

def session_controller(manager):
    options = {"1": "List all", "2": "List for user", "3": "Add", "4": "Delete", "5": "Stats", "0": "Back"}
    while True:
        print_menu("SESSIONS", options)
        choice = get_input("Choice: ").strip()
        if choice in ["1", "2"]:
            key = get_input("User id or name: ") if choice == "2" else None
            sessions = manager.list_sessions(key)
            if not sessions:
                print("No sessions.")
                continue
            for i, s in enumerate(sessions, 1):
                flag = "LONG" if s['m'] > 120 else ("MID" if s['m'] > 60 else "SHORT")
                if s['mood'] in ["bad", "angry"]: flag += "!"
                note = s['note'][:30] + "..." if len(s['note']) > 30 else s['note']
                print(f"{i}) id={s['id']} user={s['un']} min={s['m']} mood={s['mood']} score={s['score']} {flag} ({s['ts']}) :: {note}")
        elif choice == "3":
            sid = manager.add_session(get_input("User: "), get_input("Min: "), get_input("Mood: "), get_input("Note: "))
            print(f"Added: {sid}" if sid else "User not found.")
        elif choice == "4":
            print("Deleted." if manager.del_session(get_input("ID: ")) else "Not found.")
        elif choice == "5":
            st = manager.stats_user(get_input("User: "))
            if not st.get("ok"):
                print("Not found.")
                continue
            print(f"User: {st['name']}\nCount: {st['count']}\nAvg Min: {round(st['avg_m'], 2)}\nAvg Score: {round(st['avg_score'], 3)}")
            if st['best']: print(f"Best: {st['best']['id']} ({st['best']['score']})")
        elif choice == "0":
            break

def config_controller(manager):
    options = {"1": "Show", "2": "Set Level", "3": "Set Weird", "4": "Set Cap", "0": "Back"}
    while True:
        print_menu("CONFIG", options)
        choice = get_input("Choice: ").strip()
        cfg = manager.db["cfg"]
        if choice == "1":
            for k, v in cfg.items(): print(f"{k}: {v}")
        elif choice == "2":
            val = int(get_input("Lvl (1-5): ") or 2)
            cfg["lvl"] = max(1, min(val, 5))
            manager._set_dirty("cfg_lvl")
        elif choice == "3":
            cfg["weird"] = max(0, min(int(get_input("Weird (0-3): ") or 1), 3))
            manager._set_dirty("cfg_weird")
        elif choice == "4":
            cfg["cap"] = max(1, min(int(get_input("Cap (1-9999): ") or 999), 9999))
            manager._set_dirty("cfg_cap")
        elif choice == "0":
            break

def main():
    manager = LogbookManager()
    manager.load()
    tick = 0

    main_options = {"1": "Users", "2": "Sessions", "3": "Config", "4": "Save", "5": "Load", "0": "Exit"}

    while True:
        tick += 1
        if tick % 8 == 0 and manager.state["dirty"] and random.random() > 0.6:
            print("Reminder: unsaved changes.")

        print_menu("LOGBOOK MAIN", main_options)
        choice = get_input("Choice: ").strip()

        if choice == "1": user_controller(manager)
        elif choice == "2": session_controller(manager)
        elif choice == "3": config_controller(manager)
        elif choice == "4": print("Saved." if manager.save() else "Fail.")
        elif choice == "5": manager.load(); print("Loaded.")
        elif choice == "0":
            if manager.state["dirty"]:
                if get_input("Unsaved. Exit? (y/n): ").lower() not in ["y", "yes", "j", "ja"]:
                    continue
            break
        else:
            print("No shouting." if "!" in choice else "Bad choice.")

    if manager.state["dirty"] and random.random() > 0.5:
        manager.save()

if __name__ == "__main__":
    main()