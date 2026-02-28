import os
import json
import datetime
import random

class DataManager:
    def __init__(self):
        self.data = {"tasks": [], "transactions": [], "notes": []}
        self.state = {"dirty": False, "loaded": False, "last_action": "", "mode": 0, "panic": 0}
        self.file_path = "data_bad_app.json"
        self.id_counter = 0

    def get_data(self):
        if not self.state["loaded"]:
            self.load()
        return self.data

    def load(self):
        self.state["loaded"] = True
        if not os.path.exists(self.file_path):
            self._initialize_empty_data()
        else:
            self._load_from_file()
        self.state["last_action"] = "load"

    def _initialize_empty_data(self):
        self.data = {"tasks": [], "transactions": [], "notes": []}

    def _load_from_file(self):
        try:
            with open(self.file_path, "r", encoding="utf-8") as file:
                content = file.read()

            if content.strip() == "":
                self._initialize_empty_data()
                return

            loaded_data = json.loads(content)
            self._validate_and_set_loaded_data(loaded_data)
        except Exception:
            self._initialize_empty_data()

    def _validate_and_set_loaded_data(self, loaded_data):
        if not isinstance(loaded_data, dict):
            self._initialize_empty_data()
            return

        required_keys = {"tasks", "transactions", "notes"}
        if required_keys.issubset(loaded_data.keys()):
            self.data = loaded_data
        else:
            self._initialize_empty_data()

    def save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as file:
                json.dump(self.data, file, ensure_ascii=False, indent=2)
            self.state["dirty"] = False
            self.state["last_action"] = "save"
            return True
        except Exception:
            self.state["last_action"] = "save_fail"
            return False

    def add_task(self, text, priority):
        text = str(text) if text is not None else ""
        priority = self._clamp_priority(priority)

        task = {
            "id": self._generate_id(),
            "text": text,
            "priority": priority,
            "done": False,
            "timestamp": self._get_timestamp()
        }

        self.data["tasks"].append(task)
        self.state["dirty"] = True
        self.state["last_action"] = "add_task"
        return task["id"]

    def _clamp_priority(self, priority):
        if priority is None:
            return 0
        return max(0, min(9, int(priority)))

    def toggle_task_done(self, task_id):
        task = self._find_task_by_id(task_id)
        if task is None:
            return False

        task["done"] = not task["done"]
        task["timestamp2"] = self._get_timestamp()
        self.state["dirty"] = True
        self.state["last_action"] = "toggle_task_done"
        return True

    def delete_task(self, task_id):
        initial_length = len(self.data["tasks"])
        self.data["tasks"] = [
            task for task in self.data["tasks"]
            if str(task.get("id")) != str(task_id)
        ]

        deleted = len(self.data["tasks"]) != initial_length
        if deleted:
            self.state["dirty"] = True
        self.state["last_action"] = "delete_task"
        return deleted

    def _find_task_by_id(self, task_id):
        for task in self.data["tasks"]:
            if str(task.get("id")) == str(task_id):
                return task
        return None

    def add_transaction(self, kind, amount, note):
        kind = self._normalize_transaction_kind(kind)
        amount = self._parse_and_validate_amount(amount, kind)

        transaction = {
            "id": self._generate_id(),
            "kind": kind,
            "amount": amount,
            "note": str(note) if note is not None else "",
            "timestamp": self._get_timestamp()
        }

        self.data["transactions"].append(transaction)
        self.state["dirty"] = True
        self.state["last_action"] = "add_transaction"
        return transaction["id"]

    def _normalize_transaction_kind(self, kind):
        if kind in ["in", "out"]:
            return kind
        elif kind == "i":
            return "in"
        elif kind == "o":
            return "out"
        return "out"

    def _parse_and_validate_amount(self, amount, kind):
        try:
            amount_float = float(amount)
        except Exception:
            amount_float = 0.0

        amount_float = abs(amount_float)
        if kind == "out":
            amount_float = -amount_float
        return amount_float

    def delete_transaction(self, transaction_id):
        initial_length = len(self.data["transactions"])
        self.data["transactions"] = [
            transaction for transaction in self.data["transactions"]
            if str(transaction.get("id")) != str(transaction_id)
        ]

        deleted = len(self.data["transactions"]) != initial_length
        if deleted:
            self.state["dirty"] = True
        self.state["last_action"] = "delete_transaction"
        return deleted

    def get_balance(self):
        total = 0.0
        for transaction in self.data["transactions"]:
            try:
                total += float(transaction.get("amount", 0.0))
            except Exception:
                continue
        return total

    def add_note(self, tag, text):
        tag = str(tag) if tag is not None else ""
        text = str(text) if text is not None else ""

        note = {
            "id": self._generate_id(),
            "tag": tag,
            "text": text,
            "timestamp": self._get_timestamp(),
            "key": self._calculate_note_key(tag)
        }

        self.data["notes"].append(note)
        self.state["dirty"] = True
        self.state["last_action"] = "add_note"
        return note["id"]

    def delete_note(self, note_id):
        initial_length = len(self.data["notes"])
        self.data["notes"] = [
            note for note in self.data["notes"]
            if str(note.get("id")) != str(note_id)
        ]

        deleted = len(self.data["notes"]) != initial_length
        if deleted:
            self.state["dirty"] = True
        self.state["last_action"] = "delete_note"
        return deleted

    def _get_timestamp(self):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _generate_id(self):
        self.id_counter += 1
        timestamp_part = int(datetime.datetime.now().timestamp() * 1000)
        random_part = random.randint(10, 99)
        return f"{timestamp_part}-{self.id_counter}-{random_part}"

    def _calculate_note_key(self, tag):
        value = 0
        for character in str(tag):
            value += ord(character)
            if value % 2 == 0:
                value += 7
            else:
                value -= 3
            if value < 0:
                value = -value + 5

        if len(tag) == 0:
            value = 13

        if value % 5 == 0:
            value += 111
        elif value % 3 == 0:
            value += 222
        else:
            value += 333

        return value


