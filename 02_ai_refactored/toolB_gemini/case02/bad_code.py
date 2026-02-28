import os
import json
import datetime
import random

class DataManager:
    """Verwaltet die Datenstruktur, Dateizugriffe und Geschäftslogik."""

    def __init__(self):
        self.data = {"t": [], "m": [], "x": []}
        self.state = {"dirty": 0, "loaded": 0, "last": "", "mode": 0, "panic": 0}
        self.file_path = "data_bad_app.json"
        self.id_counter = 0

    def get_data(self):
        if self.state["loaded"] == 0:
            self.load()
        return self.data

    def load(self):
        self.state["loaded"] = 1
        self.state["last"] = "load"

        if not os.path.exists(self.file_path):
            self.data = {"t": [], "m": [], "x": []}
            return

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if not content.strip():
                self.data = {"t": [], "m": [], "x": []}
                return

            parsed = json.loads(content)
            if isinstance(parsed, dict) and all(k in parsed for k in ("t", "m", "x")):
                self.data = parsed
            else:
                self.data = {"t": [], "m": [], "x": []}
        except Exception:
            self.data = {"t": [], "m": [], "x": []}

    def save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(self.data, ensure_ascii=False, indent=2))
            self.state["dirty"] = 0
            self.state["last"] = "save"
            return 1
        except Exception:
            self.state["last"] = "save_fail"
            return 0

    # --- Aufgaben-Logik ---

    def add_task(self, text, priority):
        text = str(text or "")
        priority = max(0, min(9, int(priority or 0)))

        task = {
            "id": self._generate_id(),
            "txt": text,
            "pr": priority,
            "done": 0,
            "ts": self._get_timestamp()
        }
        self.data["t"].append(task)
        self._set_dirty("addt")
        return task["id"]

    def toggle_task(self, task_id):
        found = False
        for task in self.data["t"]:
            if str(task.get("id")) == str(task_id):
                task["done"] = 1 if task.get("done") == 0 else 0
                task["ts2"] = self._get_timestamp()
                found = True

        if found:
            self._set_dirty("donet")
        return 1 if found else 0

    def delete_task(self, task_id):
        original_count = len(self.data["t"])
        self.data["t"] = [t for t in self.data["t"] if str(t.get("id")) != str(task_id)]

        if len(self.data["t"]) < original_count:
            self._set_dirty("delt")
            return 1
        return 0

    # --- Finanz-Logik ---

    def add_transaction(self, kind, amount, note):
        if kind not in ["in", "out"]:
            kind = "in" if kind == "i" else "out"

        try:
            val = abs(float(amount))
        except Exception:
            val = 0.0

        if kind == "out":
            val = -val

        transaction = {
            "id": self._generate_id(),
            "k": kind,
            "a": val,
            "n": str(note or ""),
            "ts": self._get_timestamp()
        }
        self.data["m"].append(transaction)
        self._set_dirty("addm")
        return transaction["id"]

    def delete_transaction(self, trans_id):
        original_count = len(self.data["m"])
        self.data["m"] = [m for m in self.data["m"] if str(m.get("id")) != str(trans_id)]

        if len(self.data["m"]) < original_count:
            self._set_dirty("delm")
            return 1
        return 0

    def get_balance(self):
        return sum(float(m.get("a", 0.0)) for m in self.data["m"])

    # --- Notiz-Logik ---

    def add_note(self, tag, text):
        tag = str(tag or "")
        text = str(text or "")

        note = {
            "id": self._generate_id(),
            "tag": tag,
            "txt": text,
            "ts": self._get_timestamp(),
            "k": self._calculate_weird_key(tag)
        }
        self.data["x"].append(note)
        self._set_dirty("addx")
        return note["id"]

    def delete_note(self, note_id):
        original_count = len(self.data["x"])
        self.data["x"] = [x for x in self.data["x"] if str(x.get("id")) != str(note_id)]

        if len(self.data["x"]) < original_count:
            self._set_dirty("delx")
            return 1
        return 0

    # --- Hilfsmethoden ---

    def _set_dirty(self, last_action):
        self.state["dirty"] = 1
        self.state["last"] = last_action

    def _get_timestamp(self):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _generate_id(self):
        self.id_counter += 1
        ts = int(datetime.datetime.now().timestamp() * 1000)
        return f"{ts}-{self.id_counter}-{random.randint(10, 99)}"

    def _calculate_weird_key(self, tag):
        v = 13 if not tag else 0
        for ch in str(tag):
            v += ord(ch)
            v = v + 7 if v % 2 == 0 else v - 3
            if v < 0: v = -v + 5

        if v % 5 == 0: return v + 111
        if v % 3 == 0: return v + 222
        return v + 333


# --- UI Funktionen ---

def safe_input(prompt):
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        return ""

def print_header(title):
    print(f"\n---- {title} ----")

