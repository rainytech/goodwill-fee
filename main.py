"""
Goodwill Tuition Centre - Student & Fee Management (Android / Kivy)
Version 1: Students list, Add/Edit/Delete, Record Receipt, Bank Balance.
Logic shared with the PC app via feelogic.py. Same fee_data.json shape.
"""

import os
from datetime import date

from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup

import feelogic as F

# ── House colours (RGBA, 0-1) ──
GREY   = (200/255, 200/255, 200/255, 1)   # #C8C8C8 page background
BLUE   = (0/255,   87/255, 184/255, 1)    # #0057B8 header
NAVY   = (0/255,    0/255, 139/255, 1)    # #00008B bank
RED    = (204/255,  0/255,   0/255, 1)    # #CC0000
GREEN  = (0/255,  100/255,   0/255, 1)    # #006400 paid / expected
BLACK  = (0, 0, 0, 1)
WHITE  = (1, 1, 1, 1)

STATUS_COLOR = {"PAID": GREEN, "OVERDUE": RED, "DUE": BLACK}


def data_path():
    """Android-safe writable location for fee_data.json."""
    try:
        from android.storage import app_storage_path
        base = app_storage_path()
    except Exception:
        base = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "fee_data.json")


def grey_bg(widget):
    """Paint a widget background grey (#C8C8C8)."""
    from kivy.graphics import Color, Rectangle
    with widget.canvas.before:
        Color(*GREY)
        widget._bg = Rectangle(pos=widget.pos, size=widget.size)

    def _upd(*_):
        widget._bg.pos = widget.pos
        widget._bg.size = widget.size
    widget.bind(pos=_upd, size=_upd)


