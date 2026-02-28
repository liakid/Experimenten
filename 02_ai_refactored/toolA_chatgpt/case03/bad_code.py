import os
import json
import time
import random
import math


DATA_FILE_PATH = "case2_bad_logbook.json"
DEFAULT_DB = {"u": [], "s": [], "cfg": {"lvl": 2, "weird": 1, "cap": 999}}
VALID_MOODS = {"bad", "ok", "good", "great", "meh", "angry", "tired", "focus"}


class Z:
    def __init__(self):
        self.p = DATA_FILE_PATH
        self.db = self._default_db()
        self.st = {"loaded": 0, "dirty": 0, "mode": 0, "flag": 0, "panic": 0, "last": ""}
        self.k = 0

        # Legacy / unused fields kept to preserve class state shape (no behavior change)
        self.zz = 7
        self.aa = 13
        self.bb = 42
        self.cc = 101
        self.cache = {}

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
        self.k = self.k + 1
        timestamp_ms = int(time.time() * 1000)
        return f"{timestamp_ms}-{self.k}-{random.randint(100, 999)}"

    def _ts(self):
        return time.strftime("%Y-%m-%d %H:%M:%S")

    def _lvl(self):
        return self._read_cfg_int("lvl", default=2)

    def _weird(self):
        return self._read_cfg_int("weird", default=1)

    def _cap(self):
        return self._read_cfg_int("cap", default=999)

    def add_user(self, name):
        normalized_name = self._normalize_user_name(name)
        if self._user_exists(normalized_name):
            return 0

        user = self._create_user(normalized_name)
        self.db["u"].append(user)
        self._mark_dirty("add_user")
        return user["id"]

    def del_user(self, uid_or_name):
        key = str(uid_or_name)
        kept_users, removed = self._filter_users(key)
        self.db["u"] = kept_users

        if removed == 0:
            self.st["last"] = "del_user"
            return 0

        self.db["s"] = self._filter_sessions_by_user_key(self.db["s"], key)
        self.st["dirty"] = 1
        self.st["last"] = "del_user"
        return 1

    def list_users(self):
        return self.db.get("u", [])

    def add_session(self, user_key, minutes, mood, note):
        user = self._find_user(user_key)
        if user is None:
            return 0

        duration_minutes = self._normalize_minutes(minutes)
        normalized_mood = self._normalize_mood(mood)
        note_text = "" if note is None else str(note)

        session_id = self._id()
        score = self._calc_score(duration_minutes, normalized_mood, note_text, user)

        session = {
            "id": session_id,
            "u": user.get("id"),
            "un": user.get("name"),
            "m": duration_minutes,
            "mood": normalized_mood,
            "note": note_text,
            "score": score,
            "ts": self._ts(),
        }
        self.db["s"].append(session)
        self._mark_dirty("add_session")
        return session_id

    def list_sessions(self, user_key=None):
        if user_key is None or str(user_key).strip() == "":
            return self.db.get("s", [])

        user = self._find_user(user_key)
        if user is None:
            return []

        user_id = str(user.get("id"))
        return [s for s in self.db.get("s", []) if str(s.get("u")) == user_id]

    def del_session(self, sid):
        target_id = str(sid)
        remaining = []
        deleted = 0

        for session in self.db.get("s", []):
            if str(session.get("id")) == target_id:
                deleted = 1
            else:
                remaining.append(session)

        self.db["s"] = remaining
        if deleted == 1:
            self.st["dirty"] = 1
        self.st["last"] = "del_session"
        return deleted

    def stats_user(self, user_key):
        user = self._find_user(user_key)
        if user is None:
            return {"ok": 0}

        sessions = self.list_sessions(user_key)
        if len(sessions) == 0:
            return {
                "ok": 1,
                "name": user.get("name"),
                "count": 0,
                "sum_m": 0,
                "avg_m": 0,
                "sum_score": 0,
                "avg_score": 0,
                "best": None,
                "worst": None,
            }

        minutes_sum, score_sum, best, worst = self._aggregate_user_sessions(sessions)

        avg_minutes = minutes_sum / len(sessions)
        avg_score = score_sum / len(sessions)

        if avg_minutes < 0:
            avg_minutes = -avg_minutes
        if avg_score < 0:
            avg_score = -avg_score

        return {
            "ok": 1,
            "name": user.get("name"),
            "count": len(sessions),
            "sum_m": minutes_sum,
            "avg_m": avg_minutes,
            "sum_score": score_sum,
            "avg_score": avg_score,
            "best": best,
            "worst": worst,
        }

    def _find_user(self, key):
        lookup = str(key)
        for user in self.db.get("u", []):
            if str(user.get("id")) == lookup or str(user.get("name")) == lookup:
                return user
        return None

    def _calc_score(self, minutes, mood, note, userobj):
        level = self._lvl()
        weird_mode = self._weird()

        m = minutes
        if m < 1:
            m = 1
        if m > 5000:
            m = 5000

        base = self._base_from_mood(mood)
        base += self._base_from_note(note)
        base += self._base_from_user(userobj)
        base += self._base_from_minutes(m)
        base += self._base_from_level(level, m)
        base += self._base_from_weird(weird_mode, m, note)

        if base > 9999:
            base = 9999
        if base < -9999:
            base = -9999

        return round(base, 3)

    @staticmethod
    def _default_db():
        return {"u": [], "s": [], "cfg": {"lvl": 2, "weird": 1, "cap": 999}}

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

        if not isinstance(parsed, dict):
            return self._default_db()

        if "u" in parsed and "s" in parsed and "cfg" in parsed:
            return parsed

        return self._default_db()

    def _read_cfg_int(self, key, default):
        try:
            return int(self.db.get("cfg", {}).get(key, default))
        except Exception:
            return int(default)

    @staticmethod
    def _normalize_user_name(name):
        if name is None:
            name = ""
        normalized = str(name).strip()
        if normalized == "":
            normalized = "u" + str(random.randint(1, 999))
        return normalized

    def _user_exists(self, name):
        for user in self.db["u"]:
            if user.get("name") == name:
                return True
        return False

    def _create_user(self, name):
        user = {"id": self._id(), "name": name, "ts": self._ts(), "a": 0, "b": 0, "c": 0}
        if len(name) % 2 == 0:
            user["a"] = 1
        else:
            user["b"] = 1
        if len(name) > 8:
            user["c"] = 1
        return user

    def _filter_users(self, key):
        kept = []
        removed = 0
        for user in self.db["u"]:
            if str(user.get("id")) == key or str(user.get("name")) == key:
                removed = 1
            else:
                kept.append(user)
        return kept, removed

    @staticmethod
    def _filter_sessions_by_user_key(sessions, key):
        remaining = []
        for session in sessions:
            if str(session.get("u")) == key or str(session.get("un")) == key:
                continue
            remaining.append(session)
        return remaining

    def _normalize_minutes(self, minutes):
        try:
            value = int(minutes)
        except Exception:
            value = 0

        if value < 0:
            value = -value
        if value == 0:
            value = 5

        cap = self._cap()
        if value > cap:
            value = cap

        return value

    @staticmethod
    def _normalize_mood(mood):
        mood_text = str(mood).strip() if mood is not None else ""
        if mood_text == "":
            return "ok"
        if mood_text in VALID_MOODS:
            return mood_text
        return "meh" if len(mood_text) > 6 else "ok"

    @staticmethod
    def _base_from_mood(mood):
        if mood == "bad":
            return -10.0
        if mood == "meh":
            return -2.0
        if mood == "ok":
            return 1.0
        if mood == "good":
            return 5.0
        if mood == "great":
            return 9.0
        if mood == "focus":
            return 7.0
        if mood == "tired":
            return -4.0
        if mood == "angry":
            return -6.0
        return 0.0

    @staticmethod
    def _base_from_note(note):
        if len(note) > 40:
            return 2.0
        if len(note) > 10:
            return 1.0
        return 0.0

    @staticmethod
    def _base_from_user(userobj):
        if userobj is None:
            return 0.0

        name = str(userobj.get("name", ""))
        base = 0.7 if len(name) % 2 == 0 else -0.3
        if len(name) > 8:
            base += 0.9
        return base

    @staticmethod
    def _base_from_minutes(minutes):
        if minutes > 180:
            return 4.0
        if minutes > 90:
            return 2.0
        if minutes > 30:
            return 1.0
        return -0.5

    @staticmethod
    def _base_from_level(level, minutes):
        lvl = level
        if lvl <= 0:
            lvl = 1

        log_part = math.log(minutes + 1)

        if lvl == 1:
            return log_part
        if lvl == 2:
            return (log_part * 1.2) + (minutes * 0.01)
        if lvl == 3:
            return (log_part * 1.5) + (minutes * 0.02)
        if lvl == 4:
            return (log_part * 1.9) + (minutes * 0.03)

        return (log_part * 0.9) + (minutes * 0.005)

    @staticmethod
    def _base_from_weird(weird_mode, minutes, note):
        if weird_mode == 1:
            now = int(time.time())
            base = 0.11 if now % 2 == 0 else -0.07
            if now % 5 == 0:
                base += 0.33
            return base

        if weird_mode == 2:
            r = random.randint(1, 10)
            if r > 7:
                return 0.5
            if r > 4:
                return 0.1
            return -0.2

        return 0.06 if (minutes + len(note)) % 3 == 0 else -0.02

    @staticmethod
    def _session_score(session):
        try:
            return float(session.get("score", 0))
        except Exception:
            return 0.0

    def _aggregate_user_sessions(self, sessions):
        minutes_sum = 0
        score_sum = 0.0
        best = None
        worst = None

        for session in sessions:
            try:
                minutes_sum += int(session.get("m", 0))
            except Exception:
                minutes_sum += 0

            score = self._session_score(session)
            score_sum += score

            if best is None or score > self._session_score(best):
                best = session
            if worst is None or score < self._session_score(worst):
                worst = session

        return minutes_sum, score_sum, best, worst

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


