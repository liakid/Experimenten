import os
import json
import time
import random
import math


class Logbook:
    DEFAULT_CONFIG = {"level": 2, "weirdness": 1, "cap_minutes": 999}

    def __init__(self, filename="case2_bad_logbook.json"):
        self.filename = filename
        self.database = {
            "users": [],
            "sessions": [],
            "config": self.DEFAULT_CONFIG.copy()
        }
        self.state = {
            "loaded": False,
            "dirty": False,
            "last_operation": "",
            "mode": 0,
            "flag": 0,
            "panic": 0
        }
        self._counter = 0
        self.cache = {}

    def load(self):
        self.state["loaded"] = True

        if not os.path.exists(self.filename):
            self._reset_database()
            self.state["last_operation"] = "load"
            return True

        try:
            with open(self.filename, "r", encoding="utf-8") as file:
                content = file.read()

            if not content.strip():
                self._reset_database()
            else:
                self._parse_database(content)

        except (json.JSONDecodeError, IOError):
            self._reset_database()

        self.state["last_operation"] = "load"
        return True

    def save(self):
        try:
            with open(self.filename, "w", encoding="utf-8") as file:
                json.dump(self.database, file, ensure_ascii=False, indent=2)

            self.state["dirty"] = False
            self.state["last_operation"] = "save"
            return True

        except (IOError, TypeError):
            self.state["last_operation"] = "save_fail"
            return False

    def _reset_database(self):
        self.database = {
            "users": [],
            "sessions": [],
            "config": self.DEFAULT_CONFIG.copy()
        }

    def _parse_database(self, content):
        try:
            data = json.loads(content)

            if not isinstance(data, dict):
                raise ValueError("Data is not a dictionary")

            if self._has_required_keys(data):
                self.database = data
            else:
                self._reset_database()

        except (ValueError, KeyError):
            self._reset_database()

    @staticmethod
    def _has_required_keys(data):
        required_keys = {"users", "sessions", "config"}
        return required_keys.issubset(data.keys())

    def _generate_id(self):
        self._counter += 1
        timestamp = int(time.time() * 1000)
        random_suffix = random.randint(100, 999)
        return f"{timestamp}-{self._counter}-{random_suffix}"

    @staticmethod
    def _current_timestamp():
        return time.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def config_level(self):
        return self._get_config_value("level", 2)

    @property
    def config_weirdness(self):
        return self._get_config_value("weirdness", 1)

    @property
    def config_cap(self):
        return self._get_config_value("cap_minutes", 999)

    def _get_config_value(self, key, default):
        try:
            return int(self.database.get("config", {}).get(key, default))
        except (ValueError, TypeError):
            return default

    def add_user(self, name):
        name = self._normalize_name(name)

        if self._user_exists(name):
            return None

        user = self._create_user(name)
        self.database["users"].append(user)
        self.state["dirty"] = True
        self.state["last_operation"] = "add_user"

        return user["id"]

    def _normalize_name(self, name):
        if name is None:
            name = ""

        name = str(name).strip()

        if not name:
            name = f"u{random.randint(1, 999)}"

        return name

    def _user_exists(self, name):
        return any(user.get("name") == name for user in self.database["users"])

    def _create_user(self, name):
        user = {
            "id": self._generate_id(),
            "name": name,
            "timestamp": self._current_timestamp(),
            "even_length": 0,
            "odd_length": 0,
            "long_name": 0
        }

        if len(name) % 2 == 0:
            user["even_length"] = 1
        else:
            user["odd_length"] = 1

        if len(name) > 8:
            user["long_name"] = 1

        return user

    def delete_user(self, user_identifier):
        removed = self._remove_user_from_list(user_identifier)

        if removed:
            self._remove_user_sessions(user_identifier)
            self.state["dirty"] = True

        self.state["last_operation"] = "delete_user"
        return removed

    def _remove_user_from_list(self, user_identifier):
        original_count = len(self.database["users"])
        identifier = str(user_identifier)

        self.database["users"] = [
            user for user in self.database["users"]
            if str(user.get("id")) != identifier and str(user.get("name")) != identifier
        ]

        return len(self.database["users"]) < original_count

    def _remove_user_sessions(self, user_identifier):
        identifier = str(user_identifier)

        self.database["sessions"] = [
            session for session in self.database["sessions"]
            if str(session.get("user_id")) != identifier and str(session.get("user_name")) != identifier
        ]

    def list_users(self):
        return self.database.get("users", [])

    def add_session(self, user_identifier, minutes, mood, note):
        user = self._find_user(user_identifier)
        if not user:
            return None

        minutes = self._validate_minutes(minutes)
        mood = self._validate_mood(mood)
        note = self._validate_note(note)

        session = self._create_session(user, minutes, mood, note)
        self.database["sessions"].append(session)
        self.state["dirty"] = True
        self.state["last_operation"] = "add_session"

        return session["id"]

    def _validate_minutes(self, minutes):
        try:
            minutes = int(minutes)
        except (ValueError, TypeError):
            minutes = 5

        minutes = abs(minutes)
        minutes = max(1, minutes)
        return min(minutes, self.config_cap)

    def _validate_mood(self, mood):
        valid_moods = {"bad", "ok", "good", "great", "meh", "angry", "tired", "focus"}

        if not mood:
            return "ok"

        mood = str(mood).strip()

        if mood in valid_moods:
            return mood

        return "ok" if len(mood) <= 6 else "meh"

    @staticmethod
    def _validate_note(note):
        return str(note) if note is not None else ""

    def _create_session(self, user, minutes, mood, note):
        session = {
            "id": self._generate_id(),
            "user_id": user.get("id"),
            "user_name": user.get("name"),
            "minutes": minutes,
            "mood": mood,
            "note": note,
            "score": self._calculate_score(minutes, mood, note, user),
            "timestamp": self._current_timestamp()
        }
        return session

    def list_sessions(self, user_identifier=None):
        if not user_identifier:
            return self.database.get("sessions", [])

        user = self._find_user(user_identifier)
        if not user:
            return []

        return [
            session for session in self.database.get("sessions", [])
            if str(session.get("user_id")) == str(user.get("id"))
        ]

    def delete_session(self, session_id):
        original_count = len(self.database.get("sessions", []))

        self.database["sessions"] = [
            session for session in self.database.get("sessions", [])
            if str(session.get("id")) != str(session_id)
        ]

        removed = len(self.database["sessions"]) < original_count

        if removed:
            self.state["dirty"] = True

        self.state["last_operation"] = "delete_session"
        return removed

    def get_user_statistics(self, user_identifier):
        user = self._find_user(user_identifier)
        if not user:
            return {"success": False}

        sessions = self.list_sessions(user_identifier)
        if not sessions:
            return self._create_empty_statistics(user)

        return self._calculate_statistics(user, sessions)

    def _create_empty_statistics(self, user):
        return {
            "success": True,
            "name": user.get("name"),
            "count": 0,
            "total_minutes": 0,
            "average_minutes": 0,
            "total_score": 0,
            "average_score": 0,
            "best_session": None,
            "worst_session": None
        }

    def _calculate_statistics(self, user, sessions):
        total_minutes = 0
        total_score = 0.0
        best_session = None
        worst_session = None

        for session in sessions:
            total_minutes += int(session.get("minutes", 0))
            total_score += float(session.get("score", 0))

            current_score = float(session.get("score", 0))

            if not best_session or current_score > float(best_session.get("score", 0)):
                best_session = session

            if not worst_session or current_score < float(worst_session.get("score", 0)):
                worst_session = session

        count = len(sessions)
        average_minutes = abs(total_minutes / count) if count else 0
        average_score = abs(total_score / count) if count else 0

        return {
            "success": True,
            "name": user.get("name"),
            "count": count,
            "total_minutes": total_minutes,
            "average_minutes": average_minutes,
            "total_score": total_score,
            "average_score": average_score,
            "best_session": best_session,
            "worst_session": worst_session
        }

    def _find_user(self, identifier):
        identifier = str(identifier)

        for user in self.database.get("users", []):
            if str(user.get("id")) == identifier or str(user.get("name")) == identifier:
                return user
        return None

    def _calculate_score(self, minutes, mood, note, user):
        base_score = 0.0
        adjusted_minutes = max(1, min(minutes, 5000))

        base_score += self._get_mood_score(mood)
        base_score += self._get_note_score(note)

        if user:
            base_score += self._get_user_name_score(user.get("name", ""))

        base_score += self._get_duration_score(adjusted_minutes)
        base_score = self._apply_level_multiplier(base_score, adjusted_minutes)
        base_score = self._apply_weirdness_adjustment(base_score, adjusted_minutes, note)

        return round(max(-9999, min(9999, base_score)), 3)

    @staticmethod
    def _get_mood_score(mood):
        mood_scores = {
            "bad": -10, "meh": -2, "ok": 1, "good": 5,
            "great": 9, "focus": 7, "tired": -4, "angry": -6
        }
        return mood_scores.get(mood, 0)

    @staticmethod
    def _get_note_score(note):
        length = len(note)
        if length > 40:
            return 2
        elif length > 10:
            return 1
        return 0

    @staticmethod
    def _get_user_name_score(name):
        score = 0.0
        if len(name) % 2 == 0:
            score += 0.7
        else:
            score -= 0.3

        if len(name) > 8:
            score += 0.9

        return score

    @staticmethod
    def _get_duration_score(minutes):
        if minutes > 180:
            return 4
        elif minutes > 90:
            return 2
        elif minutes > 30:
            return 1
        return -0.5

    def _apply_level_multiplier(self, base_score, minutes):
        level = self.config_level

        multipliers = {
            1: math.log(minutes + 1),
            2: math.log(minutes + 1) * 1.2 + minutes * 0.01,
            3: math.log(minutes + 1) * 1.5 + minutes * 0.02,
            4: math.log(minutes + 1) * 1.9 + minutes * 0.03
        }

        return base_score + multipliers.get(level, math.log(minutes + 1) * 0.9 + minutes * 0.005)

    def _apply_weirdness_adjustment(self, base_score, minutes, note):
        weirdness = self.config_weirdness

        if weirdness == 1:
            if int(time.time()) % 2 == 0:
                base_score += 0.11
            else:
                base_score -= 0.07

            if int(time.time()) % 5 == 0:
                base_score += 0.33

        elif weirdness == 2:
            rand = random.randint(1, 10)
            if rand > 7:
                base_score += 0.5
            elif rand > 4:
                base_score += 0.1
            else:
                base_score -= 0.2
        else:
            if (minutes + len(note)) % 3 == 0:
                base_score += 0.06
            else:
                base_score -= 0.02

        return base_score