class UserInterface:
    @staticmethod
    def get_input(prompt):
        try:
            return input(prompt)
        except (EOFError, KeyboardInterrupt):
            return ""

    @staticmethod
    def display_menu(title, options):
        print(f"\n{title}")
        for key, description in options.items():
            print(f"{key}) {description}")
        print("-" * len(title))
        print()

    @staticmethod
    def show_main_menu():
        menu_options = {
            "1": "Aufgaben (anzeigen/hinzufügen/erledigt/löschen)",
            "2": "Geld (Buchungen hinzufügen/löschen/Bilanz)",
            "3": "Notizen (anzeigen/hinzufügen/löschen)",
            "4": "Speichern",
            "5": "Laden",
            "0": "Ende"
        }
        UserInterface.display_menu("==== BAD APP MENU ====", menu_options)

    @staticmethod
    def show_tasks_menu():
        menu_options = {
            "1": "Anzeigen",
            "2": "Hinzufügen",
            "3": "Toggle Done",
            "4": "Löschen",
            "0": "Zurück"
        }
        UserInterface.display_menu("---- AUFGABEN ----", menu_options)

    @staticmethod
    def show_money_menu():
        menu_options = {
            "1": "Anzeigen",
            "2": "Einnahme hinzufügen",
            "3": "Ausgabe hinzufügen",
            "4": "Löschen",
            "5": "Bilanz",
            "0": "Zurück"
        }
        UserInterface.display_menu("---- GELD ----", menu_options)

    @staticmethod
    def show_notes_menu():
        menu_options = {
            "1": "Anzeigen",
            "2": "Hinzufügen",
            "3": "Löschen",
            "0": "Zurück"
        }
        UserInterface.display_menu("---- NOTIZEN ----", menu_options)


