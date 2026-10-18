"""Feast Fast - app shell, shared design system and auth.

Run:  python main.py
Screens: landing.py, create_account.py, customer_login.py, manager_login.py,
         dashboard.py (customer dashboard + shared sidebar shell)
"""
import hashlib
import hmac
import importlib
import json
import os
import re
import secrets
import shutil
import time
import tkinter as tk
from tkinter import font as tkfont

# ════════════════════════════ DESIGN SYSTEM ════════════════════════════
C = {
    "primary": "#C0120C", "primary_hover": "#9E0E09", "primary_soft": "#FBEAE8",
    "accent": "#AD3F0B", "accent_hover": "#8F3407", "accent_on_dark": "#E8702F",
    "ink": "#1A1A1A", "ink_hover": "#000000",
    "muted": "#666666",
    "bg": "#F7F2EA", "card": "#FFFFFF", "field": "#F8F6F2",
    "border": "#E3DCD0", "input_border": "#85807A", "placeholder": "#6F6F6F",
    "error": "#B00020", "error_soft": "#FDECEC",
    "success": "#256B2A", "success_soft": "#E8F5E9",
}

# Spacing scale (8-pt grid). Use these instead of ad-hoc numbers.
SP = {"xs": 4, "sm": 8, "md": 16, "lg": 24, "xl": 32, "xxl": 48}

# kind -> (fill, hover fill, text colour, edge colour or None)
BUTTON_KINDS = {
    "primary": (C["primary"], C["primary_hover"], "#FFFFFF", None),
    "accent": (C["accent"], C["accent_hover"], "#FFFFFF", None),
    "dark": (C["ink"], C["ink_hover"], "#FFFFFF", None),
    "light": ("#FFFFFF", "#F6E4E2", C["primary"], None),
    "outline": ("#FFFFFF", "#F3EEE6", C["ink"], C["input_border"]),
    "soft": (C["primary_soft"], "#F5D9D5", C["primary"], "#EBC5C0"),
    "danger": ("#FFFFFF", C["error_soft"], C["error"], "#E3B5B5"),
    "disabled": ("#EDE7DD", "#EDE7DD", "#A39C90", None),
}

_FAMILY = "Helvetica"


def init_fonts(root):
    """Pick the nicest font installed on this machine."""
    global _FAMILY
    available = set(tkfont.families(root))
    for name in ("Inter", "Segoe UI", "SF Pro Text", "Helvetica Neue",
                 "Helvetica", "Arial", "DejaVu Sans"):
        if name in available:
            _FAMILY = name
            break


def font(size=10, weight="normal", underline=False):
    f = (_FAMILY, size, weight)
    return f + ("underline",) if underline else f


# Sample menu shared by the dashboard (and the Menu screen later).
# Replace with your canteen's real items / prices.
MENU_ITEMS = [
    {"id": "ema-datshi", "name": "Ema Datshi", "price": 90, "category": "Mains",
     "tint": "#FBE6DA", "dot": "#C8501A"},
    {"id": "momo", "name": "Steamed Momo", "price": 120, "category": "Snacks",
     "tint": "#FDF1D8", "dot": "#D9A95A"},
    {"id": "fried-rice", "name": "Fried Rice", "price": 110, "category": "Mains",
     "tint": "#EAF3DF", "dot": "#6FAE5B"},
    {"id": "thukpa", "name": "Thukpa", "price": 100, "category": "Soups",
     "tint": "#F9E1DF", "dot": "#C0120C"},
]