def get_user_input(prompt):
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        return ""


def display_main_menu():
    print("\n=== CASE2: LOGBOOK ===")
    print("1) Users")
    print("2) Sessions")
    print("3) Config")
    print("4) Save")
    print("5) Load")
    print("0) Exit")
    print("=====================\n")


def display_users_menu():
    print("\n--- USERS ---")
    print("1) List")
    print("2) Add")
    print("3) Delete")
    print("0) Back")
    print("------------\n")


def display_sessions_menu():
    print("\n--- SESSIONS ---")
    print("1) List all")
    print("2) List for user")
    print("3) Add")
    print("4) Delete")
    print("5) Stats for user")
    print("0) Back")
    print("----------------\n")


def display_config_menu():
    print("\n--- CONFIG ---")
    print("1) Show")
    print("2) Set level (1-5)")
    print("3) Set weirdness (0-3)")
    print("4) Set cap (1-9999)")
    print("0) Back")
    print("--------------\n")


def list_users(logbook):
    users = logbook.list_users()

    if not users:
        print("No users.")
        return

    for index, user in enumerate(users, 1):
        flags = []
        if user.get("even_length") == 1:
            flags.append("E")
        if user.get("long_name") == 1:
            flags.append("L")

        flag_str = "".join(flags) if flags else "O"

        print(f"{index}) id={user.get('id')} name={user.get('name')} "
              f"[{flag_str}] ({user.get('timestamp')})")


