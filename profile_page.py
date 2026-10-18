"""Customer Profile screen.

Personal information (photo, first/last name, phone; email is read-only) plus a
Danger zone (log out of all other sessions, delete account).
"""
import tkinter as tk
from tkinter import filedialog, messagebox

from main import (C, FlatButton, FormField, bump_session_version, delete_customer,
                  font, get_customer, load_avatar, pillow_installed, remove_avatar,
                  save_avatar, update_customer, validate_name, validate_phone,
                  validate_required_password, verify_customer)
from dashboard import EDGE, Avatar, CustomerPage


# ════════════════════════════ HELPERS ════════════════════════════
def validate_first(v):
    return "First name is required." if not v.strip() else validate_name(v)


def validate_last(v):
    return validate_name(v) if v.strip() else None       # optional


class ReadOnlyField(tk.Frame):
    """Greyed-out field used for the email (it is the account's login)."""

    def __init__(self, parent, label, hint):
        super().__init__(parent, bg=C["card"])
        tk.Label(self, text=label, font=font(9, "bold"), fg=C["ink"], bg=C["card"],
                 anchor="w").pack(fill="x")
        box = tk.Frame(self, bg=C["field"], highlightthickness=1,
                       highlightbackground=C["border"])
        box.pack(fill="x", pady=(5, 0))
        self.value = tk.Label(box, text=" ", font=font(10), fg=C["muted"],
                              bg=C["field"], anchor="w")
        self.value.pack(fill="x", padx=12, pady=10)
        tk.Label(self, text=hint, font=font(9), fg=C["muted"], bg=C["card"],
                 anchor="w").pack(fill="x", pady=(2, 0))

    def set(self, text):
        self.value.config(text=text or " ")


def confirm_dialog(parent, title, message, confirm_text, password_for=None):
    """Modal confirmation. When `password_for` (an email) is given the person
    must also re-enter their password. Returns True only if confirmed."""
    root = parent.winfo_toplevel()
    dlg = tk.Toplevel(root)
    dlg.title(title)
    dlg.configure(bg=C["card"])
    dlg.resizable(False, False)
    dlg.transient(root)
    result = {"ok": False}

    body = tk.Frame(dlg, bg=C["card"])
    body.pack(padx=28, pady=(24, 22))
    tk.Label(body, text=title, font=font(14, "bold"), fg=C["ink"], bg=C["card"],
             anchor="w").pack(fill="x")
    tk.Label(body, text=message, font=font(10), fg=C["muted"], bg=C["card"],
             anchor="w", justify="left", wraplength=340).pack(fill="x", pady=(6, 14))

    field = None

    def confirm():
        if field is not None:
            if not field.validate():
                return
            if verify_customer(password_for, field.get()) is None:
                field.set_error("Incorrect password.")
                return
        result["ok"] = True
        dlg.destroy()

    if password_for:
        field = FormField(body, "Confirm your password", "Enter your password",
                          secret=True, validator=validate_required_password,
                          on_enter=confirm)
        field.pack(fill="x")

    row = tk.Frame(body, bg=C["card"])
    row.pack(fill="x", pady=(6, 0))
    FlatButton(row, confirm_text, confirm, width=170, height=40, size=9).pack(side="right")
    FlatButton(row, "Cancel", dlg.destroy, kind="outline", width=90, height=40,
               size=9).pack(side="right", padx=(0, 10))

    dlg.bind("<Escape>", lambda e: dlg.destroy())
    dlg.update_idletasks()
    x = root.winfo_rootx() + (root.winfo_width() - dlg.winfo_reqwidth()) // 2
    y = root.winfo_rooty() + (root.winfo_height() - dlg.winfo_reqheight()) // 2
    dlg.geometry(f"+{max(0, x)}+{max(0, y)}")
    dlg.grab_set()
    if field is not None:
        field.focus()
    dlg.wait_window()
    return result["ok"]