# ── Drawing helpers ──────────────────────────────────────────────────────────
def round_rect(cv, x1, y1, x2, y2, r=12, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


def draw_logo(cv, x, y, size, color, ring=True):
    """Fork and knife (inside a ring) drawn at (x, y) on any canvas."""
    k = size / 56
    w = max(1, round(1.8 * k))

    def p(*v):
        return [(x if i % 2 == 0 else y) + c * k for i, c in enumerate(v)]

    if ring:
        cv.create_oval(*p(2, 2, 54, 54), outline=color, width=max(1, round(2 * k)))
    for tx in (16, 20, 24):                                  # fork tines
        cv.create_line(*p(tx, 15, tx, 24), fill=color, width=w, capstyle="round")
    cv.create_line(*p(16, 24, 24, 24), fill=color, width=w, capstyle="round")
    cv.create_line(*p(20, 24, 20, 41), fill=color, width=w, capstyle="round")
    cv.create_polygon(*p(36, 15, 40, 19, 40, 29, 36, 29), fill=color, outline=color)
    cv.create_line(*p(36, 15, 36, 41), fill=color, width=w, capstyle="round")


# ── Widgets ──────────────────────────────────────────────────────────────────
class FlatButton(tk.Canvas):
    """Rounded button with hover effect. `width` is in pixels (None = fit text,
    and it also stretches when packed with fill="x")."""

    def __init__(self, parent, text, command, kind="primary", size=10,
                 width=None, height=44, radius=10, bg=None):
        super().__init__(parent, bg=bg or parent.cget("bg"), highlightthickness=0,
                         height=height, cursor="hand2", takefocus=True,
                         width=width or tkfont.Font(family=_FAMILY, size=size,
                                                    weight="bold").measure(text) + 48)
        self.text, self.kind, self.size, self.radius = text, kind, size, radius
        self._command, self._hover, self._enabled = command, False, True
        self._focused = False
        self.bind("<FocusIn>", lambda e: self._set_focus(True))
        self.bind("<FocusOut>", lambda e: self._set_focus(False))
        for key in ("<Return>", "<space>"):
            self.bind(key, lambda e: self._enabled and self._command())
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<Button-1>", lambda e: self._enabled and self._command())

    def set_enabled(self, enabled):
        self._enabled = enabled
        self._hover = False
        self.config(cursor="hand2" if enabled else "arrow")
        self._draw()

    def _set_focus(self, value):
        self._focused = value
        self._draw()

    def _set_hover(self, value):
        self._hover = value and self._enabled
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = max(self.winfo_width(), 4), max(self.winfo_height(), 4)
        fill, hover, fg, edge = BUTTON_KINDS[self.kind if self._enabled else "disabled"]
        shade = hover if self._hover else fill
        round_rect(self, 1, 1, w - 1, h - 1, self.radius, fill=shade,
                   outline=edge or shade)
        if self._focused and self._enabled:                 # visible keyboard focus
            round_rect(self, 4, 4, w - 4, h - 4, max(2, self.radius - 3), fill="",
                       outline=fg, width=2)
        self.create_text(w / 2, h / 2, text=self.text, fill=fg,
                         font=font(self.size, "bold"))


class LinkLabel(tk.Label):
    """Clickable text that underlines on hover."""

    def __init__(self, parent, text, command, fg=None, bg=None, size=9, bold=False):
        self._w = "bold" if bold else "normal"
        self._size = size
        super().__init__(parent, text=text, fg=fg or C["ink"],
                         bg=bg or C["card"], font=font(size, self._w),
                         cursor="hand2")
        self.bind("<Enter>", lambda e: self.config(font=font(size, self._w, True)))
        self.bind("<Leave>", lambda e: self.config(font=font(size, self._w)))
        self.bind("<Button-1>", lambda e: command())


class Logo(tk.Canvas):
    def __init__(self, parent, size=48, bg=None, color=None):
        super().__init__(parent, width=size, height=size,
                         bg=bg or C["card"], highlightthickness=0)
        draw_logo(self, 0, 0, size, color or C["accent"])


class Icon(tk.Canvas):
    """Simple line icons drawn with canvas primitives (no image files needed)."""

    def __init__(self, parent, name, size=20, color="#FFFFFF", bg="#1C1C1C", lw=None):
        super().__init__(parent, width=size, height=size, bg=bg, highlightthickness=0)
        k = size / 24
        w = lw or max(1, round(1.8 * k))

        def S(vals):
            return [v * k for v in vals]

        def line(*pts):
            self.create_line(*S(pts), fill=color, width=w, capstyle="round",
                             joinstyle="round")

        def rect(*pts):
            self.create_rectangle(*S(pts), outline=color, width=w)

        def oval(*pts):
            self.create_oval(*S(pts), outline=color, width=w)

        def arc(*pts):
            self.create_arc(*S(pts), start=0, extent=180, style="arc",
                            outline=color, width=w)

        if name == "home":
            line(3, 12, 12, 4, 21, 12)
            line(6, 10.5, 6, 20, 18, 20, 18, 10.5)
            line(10, 20, 10, 14, 14, 14, 14, 20)
        elif name == "menu":
            for x in (6, 9, 12):
                line(x, 4, x, 10)
            line(6, 10, 12, 10)
            line(9, 10, 9, 21)
            line(18, 4, 18, 21)
            self.create_polygon(*S((18, 4, 21, 7, 21, 13, 18, 13)),
                                outline=color, fill=color)
        elif name == "cart":
            line(2, 4, 5, 4, 7.5, 15, 19, 15, 21, 7, 6, 7)
            oval(8.7, 18, 11.3, 20.6)
            oval(15.7, 18, 18.3, 20.6)
        elif name == "order":
            rect(5, 9, 19, 21)
            line(9, 9, 9, 6, 10.5, 4, 13.5, 4, 15, 6, 15, 9)
        elif name == "table":
            arc(6, 4, 18, 20)
            line(4, 12, 20, 12)
            line(7, 12, 7, 20)
            line(17, 12, 17, 20)
        elif name == "user":
            oval(8, 4, 16, 12)
            arc(4, 14, 20, 30)


class Banner(tk.Label):
    """One reserved line for form-level messages (no layout jumping)."""

    def __init__(self, parent):
        super().__init__(parent, text=" ", font=font(9), bg=C["card"], anchor="w",
                         justify="left", wraplength=340, padx=10, pady=7)

    def show(self, message, kind="error"):
        if kind == "error":
            self.config(text=message, fg=C["error"], bg=C["error_soft"])
        else:
            self.config(text=message, fg=C["success"], bg=C["success_soft"])

    def hide(self):
        self.config(text=" ", bg=C["card"])


class FormField(tk.Frame):
    """Label + entry + placeholder + show/hide toggle + inline error text."""

    def __init__(self, parent, label, placeholder="", secret=False,
                 validator=None, on_enter=None):
        super().__init__(parent, bg=C["card"])
        self.placeholder, self.secret, self.validator = placeholder, secret, validator
        self._ph = self._focus = self._err = self._touched = self._revealed = False

        tk.Label(self, text=label, font=font(9, "bold"), fg=C["ink"],
                 bg=C["card"], anchor="w").pack(fill="x")

        self.box = tk.Frame(self, bg=C["field"], highlightthickness=1,
                            highlightbackground=C["input_border"],
                            highlightcolor=C["input_border"])
        self.box.pack(fill="x", pady=(5, 0))

        self.entry = tk.Entry(self.box, relief="flat", bd=0, bg=C["field"],
                              fg=C["ink"], insertbackground=C["ink"],
                              font=font(10), highlightthickness=0)
        if secret:
            self.toggle = LinkLabel(self.box, "Show", self._toggle,
                                    fg=C["muted"], bg=C["field"], size=9)
            self.toggle.pack(side="right", padx=(0, 12))
        self.entry.pack(side="left", fill="x", expand=True, padx=12, pady=10)

        self.err = tk.Label(self, text=" ", font=font(9), fg=C["error"],
                            bg=C["card"], anchor="w")
        self.err.pack(fill="x", pady=(2, 0))

        self.entry.bind("<FocusIn>", self._focus_in)
        self.entry.bind("<FocusOut>", self._focus_out)
        self.entry.bind("<KeyRelease>", self._key)
        if on_enter:
            self.entry.bind("<Return>", lambda e: on_enter())
        self._show_placeholder()

    # -- public API
    def get(self):
        return "" if self._ph else self.entry.get()

    def validate(self):
        message = self.validator(self.get()) if self.validator else None
        self.set_error(message)
        return message is None

    def set_error(self, message=None):
        self._err = bool(message)
        self.err.config(text=message or " ")
        self._refresh_border()

    def focus(self):
        self.entry.focus_set()

    def clear(self):
        self.entry.delete(0, "end")
        self._ph, self._touched, self._revealed = False, False, False
        if self.secret:
            self.toggle.config(text="Show")
        self.set_error(None)
        self._style_text()
        if not self._focus:
            self._show_placeholder()

    def set(self, value):
        self.clear()
        if value:
            self.entry.delete(0, "end")          # drop the placeholder clear() inserted
            self._ph = False
            self._style_text()
            self.entry.insert(0, value)

    # -- internals
    def _style_text(self):
        self.entry.config(fg=C["ink"],
                          show="•" if self.secret and not self._revealed else "")

    def _show_placeholder(self):
        if self.entry.get():
            return
        self.entry.config(show="", fg=C["placeholder"])
        self.entry.insert(0, self.placeholder)
        self._ph = True

    def _focus_in(self, _):
        self._focus, self._touched = True, True
        if self._ph:
            self.entry.delete(0, "end")
            self._ph = False
            self._style_text()
        self._refresh_border()

    def _focus_out(self, _):
        self._focus = False
        if not self.entry.get():
            self._show_placeholder()
        if self._touched:
            self.validate()
        self._refresh_border()

    def _key(self, event):
        if self._err and event.keysym not in ("Tab", "Return"):
            self.validate()

    def _toggle(self):
        self._revealed = not self._revealed
        self.toggle.config(text="Hide" if self._revealed else "Show")
        if not self._ph:
            self._style_text()

    def _refresh_border(self):
        colour = C["error"] if self._err else (C["ink"] if self._focus else C["input_border"])
        self.box.config(highlightbackground=colour, highlightcolor=colour)


class RoleSwitch(tk.Frame):
    """Segmented control: Customer | Staff (jumps between the two login screens)."""

    def __init__(self, parent, active, controller):
        super().__init__(parent, bg=C["field"], padx=4, pady=4,
                         highlightthickness=1, highlightbackground=C["border"])
        for key, label, target in (("customer", "Customer", "customer_login"),
                                   ("staff", "Staff", "manager_login")):
            on = key == active
            tab = tk.Label(self, text=label, font=font(9, "bold"), padx=18, pady=7,
                           cursor="hand2", bg=C["card"] if on else C["field"],
                           fg=C["ink"] if on else C["muted"])
            tab.pack(side="left", expand=True, fill="x")
            if not on:
                tab.bind("<Button-1>", lambda e, t=target: controller.show(t))


# ── Layout helpers ───────────────────────────────────────────────────────────
class Page(tk.Frame):
    """Base class for every screen."""

    def __init__(self, parent, controller):
        super().__init__(parent, bg=C["bg"])
        self.controller = controller

    def on_show(self, **kwargs):
        """Called every time the page is displayed; reset forms here."""


THEMES = {
    "customer": dict(bg=C["primary"], d1="#CF2019", d2="#A60F09", sub="#FDE8E6"),
    "signup": dict(bg=C["accent"], d1="#BD4C17", d2="#8F3407", sub="#FFEFE3"),
    "staff": dict(bg="#1A1A1A", d1="#262626", d2="#101010", sub="#B9B3A8",
                  pop=C["primary"]),
}


class BrandPanel(tk.Canvas):
    """Left-hand brand panel of the auth screens."""

    def __init__(self, parent, theme, headline, sub, features):
        self.t = THEMES[theme]
        super().__init__(parent, bg=self.t["bg"], highlightthickness=0)
        self.headline, self.sub, self.features = headline, sub, features
        self.bind("<Configure>", lambda e: self._draw())

    def _draw(self):
        w, h, t = self.winfo_width(), self.winfo_height(), self.t
        self.delete("all")
        if w < 80:
            return
        self.create_oval(w - 170, -150, w + 190, 210, fill=t["d1"], outline="")
        self.create_oval(-120, h - 210, 200, h + 110, fill=t["d2"], outline="")
        self.create_oval(w * 0.55, h * 0.8, w * 0.55 + 110, h * 0.8 + 110,
                         outline=t["d1"], width=2)
        if t.get("pop"):
            self.create_oval(w - 84, h - 128, w - 40, h - 84, fill=t["pop"], outline="")
        draw_logo(self, 44, 40, 40, "#FFFFFF")
        self.create_text(94, 60, text="Feast Fast", anchor="w", fill="#FFFFFF",
                         font=font(14, "bold"))
        head = self.create_text(44, h * 0.33, text=self.headline, anchor="nw",
                                fill="#FFFFFF", font=font(28, "bold"), width=w - 88)
        y = self.bbox(head)[3] + 14
        sub = self.create_text(44, y, text=self.sub, anchor="nw", fill=t["sub"],
                               font=font(11), width=w - 100)
        y = self.bbox(sub)[3] + 30
        for text in self.features:
            self.create_oval(44, y, 66, y + 22, fill="#FFFFFF", outline="")
            self.create_line(50, y + 11, 54, y + 15, 61, y + 7, fill=t["bg"], width=2,
                             capstyle="round", joinstyle="round")
            self.create_text(80, y + 11, text=text, anchor="w", fill="#FFFFFF",
                             font=font(10))
            y += 38
        self.create_text(44, h - 32, text="Smart  •  Fast  •  Convenient", anchor="w",
                         fill=t["sub"], font=font(9))


class AuthPage(Page):
    """Split screen: brand panel on the left, form (self.body) on the right."""

    def __init__(self, parent, controller, theme, headline, sub, features):
        super().__init__(parent, controller)
        self.configure(bg=C["card"])
        BrandPanel(self, theme, headline, sub, features).place(
            x=0, y=0, relwidth=0.42, relheight=1)
        right = tk.Frame(self, bg=C["card"])
        right.place(relx=0.42, y=0, relwidth=0.58, relheight=1)
        LinkLabel(right, "←  Back to home", lambda: controller.show("landing"),
                  fg=C["muted"]).place(x=28, y=24)
        self.body = tk.Frame(right, bg=C["card"])
        self.body.place(relx=0.5, rely=0.5, anchor="center", width=380)

    def heading(self, title, subtitle):
        tk.Label(self.body, text=title, font=font(22, "bold"), fg=C["ink"],
                 bg=C["card"], anchor="w").pack(fill="x")
        tk.Label(self.body, text=subtitle, font=font(10), fg=C["muted"],
                 bg=C["card"], anchor="w").pack(fill="x", pady=(4, 14))


# ════════════════════════════ AUTH & VALIDATION ════════════════════════════
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")

# Default staff account, created the first time the app runs. Change it!
DEFAULT_STAFF = ("manager", "Manager@123", "Store Manager")

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,32}$")