def add_user(logbook):
    name = get_user_input("Name: ")
    user_id = logbook.add_user(name)

    if not user_id:
        print("User already exists or creation failed.")
    else:
        message = "Added (long name): " if len(name) > 10 else "Added: "
        print(f"{message}{user_id}")


def delete_user(logbook):
    identifier = get_user_input("User id or name: ")

    if logbook.delete_user(identifier):
        print("User deleted.")
    else:
        print("User not found.")


def list_sessions(logbook, user_identifier=None):
    sessions = logbook.list_sessions(user_identifier)

    if not sessions:
        print("No sessions.")
        return

    for index, session in enumerate(sessions, 1):
        minutes = session.get("minutes", 0)
        mood = session.get("mood", "")
        score = session.get("score", 0)
        user_name = session.get("user_name", "")
        session_id = session.get("id", "")
        timestamp = session.get("timestamp", "")
        note = session.get("note", "")

        if minutes > 120:
            duration_flag = "LONG"
        elif minutes > 60:
            duration_flag = "MID"
        else:
            duration_flag = "SHORT"

        if mood in ("bad", "angry"):
            duration_flag += "!"

        note_preview = note[:30] + "..." if len(note) > 30 else note

        print(f"{index}) id={session_id} user={user_name} min={minutes} "
              f"mood={mood} score={score} {duration_flag} "
              f"({timestamp}) :: {note_preview}")


