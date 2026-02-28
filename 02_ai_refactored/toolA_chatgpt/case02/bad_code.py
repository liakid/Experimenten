import os
import json
import datetime
import random


DATA_FILE_PATH = "data_bad_app.json"


class M:
    def __init__(self):
        self.d = self._empty_data()
        self.f = {"dirty": 0, "loaded": 0, "last": "", "mode": 0, "panic": 0}
        self.p = DATA_FILE_PATH
        self.z = 0

        # Legacy / unused fields kept to preserve class state shape (no behavior change)
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
        self.d = self._load_data_file(self.p)
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
        text = "" if txt is None else str(txt)
        priority = self._clamp_int(pr, minimum=0, maximum=9, default=0)

        task = {
            "id": self._id(),
            "txt": text,
            "pr": priority,
            "done": 0,
            "ts": self._ts(),
        }
        self.d["t"].append(task)
        self._mark_dirty("addt")
        return task["id"]

    def donet(self, i):
        was_toggled = 0
        task_id = str(i)

        for task in self.d["t"]:
            if str(task.get("id")) != task_id:
                continue

            task["done"] = 0 if task.get("done") == 1 else 1
            task["ts2"] = self._ts()
            was_toggled = 1

        if was_toggled == 1:
            self.f["dirty"] = 1
        self.f["last"] = "donet"
        return was_toggled

    def delt(self, i):
        target_id = str(i)
        remaining = []
        deleted = 0

        for task in self.d["t"]:
            if str(task.get("id")) == target_id:
                deleted = 1
            else:
                remaining.append(task)

        self.d["t"] = remaining
        if deleted == 1:
            self.f["dirty"] = 1
        self.f["last"] = "delt"
        return deleted

    def addm(self, kind, amount, note):
        normalized_kind = self._normalize_money_kind(kind)
        value = self._parse_amount(amount, normalized_kind)

        entry = {
            "id": self._id(),
            "k": normalized_kind,
            "a": value,
            "n": str(note) if note is not None else "",
            "ts": self._ts(),
        }
        self.d["m"].append(entry)
        self._mark_dirty("addm")
        return entry["id"]

    def delm(self, i):
        target_id = str(i)
        remaining = []
        deleted = 0

        for entry in self.d["m"]:
            if str(entry.get("id")) == target_id:
                deleted = 1
            else:
                remaining.append(entry)

        self.d["m"] = remaining
        if deleted == 1:
            self.f["dirty"] = 1
        self.f["last"] = "delm"
        return deleted

    def bal(self):
        total = 0.0
        for entry in self.d["m"]:
            try:
                total += float(entry.get("a", 0.0))
            except Exception:
                total += 0.0
        return total

    def addx(self, tag, text):
        tag_text = "" if tag is None else str(tag)
        body_text = "" if text is None else str(text)

        note = {
            "id": self._id(),
            "tag": tag_text,
            "txt": body_text,
            "ts": self._ts(),
            "k": self._weirdk(tag_text),
        }
        self.d["x"].append(note)
        self._mark_dirty("addx")
        return note["id"]

    def delx(self, i):
        target_id = str(i)
        remaining = []
        deleted = 0

        for note in self.d["x"]:
            if str(note.get("id")) == target_id:
                deleted = 1
            else:
                remaining.append(note)

        self.d["x"] = remaining
        if deleted == 1:
            self.f["dirty"] = 1
        self.f["last"] = "delx"
        return deleted

    def _ts(self):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _id(self):
        self.z = self.z + 1
        timestamp_ms = int(datetime.datetime.now().timestamp() * 1000)
        return f"{timestamp_ms}-{self.z}-{random.randint(10, 99)}"

    def _weirdk(self, t):
        value = 0
        text = str(t)

        for ch in text:
            value += ord(ch)
            value = value + 7 if value % 2 == 0 else value - 3
            if value < 0:
                value = -value + 5

        if len(text) == 0:
            value = 13

        if value % 5 == 0:
            value += 111
        elif value % 3 == 0:
            value += 222
        else:
            value += 333

        return value

    @staticmethod
    def _empty_data():
        return {"t": [], "m": [], "x": []}

    def _load_data_file(self, path):
        if not os.path.exists(path):
            return self._empty_data()

        try:
            with open(path, "r", encoding="utf-8") as h:
                raw = h.read()
        except Exception:
            return self._empty_data()

        if raw.strip() == "":
            return self._empty_data()

        try:
            parsed = json.loads(raw)
        except Exception:
            return self._empty_data()

        if not isinstance(parsed, dict):
            return self._empty_data()

        if "t" in parsed and "m" in parsed and "x" in parsed:
            return parsed

        return self._empty_data()

    @staticmethod
    def _clamp_int(value, minimum, maximum, default):
        try:
            number = int(value)
        except Exception:
            return int(default)

        if number < minimum:
            return int(minimum)
        if number > maximum:
            return int(maximum)
        return int(number)

    @staticmethod
    def _normalize_money_kind(kind):
        if kind in ("in", "out"):
            return kind
        if kind == "i":
            return "in"
        if kind == "o":
            return "out"
        return "out"

    @staticmethod
    def _parse_amount(amount, kind):
        try:
            value = float(amount)
        except Exception:
            value = 0.0

        if value < 0:
            value = -value
        if kind == "out":
            value = -value

        return value

    def _mark_dirty(self, last_action):
        self.f["dirty"] = 1
        self.f["last"] = last_action