class FeeRoot(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)
        grey_bg(self)
        self.file = data_path()
        self.data = F.load_data(self.file)
        self.selected = None  # index of selected student

        # ── Today line ──
        self.today_lbl = Label(
            text=f"Today: {date.today().strftime('%d/%m/%y')}",
            font_name="Times.ttf", font_size="15sp", bold=True,
            color=RED, size_hint_y=None, height=dp(28),
        )
        self.add_widget(self.today_lbl)

        # ── Header ──
        self.add_widget(Label(
            text="GOODWILL TUITION CENTRE\nFEE MANAGEMENT",
            font_name="Times.ttf", font_size="18sp", bold=True,
            color=BLUE, halign="center",
            size_hint_y=None, height=dp(60),
        ))

        # ── Summary line ──
        self.summary = Label(
            text="", font_name="Times.ttf", font_size="14sp",
            color=BLACK, size_hint_y=None, height=dp(30),
        )
        self.add_widget(self.summary)

        # ── Scrolling student list ──
        scroll = ScrollView()
        self.list_grid = GridLayout(
            cols=1, size_hint_y=None, spacing=dp(4), padding=dp(4),
        )
        self.list_grid.bind(minimum_height=self.list_grid.setter("height"))
        scroll.add_widget(self.list_grid)
        self.add_widget(scroll)

        # ── Bank balance line ──
        self.bank_lbl = Label(
            text="", font_name="Times.ttf", font_size="16sp", bold=True,
            color=NAVY, size_hint_y=None, height=dp(34),
        )
        self.add_widget(self.bank_lbl)

        # ── Action buttons (two rows) ──
        row1 = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(4))
        row1.add_widget(self._btn("Add", self.add_student))
        row1.add_widget(self._btn("Edit", self.edit_student))
        row1.add_widget(self._btn("Delete", self.delete_student))
        self.add_widget(row1)

        row2 = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(4))
        row2.add_widget(self._btn("Record Receipt", self.record_receipt))
        row2.add_widget(self._btn("Deposit", lambda *_: self.bank_op("deposit")))
        row2.add_widget(self._btn("Withdraw", lambda *_: self.bank_op("withdraw")))
        self.add_widget(row2)

        self.refresh()

    def _btn(self, text, cb):
        b = Button(text=text, font_name="Times.ttf", font_size="14sp", bold=True,
                   background_normal="", background_color=(0.7, 0.7, 0.7, 1),
                   color=BLACK)
        b.bind(on_release=cb)
        return b

    # ── render ──
    def refresh(self):
        self.list_grid.clear_widgets()
        students = self.data["students"]

        for i, s in enumerate(students):
            st = F.status_of(s)
            next_amt = s.get("next_due_amount", 0) or 0
            next_dt = s.get("next_due_date", "") or "—"
            sel = (i == self.selected)

            row = Button(
                text=(f"[b]{s['roll_no']}[/b]  {s['name']}\n"
                      f"{s['class']}  |  {st}  |  "
                      f"Due: {('Rs ' + format(next_amt, ',')) if next_amt > 0 else '—'}"
                      f"  ({next_dt})"),
                markup=True, halign="left", valign="middle",
                font_name="Times.ttf", font_size="13sp",
                background_normal="", color=BLACK,
                background_color=(0.78, 0.78, 0.78, 1) if not sel else (0.55, 0.55, 0.55, 1),
                size_hint_y=None, height=dp(56),
            )
            row.text_size = (Window.width - dp(24), None)
            row.bind(on_release=lambda _w, idx=i: self.select(idx))
            self.list_grid.add_widget(row)

        # summary: outstanding by next two 5ths
        w1 = F.next_fifth()
        w2 = F.fifth_after(w1)
        out1 = F.window_receipts(students, None, w1)
        out2 = F.window_receipts(students, w1, w2)
        self.summary.text = (f"Due by {w1.strftime('%d/%m/%y')}: Rs {out1:,.0f}    "
                             f"Due by {w2.strftime('%d/%m/%y')}: Rs {out2:,.0f}")

        bal = self.data["bank_balance"]
        exp = bal + F.expected_receipts(students, w1)
        self.bank_lbl.text = (f"Bank: Rs {bal:,.2f}   |   "
                              f"Expected by {w1.strftime('%d/%m/%y')}: Rs {exp:,.2f}")

        F.save_data(self.file, self.data)

    def select(self, idx):
        self.selected = idx
        self.refresh()

    def _need_selection(self):
        if self.selected is None or self.selected >= len(self.data["students"]):
            self.toast("Tap a student in the list first.")
            return False
        return True

    # ── popups ──
    def toast(self, msg):
        p = Popup(title="Goodwill",
                  content=Label(text=msg, font_name="Times.ttf"),
                  size_hint=(0.8, 0.4))
        p.open()

    def add_student(self, *_):
        self._student_form("Add Student", None)

    def edit_student(self, *_):
        if not self._need_selection():
            return
        self._student_form("Edit Student", self.data["students"][self.selected])

    def delete_student(self, *_):
        if not self._need_selection():
            return
        s = self.data["students"][self.selected]
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        box.add_widget(Label(text=f"Delete {s['name']}?", font_name="Times.ttf"))
        btns = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        p = Popup(title="Confirm", content=box, size_hint=(0.8, 0.4))

        def do_del(*_):
            del self.data["students"][self.selected]
            self.selected = None
            self.refresh()
            p.dismiss()

        yes = Button(text="Delete", font_name="Times.ttf"); yes.bind(on_release=do_del)
        no = Button(text="Cancel", font_name="Times.ttf"); no.bind(on_release=p.dismiss)
        btns.add_widget(yes); btns.add_widget(no)
        box.add_widget(btns)
        p.open()

    FIELDS = [
        ("Roll No", "roll_no"), ("Name", "name"), ("Class", "class"),
        ("Phone", "phone"), ("Term (ST/LT)", "term"),
        ("Join Date DD/MM/YY", "join_date"), ("End Date DD/MM/YY", "end_date"),
        ("Fee Due", "fee_due"), ("Fee Received", "fee_received"),
        ("Last Payment DD/MM/YY", "last_payment_date"),
        ("Next Due Date DD/MM/YY", "next_due_date"),
        ("Next Due Amount", "next_due_amount"),
        ("Cycle one-time/weekly/monthly", "cycle"),
        ("Cycle Fee", "cycle_fee"),
    ]

    def _student_form(self, title, existing):
        scroll = ScrollView()
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(4), padding=dp(6))
        grid.bind(minimum_height=grid.setter("height"))
        inputs = {}
        for lbl, key in self.FIELDS:
            grid.add_widget(Label(text=lbl, font_name="Times.ttf", font_size="12sp",
                                  color=BLACK, size_hint_y=None, height=dp(22)))
            ti = TextInput(text=str(existing.get(key, "")) if existing else "",
                           font_name="Times.ttf", multiline=False,
                           size_hint_y=None, height=dp(38))
            inputs[key] = ti
            grid.add_widget(ti)
        scroll.add_widget(grid)

        wrap = BoxLayout(orientation="vertical")
        wrap.add_widget(scroll)
        btns = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8), padding=dp(4))
        p = Popup(title=title, content=wrap, size_hint=(0.95, 0.9))

        def save(*_):
            try:
                rec = {k: inputs[k].get_text().strip() if hasattr(inputs[k], "get_text")
                       else inputs[k].text.strip() for k in inputs}
            except Exception:
                rec = {k: inputs[k].text.strip() for k in inputs}
            try:
                if not rec["roll_no"] or not rec["name"]:
                    raise ValueError("Roll No and Name are required.")
                rec["term"] = (rec["term"].upper() or "ST")
                if rec["term"] not in ("ST", "LT"):
                    raise ValueError("Term must be ST or LT.")
                for nkey in ("fee_due", "fee_received", "next_due_amount", "cycle_fee"):
                    rec[nkey] = float(rec[nkey] or 0)
                rec["cycle"] = (rec["cycle"] or "monthly").lower()
                if rec["cycle"] not in ("one-time", "weekly", "monthly"):
                    raise ValueError("Cycle must be one-time, weekly, or monthly.")
                for dkey in ("join_date", "end_date", "last_payment_date", "next_due_date"):
                    if rec[dkey]:
                        rec[dkey] = F.fmt_date(rec[dkey])
            except ValueError as err:
                self.toast(str(err)); return

            if existing is None:
                if any(x["roll_no"] == rec["roll_no"] for x in self.data["students"]):
                    self.toast(f"Roll No {rec['roll_no']} already exists."); return
                self.data["students"].append(rec)
            else:
                self.data["students"][self.selected] = rec
            self.refresh()
            p.dismiss()

        sbtn = Button(text="Save", font_name="Times.ttf", bold=True); sbtn.bind(on_release=save)
        cbtn = Button(text="Cancel", font_name="Times.ttf"); cbtn.bind(on_release=p.dismiss)
        btns.add_widget(sbtn); btns.add_widget(cbtn)
        wrap.add_widget(btns)
        p.open()

    def record_receipt(self, *_):
        if not self._need_selection():
            return
        s = self.data["students"][self.selected]
        pending = (s.get("fee_due", 0) or 0) - (s.get("fee_received", 0) or 0)
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(10))
        box.add_widget(Label(
            text=f"{s['name']} ({s['roll_no']})\nPending: Rs {pending:,.2f}",
            font_name="Times.ttf", color=BLACK))
        amt_in = TextInput(hint_text="Amount received", font_name="Times.ttf",
                           multiline=False, input_filter="float",
                           size_hint_y=None, height=dp(40))
        box.add_widget(amt_in)
        btns = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        p = Popup(title="Record Receipt", content=box, size_hint=(0.85, 0.5))

        def do(*_):
            try:
                amt = float(amt_in.text or 0)
                if amt <= 0:
                    raise ValueError
            except ValueError:
                self.toast("Enter a valid amount."); return
            msg = F.apply_receipt(s, amt)
            self.data["bank_balance"] += amt
            self.refresh()
            p.dismiss()
            self.toast(msg)

        ok = Button(text="Save", font_name="Times.ttf", bold=True); ok.bind(on_release=do)
        no = Button(text="Cancel", font_name="Times.ttf"); no.bind(on_release=p.dismiss)
        btns.add_widget(ok); btns.add_widget(no)
        box.add_widget(btns)
        p.open()

    def bank_op(self, kind):
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(10))
        box.add_widget(Label(text=f"{kind.title()} amount (Rs):",
                             font_name="Times.ttf", color=BLACK))
        amt_in = TextInput(font_name="Times.ttf", multiline=False,
                           input_filter="float", size_hint_y=None, height=dp(40))
        box.add_widget(amt_in)
        btns = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        p = Popup(title=f"Bank {kind.title()}", content=box, size_hint=(0.85, 0.45))

        def do(*_):
            try:
                amt = float(amt_in.text or 0)
                if amt <= 0:
                    raise ValueError
            except ValueError:
                self.toast("Enter a valid amount."); return
            if kind == "deposit":
                self.data["bank_balance"] += amt
            else:
                self.data["bank_balance"] -= amt
            self.refresh()
            p.dismiss()

        ok = Button(text="OK", font_name="Times.ttf", bold=True); ok.bind(on_release=do)
        no = Button(text="Cancel", font_name="Times.ttf"); no.bind(on_release=p.dismiss)
        btns.add_widget(ok); btns.add_widget(no)
        box.add_widget(btns)
        p.open()


class GoodwillApp(App):
    def build(self):
        self.title = "Goodwill Fee Manager"
        if Window is not None:
            Window.clearcolor = GREY
        return FeeRoot()


if __name__ == "__main__":
    GoodwillApp().run()