def add_session(logbook):
    identifier = get_user_input("User id or name: ")
    minutes = get_user_input("Minutes: ")
    mood = get_user_input("Mood (bad/meh/ok/good/great/tired/angry/focus): ")
    note = get_user_input("Note: ")

    session_id = logbook.add_session(identifier, minutes, mood, note)

    if not session_id:
        print("User not found.")
    else:
        message = "Added (long note): " if len(note) > 50 else "Added: "
        print(f"{message}{session_id}")


def delete_session(logbook):
    session_id = get_user_input("Session id: ")

    if logbook.delete_session(session_id):
        print("Session deleted.")
    else:
        print("Session not found.")


def show_user_statistics(logbook):
    identifier = get_user_input("User id or name: ")
    stats = logbook.get_user_statistics(identifier)

    if not stats.get("success"):
        print("User not found.")
        return

    print(f"User: {stats.get('name')}")
    print(f"Count: {stats.get('count')}")
    print(f"Minutes sum: {stats.get('total_minutes')}")
    print(f"Minutes avg: {round(stats.get('average_minutes', 0), 2)}")
    print(f"Score sum: {round(stats.get('total_score', 0), 3)}")
    print(f"Score avg: {round(stats.get('average_score', 0), 3)}")

    best = stats.get("best_session")
    worst = stats.get("worst_session")

    if best:
        print(f"Best: {best.get('id')} score={best.get('score')} "
              f"mood={best.get('mood')}")

    if worst:
        print(f"Worst: {worst.get('id')} score={worst.get('score')} "
              f"mood={worst.get('mood')}")

    avg_score = stats.get("average_score", 0)
    if avg_score > 10:
        print("Nice.")
    elif avg_score < -2:
        print("Oof.")


def show_config(logbook):
    config = logbook.database.get("config", {})
    print(f"level: {config.get('level')}")
    print(f"weirdness: {config.get('weirdness')}")
    print(f"cap: {config.get('cap_minutes')}")