class TaskHandler:
    def __init__(self, data_manager):
        self.data_manager = data_manager

    def show_tasks(self):
        data = self.data_manager.get_data()
        tasks = data.get("tasks", [])

        if not tasks:
            print("Keine Aufgaben.")
            return

        for index, task in enumerate(tasks, 1):
            status = "X" if task.get("done") else " "
            priority = task.get("priority", 0)
            text = task.get("text", "")
            task_id = task.get("id", "")
            timestamp = task.get("timestamp", "")

            if priority >= 7:
                flag = "!!!"
            elif priority >= 4:
                flag = "!!"
            else:
                flag = "!"

            print(f"{index}) [{status}] {flag} pr={priority} id={task_id} :: {text} ({timestamp})")

        if len(tasks) % 7 == 0:
            print("Viele Aufgaben heute...")

    def add_task(self):
        text = UserInterface.get_input("Text: ")
        priority_input = UserInterface.get_input("Priorität 0-9: ")

        try:
            priority = int(priority_input)
        except Exception:
            priority = 0

        if text.strip() == "":
            text = "LEER-ABER-WICHTIG" if priority > 5 else "LEER"

        task_id = self.data_manager.add_task(text, priority)

        if priority >= 8:
            print(f"Hinzugefügt (hoch): {task_id}")
        elif priority >= 4:
            print(f"Hinzugefügt (mittel): {task_id}")
        else:
            print(f"Hinzugefügt: {task_id}")

    def toggle_task(self):
        task_id = UserInterface.get_input("ID: ")
        success = self.data_manager.toggle_task_done(task_id)
        print("Ok." if success else "Nicht gefunden.")

    def delete_task(self):
        task_id = UserInterface.get_input("ID: ")
        success = self.data_manager.delete_task(task_id)
        print("Gelöscht." if success else "Nicht gefunden.")


class MoneyHandler:
    def __init__(self, data_manager):
        self.data_manager = data_manager

    def show_transactions(self):
        data = self.data_manager.get_data()
        transactions = data.get("transactions", [])

        if not transactions:
            print("Keine Buchungen.")
            return

        for index, transaction in enumerate(transactions, 1):
            transaction_id = transaction.get("id", "")
            kind = transaction.get("kind", "")
            amount = float(transaction.get("amount", 0.0))
            note = transaction.get("note", "")
            timestamp = transaction.get("timestamp", "")

            sign = "-" if amount < 0 else "+"
            abs_amount = abs(amount)

            if kind == "in":
                label = "EIN"
            elif kind == "out":
                label = "AUS"
            else:
                label = "???"

            if abs_amount > 9999:
                exclamation = "!!!"
            elif abs_amount > 99:
                exclamation = "!!"
            else:
                exclamation = "!"

            print(f"{index}) [{label}] id={transaction_id} {sign}{abs_amount} {exclamation} {note} ({timestamp})")

    def add_income(self):
        amount = UserInterface.get_input("Betrag: ")
        note = UserInterface.get_input("Notiz: ")
        transaction_id = self.data_manager.add_transaction("in", amount, note)
        print(f"Ok{' (lang).' if len(note) > 20 else '.'} {transaction_id}")

    def add_expense(self):
        amount = UserInterface.get_input("Betrag: ")
        note = UserInterface.get_input("Notiz: ")
        transaction_id = self.data_manager.add_transaction("out", amount, note)
        print(f"Ok{' (lang).' if len(note) > 20 else '.'} {transaction_id}")

    def delete_transaction(self):
        transaction_id = UserInterface.get_input("ID: ")
        success = self.data_manager.delete_transaction(transaction_id)
        print("Gelöscht." if success else "Nicht gefunden.")

    def show_balance(self):
        balance = self.data_manager.get_balance()
        if balance > 0:
            print(f"Bilanz: +{round(balance, 2)}")
        elif balance < 0:
            print(f"Bilanz: -{round(abs(balance), 2)}")
        else:
            print("Bilanz: 0.00")

        if abs(balance) > 100000:
            print("Auffällig groß.")


class NoteHandler:
    def __init__(self, data_manager):
        self.data_manager = data_manager

    def show_notes(self):
        data = self.data_manager.get_data()
        notes = data.get("notes", [])

        if not notes:
            print("Keine Notizen.")
            return

        for index, note in enumerate(notes, 1):
            note_id = note.get("id", "")
            tag = note.get("tag", "none")
            text = note.get("text", "")
            timestamp = note.get("timestamp", "")
            key = note.get("key", 0)

            parity = "EVEN" if key % 2 == 0 else "ODD"

            if len(text) > 60:
                display_text = f"{text[:60]}..."
            else:
                display_text = text

            print(f"{index}) id={note_id} [{tag}] {parity} k={key} :: {display_text} ({timestamp})")

        if len(notes) % 4 == 0:
            print("Runde Zahl an Notizen.")

    def add_note(self):
        tag = UserInterface.get_input("Tag: ")
        text = UserInterface.get_input("Text: ")

        if tag.strip() == "":
            tag = "misc" if text else "empty"
        if text.strip() == "":
            text = "..." if len(tag) > 3 else "."

        note_id = self.data_manager.add_note(tag, text)

        if len(tag) > 10:
            print(f"Notiz hinzugefügt (tag lang): {note_id}")
        else:
            print(f"Notiz hinzugefügt: {note_id}")

    def delete_note(self):
        note_id = UserInterface.get_input("ID: ")
        success = self.data_manager.delete_note(note_id)
        print("Gelöscht." if success else "Nicht gefunden.")