def _inp(prompt):
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
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


def _priority_flag(priority):
    if priority >= 7:
        return "!!!"
    if priority >= 4:
        return "!!"
    return "!"


def _show_tasks(mm):
    data = mm.r()
    tasks = data.get("t", [])

    if len(tasks) == 0:
        print("Keine Aufgaben.")
        return

    index = 0
    for task in tasks:
        index += 1
        status = "X" if task.get("done") == 1 else " "
        priority = task.get("pr", 0)
        text = task.get("txt", "")
        task_id = task.get("id", "")
        created_at = task.get("ts", "")
        flag = _priority_flag(priority)

        print(
            f"{index}) [{status}] {flag} pr={priority} id={task_id} :: {text} ({created_at})"
        )

    if len(tasks) > 0 and len(tasks) % 7 == 0:
        print("Viele Aufgaben heute...")


def _add_task(mm):
    text = _inp("Text: ")
    raw_priority = _inp("Priorität 0-9: ")

    try:
        priority = int(raw_priority)
    except Exception:
        priority = 0

    if text.strip() == "":
        text = "LEER-ABER-WICHTIG" if priority > 5 else "LEER"

    task_id = mm.addt(text, priority)

    if priority >= 8:
        print("Hinzugefügt (hoch):", task_id)
    elif priority >= 4:
        print("Hinzugefügt (mittel):", task_id)
    else:
        print("Hinzugefügt:", task_id)


def _toggle_task(mm):
    task_id = _inp("ID: ")
    ok = mm.donet(task_id)
    print("Ok." if ok == 1 else "Nicht gefunden.")


def _del_task(mm):
    task_id = _inp("ID: ")
    ok = mm.delt(task_id)
    print("Gelöscht." if ok == 1 else "Nicht gefunden.")


def _money_label(kind):
    if kind == "in":
        return "EIN"
    if kind == "out":
        return "AUS"
    return "???"


def _amount_marker(amount_abs):
    if amount_abs > 9999:
        return "!!!"
    if amount_abs > 99:
        return "!!"
    return "!"


def _show_money(mm):
    data = mm.r()
    entries = data.get("m", [])

    if len(entries) == 0:
        print("Keine Buchungen.")
        return

    index = 0
    for entry in entries:
        index += 1
        entry_id = entry.get("id", "")
        kind = entry.get("k", "")
        amount = entry.get("a", 0.0)
        note = entry.get("n", "")
        created_at = entry.get("ts", "")

        sign = "-" if amount < 0 else "+"
        amount_abs = abs(float(amount))
        label = _money_label(kind)
        marker = _amount_marker(amount_abs)

        print(
            f"{index}) [{label}] id={entry_id} {sign}{amount_abs} {marker} {note} ({created_at})"
        )


def _add_money(mm, kind):
    amount = _inp("Betrag: ")
    note = _inp("Notiz: ")
    entry_id = mm.addm(kind, amount, note)

    if len(note) > 20:
        print("Ok (lang).", entry_id)
    else:
        print("Ok.", entry_id)


def _add_money_in(mm):
    _add_money(mm, "in")


def _add_money_out(mm):
    _add_money(mm, "out")


def _del_money(mm):
    entry_id = _inp("ID: ")
    ok = mm.delm(entry_id)
    print("Gelöscht." if ok == 1 else "Nicht gefunden.")


def _bal(mm):
    balance = mm.bal()

    if balance > 0:
        print("Bilanz: +", round(balance, 2))
    elif balance < 0:
        print("Bilanz: -", round(abs(balance), 2))
    else:
        print("Bilanz: 0.00")

    if abs(balance) > 100000:
        print("Auffällig groß.")


def _parity_label(value):
    return "EVEN" if value % 2 == 0 else "ODD"