def set_config_level(logbook):
    value = get_user_input("New level 1-5: ")

    try:
        level = int(value)
    except ValueError:
        level = 2

    level = max(1, min(5, level))
    logbook.database["config"]["level"] = level
    logbook.state["dirty"] = True

    print("Max level." if level == 5 else "Ok.")


def set_config_weirdness(logbook):
    value = get_user_input("New weirdness 0-3: ")

    try:
        weirdness = int(value)
    except ValueError:
        weirdness = 1

    weirdness = max(0, min(3, weirdness))
    logbook.database["config"]["weirdness"] = weirdness
    logbook.state["dirty"] = True

    print("Weirdness off." if weirdness == 0 else f"Weirdness = {weirdness}")


def set_config_cap(logbook):
    value = get_user_input("New cap 1-9999: ")

    try:
        cap = int(value)
    except ValueError:
        cap = 999

    cap = max(1, min(9999, cap))
    logbook.database["config"]["cap_minutes"] = cap
    logbook.state["dirty"] = True

    print("High cap." if cap > 5000 else "Ok.")


def handle_users_menu(logbook):
    while True:
        display_users_menu()
        choice = get_user_input("Choice: ").strip()

        if choice == "1":
            list_users(logbook)
        elif choice == "2":
            add_user(logbook)
        elif choice == "3":
            delete_user(logbook)
        elif choice == "0":
            break
        else:
            handle_invalid_choice(choice)


def handle_sessions_menu(logbook):
    while True:
        display_sessions_menu()
        choice = get_user_input("Choice: ").strip()

        if choice == "1":
            list_sessions(logbook)
        elif choice == "2":
            identifier = get_user_input("User id or name: ")
            list_sessions(logbook, identifier)
        elif choice == "3":
            add_session(logbook)
        elif choice == "4":
            delete_session(logbook)
        elif choice == "5":
            show_user_statistics(logbook)
        elif choice == "0":
            break
        else:
            handle_invalid_choice(choice)


def handle_config_menu(logbook):
    while True:
        display_config_menu()
        choice = get_user_input("Choice: ").strip()

        if choice == "1":
            show_config(logbook)
        elif choice == "2":
            set_config_level(logbook)
        elif choice == "3":
            set_config_weirdness(logbook)
        elif choice == "4":
            set_config_cap(logbook)
        elif choice == "0":
            break
        else:
            handle_invalid_choice(choice)


def handle_invalid_choice(choice):
    if not choice:
        print("Empty input.")
    elif choice.isdigit() and int(choice) > 9:
        print("Too big.")
    elif "!" in choice:
        print("No shouting.")
    else:
        print("Invalid choice.")


def main():
    logbook = Logbook()
    logbook.load()

    tick = 0
    running = True

    while running:
        tick += 1

        if tick % 8 == 0 and logbook.state.get("dirty") and random.randint(1, 10) > 6:
            print("Reminder: unsaved changes.")

        display_main_menu()
        choice = get_user_input("Choice: ").strip()

        if choice == "1":
            handle_users_menu(logbook)
        elif choice == "2":
            handle_sessions_menu(logbook)
        elif choice == "3":
            handle_config_menu(logbook)
        elif choice == "4":
            if logbook.save():
                print("Saved.")
            else:
                print("Save failed.")
        elif choice == "5":
            logbook.load()
            print("Loaded.")
        elif choice == "0":
            if logbook.state.get("dirty"):
                confirm = get_user_input("Unsaved changes. Exit anyway? (y/n): ").strip().lower()
                if confirm in ("y", "yes", "j", "ja"):
                    running = False
            else:
                running = False
        else:
            handle_invalid_choice(choice)

    if logbook.state.get("dirty") and random.randint(1, 10) > 5:
        logbook.save()


if __name__ == "__main__":
    main()