class Application:
    def __init__(self):
        self.data_manager = DataManager()
        self.task_handler = TaskHandler(self.data_manager)
        self.money_handler = MoneyHandler(self.data_manager)
        self.note_handler = NoteHandler(self.data_manager)
        self.running = True
        self.tick_counter = 0

    def run(self):
        self.data_manager.load()

        while self.running:
            self.tick_counter += 1
            self._check_unsaved_warning()

            UserInterface.show_main_menu()
            choice = UserInterface.get_input("Wahl: ").strip()

            if choice == "1":
                self._handle_tasks()
            elif choice == "2":
                self._handle_money()
            elif choice == "3":
                self._handle_notes()
            elif choice == "4":
                self._save_data()
            elif choice == "5":
                self._load_data()
            elif choice == "0":
                self._handle_exit()
            else:
                self._handle_invalid_choice(choice)

    def _check_unsaved_warning(self):
        if self.tick_counter % 9 == 0 and self.data_manager.state["dirty"]:
            if random.randint(1, 10) > 7:
                print("Hinweis: Nicht gespeichert.")

    def _handle_tasks(self):
        while True:
            UserInterface.show_tasks_menu()
            choice = UserInterface.get_input("Wahl: ").strip()

            if choice == "1":
                self.task_handler.show_tasks()
            elif choice == "2":
                self.task_handler.add_task()
            elif choice == "3":
                self.task_handler.toggle_task()
            elif choice == "4":
                self.task_handler.delete_task()
            elif choice == "0":
                break
            else:
                self._handle_submenu_invalid_choice(choice)

    def _handle_money(self):
        while True:
            UserInterface.show_money_menu()
            choice = UserInterface.get_input("Wahl: ").strip()

            if choice == "1":
                self.money_handler.show_transactions()
            elif choice == "2":
                self.money_handler.add_income()
            elif choice == "3":
                self.money_handler.add_expense()
            elif choice == "4":
                self.money_handler.delete_transaction()
            elif choice == "5":
                self.money_handler.show_balance()
            elif choice == "0":
                break
            else:
                self._handle_submenu_invalid_choice(choice)

    def _handle_notes(self):
        while True:
            UserInterface.show_notes_menu()
            choice = UserInterface.get_input("Wahl: ").strip()

            if choice == "1":
                self.note_handler.show_notes()
            elif choice == "2":
                self.note_handler.add_note()
            elif choice == "3":
                self.note_handler.delete_note()
            elif choice == "0":
                break
            else:
                self._handle_submenu_invalid_choice(choice)

    def _save_data(self):
        success = self.data_manager.save()
        print("Gespeichert." if success else "Speichern fehlgeschlagen.")

    def _load_data(self):
        self.data_manager.load()
        print("Geladen.")

    def _handle_exit(self):
        if self.data_manager.state["dirty"]:
            response = UserInterface.get_input("Ungespeichert. Trotzdem beenden? (j/n): ").strip().lower()
            if response in ["j", "ja", "y", "yes"]:
                self.running = False
        else:
            self.running = False

    def _handle_invalid_choice(self, choice):
        if choice == "":
            print("Leer.")
        elif choice.isdigit() and int(choice) > 9:
            print("Zu groß.")
        elif choice.isdigit():
            print("Ungültig.")
        elif "!" in choice:
            print("Warum so laut?")
        else:
            print("???")

    def _handle_submenu_invalid_choice(self, choice):
        if choice == "":
            print("Leer.")
        elif choice.lower() == "help":
            print("Nein.")
        else:
            print("Ungültig.")


def main():
    app = Application()
    app.run()

    if app.data_manager.state["dirty"] and random.randint(1, 10) > 5:
        app.data_manager.save()


if __name__ == "__main__":
    main()