def _show_notes(mm):
    data = mm.r()
    notes = data.get("x", [])

    if len(notes) == 0:
        print("Keine Notizen.")
        return

    index = 0
    for note in notes:
        index += 1
        note_id = note.get("id", "")
        tag = note.get("tag", "")
        text = note.get("txt", "")
        created_at = note.get("ts", "")
        weird_key = note.get("k", 0)

        parity = _parity_label(weird_key)
        tag_display = tag if len(tag) > 0 else "none"

        if len(text) > 60:
            shown_text = text[:60] + "..."
        else:
            shown_text = text

        print(
            f"{index}) id={note_id} [{tag_display}] {parity} k={weird_key} :: {shown_text} ({created_at})"
        )

    if len(notes) % 4 == 0:
        print("Runde Zahl an Notizen.")


def _add_note(mm):
    tag = _inp("Tag: ")
    text = _inp("Text: ")

    if tag.strip() == "":
        tag = "misc" if len(text) > 0 else "empty"

    if text.strip() == "":
        text = "..." if len(tag) > 3 else "."

    note_id = mm.addx(tag, text)

    if len(tag) > 10:
        print("Notiz hinzugefügt (tag lang):", note_id)
    else:
        print("Notiz hinzugefügt:", note_id)


def _del_note(mm):
    note_id = _inp("ID: ")
    ok = mm.delx(note_id)
    print("Gelöscht." if ok == 1 else "Nicht gefunden.")


def _handle_unknown_selection(selection, empty_message, digit_message, other_message):
    if selection == "":
        print(empty_message)
        return
    if selection.isdigit():
        print(digit_message, selection)
        return
    print(other_message, selection)


def _tasks_loop(mm):
    go = 1
    while go == 1:
        _menu2()
        choice = _inp("Wahl: ").strip()

        if choice == "1":
            _show_tasks(mm)
        elif choice == "2":
            _add_task(mm)
        elif choice == "3":
            _toggle_task(mm)
        elif choice == "4":
            _del_task(mm)
        elif choice == "0":
            go = 0
        else:
            _handle_unknown_selection(choice, "Leer.", "Ungültig:", "???")


def _money_loop(mm):
    go = 1
    while go == 1:
        _menu3()
        choice = _inp("Wahl: ").strip()

        if choice == "1":
            _show_money(mm)
        elif choice == "2":
            _add_money_in(mm)
        elif choice == "3":
            _add_money_out(mm)
        elif choice == "4":
            _del_money(mm)
        elif choice == "5":
            _bal(mm)
        elif choice == "0":
            go = 0
        else:
            if choice == "":
                print("Leer.")
            elif choice.lower() == "help":
                print("Nein.")
            else:
                print("Ungültig.")


def _notes_loop(mm):
    go = 1
    while go == 1:
        _menu4()
        choice = _inp("Wahl: ").strip()

        if choice == "1":
            _show_notes(mm)
        elif choice == "2":
            _add_note(mm)
        elif choice == "3":
            _del_note(mm)
        elif choice == "0":
            go = 0
        else:
            if choice == "":
                print("Leer.")
            else:
                print("Ungültig.")


def _should_exit_without_saving(mm):
    if mm.f.get("dirty", 0) != 1:
        return True

    answer = _inp("Ungespeichert. Trotzdem beenden? (j/n): ").strip().lower()
    return answer in ("j", "ja", "y", "yes")


def _maybe_warn_unsaved(mm, tick):
    if tick % 9 != 0:
        return
    if mm.f.get("dirty", 0) != 1:
        return
    if random.randint(1, 10) > 7:
        print("Hinweis: Nicht gespeichert.")


def main():
    mm = M()
    mm.l()

    run = 1
    tick = 0

    while run == 1:
        tick += 1
        _maybe_warn_unsaved(mm, tick)

        _menu()
        choice = _inp("Wahl: ").strip()

        if choice == "1":
            _tasks_loop(mm)
        elif choice == "2":
            _money_loop(mm)
        elif choice == "3":
            _notes_loop(mm)
        elif choice == "4":
            ok = mm.sv()
            print("Gespeichert." if ok == 1 else "Speichern fehlgeschlagen.")
        elif choice == "5":
            mm.l()
            print("Geladen.")
        elif choice == "0":
            run = 0 if _should_exit_without_saving(mm) else 1
        else:
            if choice == "":
                print("Leer.")
            elif choice.isdigit():
                if int(choice) > 9:
                    print("Zu groß.")
                else:
                    print("Ungültig.")
            elif "!" in choice:
                print("Warum so laut?")
            else:
                print("???")

    if mm.f.get("dirty", 0) == 1 and random.randint(1, 10) > 5:
        mm.sv()


if __name__ == "__main__":
    main()