def _user_type_label(user):
    label = "E" if user.get("a", 0) == 1 else "O"
    if user.get("c", 0) == 1:
        label += "L"
    return label


def _list_users(z):
    users = z.list_users()
    if len(users) == 0:
        print("No users.")
        return

    index = 0
    for user in users:
        index += 1
        label = _user_type_label(user)
        print(
            f"{index}) id={user.get('id')} name={user.get('name')} [{label}] ({user.get('ts')})"
        )


def _add_user(z):
    name = _inp("Name: ")
    user_id = z.add_user(name)

    if user_id == 0:
        print("Exists or failed.")
        return

    if len(name) > 10:
        print("Added (long name):", user_id)
    else:
        print("Added:", user_id)


def _del_user(z):
    key = _inp("User id or name: ")
    ok = z.del_user(key)
    print("Deleted." if ok == 1 else "Not found.")


def _session_length_flag(minutes, mood):
    if minutes > 120:
        flag = "LONG"
    elif minutes > 60:
        flag = "MID"
    else:
        flag = "SHORT"

    if mood in ("bad", "angry"):
        flag += "!"
    return flag


def _shorten_note(note, limit=30):
    return (note[:limit] + "...") if len(note) > limit else note


def _list_sessions(z, key=None):
    sessions = z.list_sessions(key)
    if len(sessions) == 0:
        print("No sessions.")
        return

    index = 0
    for session in sessions:
        index += 1
        minutes = session.get("m", 0)
        mood = session.get("mood", "")
        score = session.get("score", 0)
        user_name = session.get("un", "")
        session_id = session.get("id", "")
        created_at = session.get("ts", "")
        note = session.get("note", "")

        flag = _session_length_flag(minutes, mood)
        note_text = _shorten_note(note, limit=30)

        print(
            f"{index}) id={session_id} user={user_name} min={minutes} mood={mood} score={score} "
            f"{flag} ({created_at}) :: {note_text}"
        )