# ── Validators: return an error message, or None when the value is fine ─────
def validate_name(v):
    v = v.strip()
    if not v:
        return "Full name is required."
    if len(v) < 2 or len(v) > 50:
        return "Name must be 2-50 characters."
    if not v[0].isalpha() or not all(c.isalpha() or c in " .'-" for c in v):
        return "Use letters, spaces, apostrophes or hyphens only."
    return None


def validate_email(v):
    v = v.strip()
    if not v:
        return "Email is required."
    if len(v) > 254 or not EMAIL_RE.match(v):
        return "Enter a valid email, e.g. name@example.com."
    return None


def validate_password(v):
    if not v:
        return "Password is required."
    if len(v) < 8:
        return "Use at least 8 characters."
    if len(v) > 64:
        return "Use at most 64 characters."
    if " " in v:
        return "Password cannot contain spaces."
    if not re.search(r"[a-z]", v) or not re.search(r"[A-Z]", v):
        return "Include both upper and lower case letters."
    if not re.search(r"\d", v):
        return "Include at least one number."
    if not re.search(r"[^A-Za-z0-9]", v):
        return "Include at least one symbol (e.g. ! @ # $)."
    return None


PHONE_RE = re.compile(r"^\+?[0-9][0-9 ()-]{5,19}$")