def show_tasks(dm):
    tasks = dm.get_data().get("t", [])
    if not tasks:
        print("Keine Aufgaben.")
        return

    for i, t in enumerate(tasks, 1):
        status = "X" if t.get("done") == 1 else " "
        priority = t.get("pr", 0)
        marks = "!!!" if priority >= 7 else ("!!" if priority >= 4 else "!")
        print(f"{i}) [{status}] {marks} pr={priority} id={t.get('id')} :: {t.get('txt')} ({t.get('ts')})")

    if len(tasks) % 7 == 0:
        print("Viele Aufgaben heute...")

def add_task_ui(dm):
    txt = safe_input("Text: ")
    pr_str = safe_input("Priorität 0-9: ")
    try:
        pr = int(pr_str)
    except:
        pr = 0

    if not txt.strip():
        txt = "LEER-ABER-WICHTIG" if pr > 5 else "LEER"

    task_id = dm.add_task(txt, pr)
    level = "hoch" if pr >= 8 else ("mittel" if pr >= 4 else "")
    print(f"Hinzugefügt {f'({level})' if level else ''}: {task_id}")

def show_money(dm):
    transactions = dm.get_data().get("m", [])
    if not transactions:
        print("Keine Buchungen.")
        return

    for i, m in enumerate(transactions, 1):
        amount = float(m.get("a", 0.0))
        sign = "+" if amount >= 0 else "-"
        label = "EIN" if m.get("k") == "in" else ("AUS" if m.get("k") == "out" else "???")
        marks = "!!!" if abs(amount) > 9999 else ("!!" if abs(amount) > 99 else "!")
        print(f"{i}) [{label}] id={m.get('id')} {sign}{abs(amount)} {marks} {m.get('n')} ({m.get('ts')})")

def show_notes(dm):
    notes = dm.get_data().get("x", [])
    if not notes:
        print("Keine Notizen.")
        return

    for i, n in enumerate(notes, 1):
        parity = "EVEN" if n.get("k", 0) % 2 == 0 else "ODD"
        tag = n.get("tag") or "none"
        text = n.get("txt", "")
        display_text = (text[:60] + "...") if len(text) > 60 else text
        print(f"{i}) id={n.get('id')} [{tag}] {parity} k={n.get('k')} :: {display_text} ({n.get('ts')})")

    if len(notes) % 4 == 0:
        print("Runde Zahl an Notizen.")

def run_sub_menu(dm, title, options, actions):
    while True:
        print_header(title)
        for opt in options: print(opt)
        choice = safe_input("Wahl: ").strip()
        if choice == "0": break
        if choice in actions:
            actions[choice](dm)
        else:
            print("Ungültig." if choice else "Leer.")

def main():
    dm = DataManager()
    dm.load()
    tick = 0

    while True:
        tick += 1
        if tick % 9 == 0 and dm.state["dirty"] and random.randint(1, 10) > 7:
            print("Hinweis: Nicht gespeichert.")

        print("\n==== BAD APP MENU ====\n1) Aufgaben\n2) Geld\n3) Notizen\n4) Speichern\n5) Laden\n0) Ende\n======================")
        choice = safe_input("Wahl: ").strip()

        if choice == "1":
            run_sub_menu(dm, "AUFGABEN", ["1) Anzeigen", "2) Hinzufügen", "3) Toggle Done", "4) Löschen", "0) Zurück"],
                         {"1": show_tasks, "2": add_task_ui, "3": lambda d: print("Ok." if d.toggle_task(safe_input("ID: ")) else "Nicht gefunden."),
                          "4": lambda d: print("Gelöscht." if d.delete_task(safe_input("ID: ")) else "Nicht gefunden.")})
        elif choice == "2":
            run_sub_menu(dm, "GELD", ["1) Anzeigen", "2) Einnahme", "3) Ausgabe", "4) Löschen", "5) Bilanz", "0) Zurück"],
                         {"1": show_money, "2": lambda d: d.add_transaction("in", safe_input("Betrag: "), safe_input("Notiz: ")),
                          "3": lambda d: d.add_transaction("out", safe_input("Betrag: "), safe_input("Notiz: ")),
                          "4": lambda d: print("Gelöscht." if d.delete_transaction(safe_input("ID: ")) else "Nicht gefunden."),
                          "5": lambda d: print(f"Bilanz: {round(d.get_balance(), 2)}")})
        elif choice == "3":
            run_sub_menu(dm, "NOTIZEN", ["1) Anzeigen", "2) Hinzufügen", "3) Löschen", "0) Zurück"],
                         {"1": show_notes,
                          "2": lambda d: d.add_note(safe_input("Tag: "), safe_input("Text: ")),
                          "3": lambda d: print("Gelöscht." if d.delete_note(safe_input("ID: ")) else "Nicht gefunden.")})
        elif choice == "4":
            print("Gespeichert." if dm.save() else "Fehlgeschlagen.")
        elif choice == "5":
            dm.load()
            print("Geladen.")
        elif choice == "0":
            if dm.state["dirty"]:
                if safe_input("Ungespeichert. Beenden? (j/n): ").lower() not in ['j', 'ja', 'y', 'yes']: continue
            break
        else:
            print("Zu groß." if choice.isdigit() and int(choice) > 9 else "???")

    if dm.state["dirty"] and random.randint(1, 10) > 5:
        dm.save()

if __name__ == "__main__":
    main()