# ════════════════════════════ PAGE ════════════════════════════
class ProfilePage(CustomerPage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller, active="profile")
        self.set_header("Profile", "Manage your account details and preferences.")
        self._loaded = ("", "", "")

        # ── Personal information card
        card = tk.Frame(self.content, bg=C["card"], highlightthickness=1,
                        highlightbackground=EDGE, highlightcolor=EDGE)
        card.pack(fill="x")
        inner = tk.Frame(card, bg=C["card"])
        inner.pack(fill="x", padx=24, pady=(18, 18))
        tk.Label(inner, text="Personal information", font=font(12, "bold"),
                 fg=C["ink"], bg=C["card"], anchor="w").pack(fill="x")

        row = tk.Frame(inner, bg=C["card"])
        row.pack(fill="x", pady=(12, 10))
        self.photo_avatar = Avatar(row, size=64, bg=C["card"])
        self.photo_avatar.pack(side="left")
        self.btn_change = FlatButton(row, "Change photo", self._change_photo,
                                     kind="soft", size=9, width=120, height=34)
        self.btn_change.pack(side="left", padx=(16, 8))
        self.btn_remove = FlatButton(row, "Remove", self._remove_photo,
                                     kind="outline", size=9, width=90, height=34)
        self.btn_remove.pack(side="left")

        grid = tk.Frame(inner, bg=C["card"])
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=1, uniform="f")
        grid.columnconfigure(1, minsize=16)
        grid.columnconfigure(2, weight=1, uniform="f")
        self.first = FormField(grid, "First name", "Enter your first name",
                               validator=validate_first, on_enter=self.save)
        self.last = FormField(grid, "Last name", "Enter your last name (optional)",
                              validator=validate_last, on_enter=self.save)
        self.email = ReadOnlyField(grid, "Email", "Your email is your login and can't be changed.")
        self.phone = FormField(grid, "Phone number", "+975 17 123 456",
                               validator=validate_phone, on_enter=self.save)
        self.first.grid(row=0, column=0, sticky="ew")
        self.last.grid(row=0, column=2, sticky="ew")
        self.email.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.phone.grid(row=1, column=2, sticky="new", pady=(4, 0))
        for f in (self.first, self.last, self.phone):
            f.entry.bind("<KeyRelease>", lambda e: self._dirty_check(), add="+")

        foot = tk.Frame(inner, bg=C["card"])
        foot.pack(fill="x", pady=(8, 0))
        self.btn_save = FlatButton(foot, "Save changes", self.save, width=140, height=40,
                                   size=9)
        self.btn_save.pack(side="left")
        self.status = tk.Label(foot, text="", font=font(9), fg=C["success"], bg=C["card"])
        self.status.pack(side="left", padx=14)

        # ── Danger zone card
        zone = tk.Frame(self.content, bg=C["card"], highlightthickness=1,
                        highlightbackground=EDGE, highlightcolor=EDGE)
        zone.pack(fill="x", pady=(16, 0))
        tk.Label(zone, text="Danger zone", font=font(10, "bold"), fg=C["accent"],
                 bg=C["card"], anchor="w").pack(fill="x", padx=24, pady=(12, 8))
        self._danger_row(zone, "Log out of all devices",
                         "Ends every active session except this one.",
                         "Log out everywhere", "outline", self._logout_everywhere)
        self._danger_row(zone, "Delete account",
                         "Removes your profile, orders, and reservations.",
                         "Delete account", "danger", self._delete_account)

    def _danger_row(self, parent, title, desc, button, kind, command):
        tk.Frame(parent, height=1, bg=EDGE).pack(fill="x")
        row = tk.Frame(parent, bg=C["card"])
        row.pack(fill="x", padx=24, pady=11)
        text = tk.Frame(row, bg=C["card"])
        text.pack(side="left")
        tk.Label(text, text=title, font=font(10, "bold"), fg=C["ink"], bg=C["card"],
                 anchor="w").pack(anchor="w")
        tk.Label(text, text=desc, font=font(9), fg=C["muted"], bg=C["card"],
                 anchor="w").pack(anchor="w")
        FlatButton(row, button, command, kind=kind, size=9, width=160,
                   height=36).pack(side="right")

    # ── data
    def _email(self):
        return self.controller.state.get("email")

    def _values(self):
        return (self.first.get().strip(), self.last.get().strip(), self.phone.get().strip())

    def _dirty_check(self):
        self.btn_save.set_enabled(self._values() != self._loaded)
        self.status.config(text="")

    def on_show(self, **kwargs):
        super().on_show(**kwargs)
        if self._email():                       # (not redirected to the landing page)
            self._load()

    def _load(self):
        record = get_customer(self._email()) or {}
        first, _, last = record.get("name", "").partition(" ")
        self.first.set(first)
        self.last.set(last.strip())
        self.phone.set(record.get("phone", ""))
        self.email.set(record.get("email", ""))
        self._loaded = self._values()
        self._paint_photo()
        self.btn_save.set_enabled(False)
        self.status.config(text="")

    def _paint_photo(self):
        photo = self.controller.state.get("photo")
        self.photo_avatar.set(self.controller.state["name"].strip()[:1] or "?",
                        load_avatar(photo, 64))
        self.btn_remove.set_enabled(bool(photo))

    # ── actions
    def save(self):
        if not self._email():
            self.controller.toast("Log in to edit your profile.")
            return
        results = [self.first.validate(), self.last.validate(), self.phone.validate()]
        if not all(results):
            (self.first, self.last, self.phone)[results.index(False)].focus()
            return
        first, last, phone = self._values()
        if (first, last, phone) == self._loaded:
            return
        name = f"{first} {last}".strip()
        error = update_customer(self._email(), name=name, phone=phone or None)
        if error:
            self.controller.toast(error)
            return
        self.controller.state["name"] = name
        self._loaded = (first, last, phone)
        self.refresh_user()
        self._paint_photo()
        self.btn_save.set_enabled(False)
        self.status.config(text="Changes saved.")
        self.focus_set()

    def _change_photo(self):
        email = self._email()
        if not email:
            return
        kinds = ("*.png *.jpg *.jpeg *.gif *.bmp *.webp" if pillow_installed()
                 else "*.png *.gif")
        path = filedialog.askopenfilename(parent=self, title="Choose a profile photo",
                                          filetypes=[("Images", kinds)])
        if not path:
            return
        filename, error = save_avatar(email, path)
        if error:
            messagebox.showerror("Profile photo", error, parent=self)
            return
        old = self.controller.state.get("photo")
        update_customer(email, photo=filename)
        if old and old != filename:
            remove_avatar(old)
        self.controller.state["photo"] = filename
        self._paint_photo()
        self.refresh_user()
        self.controller.toast("Profile photo updated.")

    def _remove_photo(self):
        email, photo = self._email(), self.controller.state.get("photo")
        if not (email and photo):
            return
        update_customer(email, photo=None)
        remove_avatar(photo)
        self.controller.state["photo"] = None
        self._paint_photo()
        self.refresh_user()
        self.controller.toast("Profile photo removed.")

    def _logout_everywhere(self):
        email = self._email()
        if not email:
            return
        if confirm_dialog(self, "Log out of all devices?",
                          "This signs your account out everywhere else. "
                          "You'll stay logged in on this device.",
                          "Log out everywhere"):
            self.controller.state["session_version"] = bump_session_version(email)
            self.controller.toast("Signed out of all other sessions.")

    def _delete_account(self):
        email = self._email()
        if not email:
            return
        if confirm_dialog(self, "Delete your account?",
                          "This permanently removes your profile, orders and "
                          "reservations. This can't be undone.",
                          "Delete account", password_for=email):
            delete_customer(email)
            self.controller.logout("Your account has been deleted.")


if __name__ == "__main__":
    import main
    main.App("profile").mainloop()