def validate_phone(v):
    """Optional field: empty is fine."""
    v = v.strip()
    if not v:
        return None
    if not PHONE_RE.match(v) or not 7 <= len(re.sub(r"\D", "", v)) <= 15:
        return "Enter a valid phone number, e.g. +975 17 123 456."
    return None


def validate_required_password(v):
    return "Password is required." if not v else None


def validate_username(v):
    v = v.strip()
    if not v:
        return "Username is required."
    if not USERNAME_RE.match(v):
        return "3-32 characters: letters, numbers, . _ - only."
    return None


# ── Storage ──────────────────────────────────────────────────────────────────
def _hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000)
    return {"salt": salt, "hash": digest.hex()}


def _matches(password, record):
    candidate = _hash(password, record["salt"])["hash"]
    return hmac.compare_digest(candidate, record["hash"])


def _load():
    try:
        with open(DB_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    data.setdefault("customers", {})
    data.setdefault("staff", {})
    if not data["staff"]:
        user, pw, name = DEFAULT_STAFF
        data["staff"][user] = {"name": name, **_hash(pw)}
        _save(data)
    return data


def _save(data):
    with open(DB_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def register_customer(name, email, password):
    """Returns None on success, or an error message."""
    data = _load()
    key = email.strip().lower()
    if key in data["customers"]:
        return "An account with this email already exists."
    data["customers"][key] = {"name": name.strip(), "email": key, **_hash(password)}
    _save(data)
    return None


def verify_customer(email, password):
    record = _load()["customers"].get(email.strip().lower())
    ok = _matches(password, record or {"salt": "00" * 16, "hash": ""})
    return record if record and ok else None


def verify_staff(username, password):
    record = _load()["staff"].get(username.strip().lower())
    ok = _matches(password, record or {"salt": "00" * 16, "hash": ""})
    return record if record and ok else None


# ── Profile helpers ──────────────────────────────────────────────────────────
AVATAR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "avatars")


def get_customer(email):
    return _load()["customers"].get((email or "").strip().lower())


def update_customer(email, **fields):
    """Set fields on a customer record (a value of None removes the field).
    Returns None on success, or an error message."""
    data = _load()
    record = data["customers"].get(email.strip().lower())
    if record is None:
        return "Account not found."
    for key, value in fields.items():
        if value is None:
            record.pop(key, None)
        else:
            record[key] = value
    _save(data)
    return None


def delete_customer(email):
    data = _load()
    record = data["customers"].pop(email.strip().lower(), None)
    if record is None:
        return False
    _save(data)
    remove_avatar(record.get("photo"))
    return True


def bump_session_version(email):
    """Invalidate every other signed-in session of this account. Each session
    remembers the version it logged in with and signs itself out when it no
    longer matches (checked whenever a customer screen is shown)."""
    data = _load()
    record = data["customers"][email.strip().lower()]
    record["session_version"] = record.get("session_version", 0) + 1
    _save(data)
    return record["session_version"]


def pillow_installed():
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False


def save_avatar(email, src):
    """Store a profile photo. Returns (filename, None) or (None, error)."""
    if os.path.getsize(src) > 8 * 1024 * 1024:
        return None, "That image is too large (8 MB max)."
    os.makedirs(AVATAR_DIR, exist_ok=True)
    stem = hashlib.sha256(email.strip().lower().encode()).hexdigest()[:16]
    try:
        from PIL import Image, ImageOps
        name = stem + ".png"
        ImageOps.fit(Image.open(src).convert("RGB"), (256, 256)).save(
            os.path.join(AVATAR_DIR, name))
        return name, None
    except ImportError:
        ext = os.path.splitext(src)[1].lower()
        if ext not in (".png", ".gif"):
            return None, ("Only PNG or GIF photos are supported.\n"
                          "Install Pillow (pip install pillow) to use JPG photos too.")
        name = stem + ext
        dest = os.path.join(AVATAR_DIR, name)
        shutil.copyfile(src, dest)
        try:
            tk.PhotoImage(file=dest)           # make sure Tk can actually read it
        except tk.TclError:
            os.remove(dest)
            return None, "That file isn't a valid image."
        return name, None
    except Exception:
        return None, "That file isn't a valid image."


def remove_avatar(filename):
    if filename:
        try:
            os.remove(os.path.join(AVATAR_DIR, filename))
        except OSError:
            pass


def load_avatar(filename, size):
    """PhotoImage of a stored avatar (about size x size), or None."""
    path = os.path.join(AVATAR_DIR, filename) if filename else ""
    if not filename or not os.path.exists(path):
        return None
    try:
        from PIL import Image, ImageOps, ImageTk
        return ImageTk.PhotoImage(ImageOps.fit(Image.open(path).convert("RGBA"),
                                               (size, size)))
    except ImportError:
        pass
    except Exception:
        return None
    try:                                       # no Pillow: PNG/GIF through Tk itself
        img = tk.PhotoImage(file=path)
        short = min(img.width(), img.height())
        if short < size:
            return img.zoom(-(-size // short))
        return img.subsample(max(1, short // size))
    except tk.TclError:
        return None


# ── Brute-force protection ──────────────────────────────────────────────────
class Throttle:
    """Locks an identity for `lock_seconds` after `limit` failed attempts."""

    def __init__(self, limit=5, lock_seconds=30):
        self.limit, self.lock_seconds = limit, lock_seconds
        self._fails, self._until = {}, {}

    def locked_for(self, key):
        return max(0, int(self._until.get(key, 0) - time.time() + 0.999))

    def fail(self, key):
        self._fails[key] = self._fails.get(key, 0) + 1
        if self._fails[key] >= self.limit:
            self._until[key] = time.time() + self.lock_seconds
            self._fails[key] = 0

    def reset(self, key):
        self._fails.pop(key, None)
        self._until.pop(key, None)


THROTTLE = Throttle()


# ════════════════════════════ MANAGER HOME (placeholder) ════════════════════════════
class HomePage(Page):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        card = tk.Frame(self, bg=C["card"], highlightthickness=1,
                        highlightbackground=C["border"])
        card.place(relx=0.5, rely=0.46, anchor="center")
        body = tk.Frame(card, bg=C["card"])
        body.pack(padx=64, pady=44)
        Logo(body, size=64).pack()
        self.title = tk.Label(body, text="", font=font(22, "bold"), fg=C["ink"], bg=C["card"])
        self.title.pack(pady=(16, 6))
        self.chip = tk.Label(body, text="", font=font(9, "bold"), fg=C["primary"],
                             bg=C["primary_soft"], padx=10, pady=3)
        self.chip.pack()
        self.sub = tk.Label(body, text="", font=font(10), fg=C["muted"], bg=C["card"])
        self.sub.pack(pady=(12, 0))
        FlatButton(body, "Log Out", controller.logout, kind="dark", size=9,
                   width=160, height=40).pack(pady=(24, 0))

    def on_show(self, role="Manager", name="", **kwargs):
        self.title.config(text=f"Welcome, {name}")
        self.chip.config(text=role.upper())
        self.sub.config(text=f"The {role.lower()} screens come next.")


# ════════════════════════════ APP / NAVIGATION ════════════════════════════
# page name -> (module, class[, constructor options])
PAGES = {
    "landing": ("landing", "LandingPage"),
    "create_account": ("create_account", "CreateAccountPage"),
    "customer_login": ("customer_login", "CustomerLoginPage"),
    "manager_login": ("manager_login", "ManagerLoginPage"),
    "home": ("main", "HomePage"),          # placeholder shown after a manager login
    # ── customer screens (dashboard.py) ──
    "dashboard": ("dashboard", "DashboardPage"),
    # Placeholders until the real screens exist. To replace one, point its entry
    # at your new module/class (subclass CustomerPage) and drop the options dict.
    "menu": ("dashboard", "SectionPage", dict(
        key="menu", title="Menu", icon="menu",
        blurb="Browse today's menu and add items to your cart.")),
    "cart": ("dashboard", "SectionPage", dict(
        key="cart", title="My Cart", icon="cart",
        blurb="Review the items you've added before placing your order.")),
    "orders": ("dashboard", "SectionPage", dict(
        key="orders", title="My Order", icon="order",
        blurb="Track your current order and see your past orders.")),
    "reservation": ("dashboard", "SectionPage", dict(
        key="reservation", title="Reservation", icon="table",
        blurb="Book a table or cancel an existing reservation.")),
    "profile": ("profile_page", "ProfilePage"),
}


class App(tk.Tk):
    def __init__(self, start="landing"):
        super().__init__()
        init_fonts(self)
        self.title("Feast Fast")
        self.configure(bg=C["bg"])
        self.minsize(960, 680)
        w, h = 1100, 720
        x = (self.winfo_screenwidth() - w) // 2
        y = max(0, (self.winfo_screenheight() - h) // 2 - 20)
        self.geometry(f"{w}x{h}+{x}+{y}")

        # Shared session data. Cart / orders / reservations screens read and
        # write these lists; the dashboard shows their counts.
        self.state = {"name": "Guest", "email": None, "photo": None,
                      "session_version": 0, "cart": [], "orders": [], "reservations": []}
        self._current = None
        self._toast = None

        self.container = tk.Frame(self, bg=C["bg"])
        self.container.pack(fill="both", expand=True)
        self.frames = {}
        self.show(start)

    def show(self, page_name, /, **kwargs):
        name = page_name          # positional-only, so callers may also pass name="..."
        if name not in self.frames:
            module, cls, *extra = PAGES[name]
            options = extra[0] if extra else {}
            page = getattr(importlib.import_module(module), cls)(
                self.container, self, **options)
            page.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.frames[name] = page
        page = self.frames[name]
        self._current = name
        page.on_show(**kwargs)
        if self._current == name:     # on_show may have redirected (e.g. forced logout)
            page.tkraise()

    def logout(self, message="You've been signed out."):
        self.state.update(name="Guest", email=None, photo=None, session_version=0,
                          cart=[], orders=[], reservations=[])
        self.show("landing")
        self.toast(message)

    def toast(self, message):
        """Small message that fades away after a couple of seconds."""
        if self._toast is not None:
            self._toast.destroy()
        lbl = tk.Label(self, text=message, bg=C["ink"], fg="#FFFFFF",
                       font=font(10, "bold"), padx=18, pady=10)
        lbl.place(relx=0.5, rely=0.94, anchor="center")
        lbl.lift()
        self._toast = lbl
        self.after(2600, lambda: lbl.destroy() if lbl.winfo_exists() else None)


if __name__ == "__main__":
    import main as _m          # run the single canonical copy of this module
    _m.App().mainloop()