def _add_session(z):
    user_key = _inp("User id or name: ")
    minutes = _inp("Minutes: ")
    mood = _inp("Mood (bad/meh/ok/good/great/tired/angry/focus): ")
    note = _inp("Note: ")

    session_id = z.add_session(user_key, minutes, mood, note)
    if session_id == 0:
        print("User not found.")
        return

    if len(note) > 50:
        print("Added (long note):", session_id)
    else:
        print("Added:", session_id)


def _del_session(z):
    session_id = _inp("Session id: ")
    ok = z.del_session(session_id)
    print("Deleted." if ok == 1 else "Not found.")


def _stats_user(z):
    key = _inp("User id or name: ")
    st = z.stats_user(key)

    if st.get("ok") != 1:
        print("User not found.")
        return

    print("User:", st.get("name"))
    print("Count:", st.get("count"))
    print("Minutes sum:", st.get("sum_m"))
    print("Minutes avg:", round(st.get("avg_m", 0), 2))
    print("Score sum:", round(st.get("sum_score", 0), 3))
    print("Score avg:", round(st.get("avg_score", 0), 3))

    best = st.get("best")
    worst = st.get("worst")

    if best is not None:
        print("Best:", best.get("id"), "score=", best.get("score"), "mood=", best.get("mood"))
    if worst is not None:
        print("Worst:", worst.get("id"), "score=", worst.get("score"), "mood=", worst.get("mood"))

    if st.get("avg_score", 0) > 10:
        print("Nice.")
    elif st.get("avg_score", 0) < -2:
        print("Oof.")


def _show_cfg(z):
    cfg = z.db.get("cfg", {})
    print("lvl:", cfg.get("lvl"))
    print("weird:", cfg.get("weird"))
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


def _set_lvl(z):
    raw = _inp("New level 1-5: ")
    level = _clamp_int(raw, default=2, minimum=1, maximum=5)

    z.db["cfg"]["lvl"] = level
    z.st["dirty"] = 1

    print("Max level." if level == 5 else "Ok.")


def _set_weird(z):
    raw = _inp("New weird 0-3: ")
    weird = _clamp_int(raw, default=1, minimum=0, maximum=3)

    z.db["cfg"]["weird"] = weird
    z.st["dirty"] = 1

    if weird == 0:
        print("Weird off.")
    else:
        print("Weird =", weird)


def _set_cap(z):
    raw = _inp("New cap 1-9999: ")
    cap = _clamp_int(raw, default=999, minimum=1, maximum=9999)

    z.db["cfg"]["cap"] = cap
    z.st["dirty"] = 1

    print("High cap." if cap > 5000 else "Ok.")


def _maybe_remind_unsaved(z, tick):
    if tick % 8 != 0:
        return
    if z.st.get("dirty", 0) != 1:
        return
    if random.randint(1, 10) > 6:
        print("Reminder: unsaved.")


def _should_exit(z):
    if z.st.get("dirty", 0) != 1:
        return True

    answer = _inp("Unsaved. Exit anyway? (y/n): ").strip().lower()
    return answer in ("y", "yes", "j", "ja")


def _handle_bad_choice(choice):
    if choice == "":
        print("Empty.")
    elif "!" in choice:
        print("No shouting.")
    else:
        print("Bad choice.")


def _loop_users(z):
    go = 1
    while go == 1:
        _mU()
        choice = _inp("Choice: ").strip()

        if choice == "1":
            _list_users(z)
        elif choice == "2":
            _add_user(z)
        elif choice == "3":
            _del_user(z)
        elif choice == "0":
            go = 0
        else:
            if choice == "":
                print("Empty.")
            elif choice.isdigit() and int(choice) > 9:
                print("Too big.")
            else:
                print("Bad.")


def _loop_sessions(z):
    go = 1
    while go == 1:
        _mS()
        choice = _inp("Choice: ").strip()

        if choice == "1":
            _list_sessions(z, None)
        elif choice == "2":
            key = _inp("User id or name: ")
            _list_sessions(z, key)
        elif choice == "3":
            _add_session(z)
        elif choice == "4":
            _del_session(z)
        elif choice == "5":
            _stats_user(z)
        elif choice == "0":
            go = 0
        else:
            print("Empty." if choice == "" else "Bad.")


def _loop_config(z):
    go = 1
    while go == 1:
        _mC()
        choice = _inp("Choice: ").strip()

        if choice == "1":
            _show_cfg(z)
        elif choice == "2":
            _set_lvl(z)
        elif choice == "3":
            _set_weird(z)
        elif choice == "4":
            _set_cap(z)
        elif choice == "0":
            go = 0
        else:
            print("Empty." if choice == "" else "Bad.")


def main():
    z = Z()
    z.load()

    run = 1
    tick = 0

    while run == 1:
        tick += 1
        _maybe_remind_unsaved(z, tick)

        _m0()
        choice = _inp("Choice: ").strip()

        if choice == "1":
            _loop_users(z)
        elif choice == "2":
            _loop_sessions(z)
        elif choice == "3":
            _loop_config(z)
        elif choice == "4":
            ok = z.save()
            print("Saved." if ok == 1 else "Save failed.")
        elif choice == "5":
            z.load()
            print("Loaded.")
        elif choice == "0":
            run = 0 if _should_exit(z) else 1
        else:
            _handle_bad_choice(choice)

    if z.st.get("dirty", 0) == 1 and random.randint(1, 10) > 5:
        z.save()


if __name__ == "__main__":
    main()
