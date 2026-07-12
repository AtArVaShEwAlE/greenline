import ctypes
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('greenline.app.v1')
import customtkinter as ctk
from tkinter import filedialog
import threading
import queue
from PIL import Image
from customtkinter import CTkImage
from highlighter import highlight_python
from vcs import git_commit, get_commit_history, restore_file_from_commit, get_repo_root
import os
import tkinter as tk
import difflib
from patcher import get_call_count
from sessions import save_session, load_sessions
from settings import load_settings, save_settings as persist_settings, load_project_settings, save_project_settings
from tkinterdnd2 import TkinterDnD, DND_FILES

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")
# ── DESIGN TOKENS ──
COLOR_BG = "#0a0a0e"
COLOR_PANEL = "#111114"
COLOR_PANEL_ALT = "#0e0e12"
COLOR_BORDER = "#1e1e24"
COLOR_TEXT_PRIMARY = "#e4e4e8"
COLOR_TEXT_SECONDARY = "#8a8a98"
COLOR_TEXT_MUTED = "#55555f"
COLOR_ACCENT = "#01a501"
COLOR_ACCENT_HOVER = "#009100"
COLOR_SUCCESS = "#5bcaa5"
COLOR_WARNING = "#fac775"
COLOR_ERROR = "#f0997b"
COLOR_BTN_SECONDARY = "#1c1c22"
COLOR_BTN_SECONDARY_HOVER = "#28282f"
FONT_MONO = "Consolas"
COLOR_TAB_ACTIVE = COLOR_PANEL
COLOR_TAB_INACTIVE = COLOR_PANEL_ALT
COLOR_SIDEBAR = "#0c0c10"
COLOR_LINE_NUMBERS = "#3a3a44"

class DnDApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)

app = DnDApp()
app.title("Greenline")
app.geometry("1100x700")
app.minsize(900, 600)
app.iconbitmap(r"E:\greenline\logo.ico")
app.configure(fg_color=COLOR_BG)
app.settings = load_settings()
app.grid_rowconfigure(0, weight=0)   # combined header — fixed
app.grid_rowconfigure(1, weight=1)   # panels — expandable
app.grid_columnconfigure(0, weight=3)
app.grid_columnconfigure(1, weight=2)


# ── HEADER BAR (logo + model + retries, all in one row) ──
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]

header_bar = ctk.CTkFrame(app, height=56, corner_radius=0, fg_color=COLOR_PANEL_ALT)
header_bar.grid(row=0, column=0, columnspan=2, sticky="ew")
header_bar.grid_propagate(False)

header_border = ctk.CTkFrame(app, height=1, corner_radius=0, fg_color=COLOR_BORDER)
header_border.grid(row=0, column=0, columnspan=2, sticky="sew")

wm_image = CTkImage(light_image=Image.open("wordmark.png"),
                    dark_image=Image.open("wordmark.png"),
                    size=(150, 28))
wordmark_label = ctk.CTkLabel(header_bar, image=wm_image, text="")
wordmark_label.pack(side="left", padx=(20, 28), pady=10)

ctk.CTkLabel(header_bar, text="Model", font=ctk.CTkFont(family=FONT_MONO, size=11),
             text_color=COLOR_TEXT_MUTED).pack(side="left", padx=(0, 8))

model_var = ctk.StringVar(value=app.settings.get("model", GROQ_MODELS[0]))
model_menu = ctk.CTkOptionMenu(header_bar, values=GROQ_MODELS, variable=model_var,
                                width=200, height=28,
                                fg_color=COLOR_BTN_SECONDARY, button_color=COLOR_ACCENT,
                                button_hover_color=COLOR_ACCENT_HOVER,
                                font=ctk.CTkFont(family=FONT_MONO, size=11))
model_menu.pack(side="left", padx=(0, 24))

ctk.CTkLabel(header_bar, text="Max retries", font=ctk.CTkFont(family=FONT_MONO, size=11),
             text_color=COLOR_TEXT_MUTED).pack(side="left", padx=(0, 8))

retry_var = ctk.StringVar(value=str(app.settings.get("max_retries", 5)))
retry_entry = ctk.CTkEntry(header_bar, textvariable=retry_var, width=50, height=28,
                            fg_color=COLOR_PANEL, border_color=COLOR_BORDER,
                            text_color=COLOR_TEXT_PRIMARY,
                            font=ctk.CTkFont(family=FONT_MONO, size=11))
retry_entry.pack(side="left")
left_title = ctk.CTkLabel(header_bar, text="No project loaded",
                           font=ctk.CTkFont(family=FONT_MONO, size=12),
                           text_color=COLOR_TEXT_SECONDARY, anchor="w")
left_title.pack(side="left", padx=(24, 0))

def open_settings_window():
    win = ctk.CTkToplevel(app)
    win.title("Settings")
    win.geometry("380x280")
    win.configure(fg_color=COLOR_BG)

    ctk.CTkLabel(win, text="Settings",
                 font=ctk.CTkFont(family=FONT_MONO, size=15, weight="bold"),
                 text_color=COLOR_TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(20, 16))

    ctk.CTkLabel(win, text="Model", font=ctk.CTkFont(family=FONT_MONO, size=12),
                 text_color=COLOR_TEXT_SECONDARY).pack(anchor="w", padx=20)
    settings_model_menu = ctk.CTkOptionMenu(win, values=GROQ_MODELS, variable=model_var,
                                             fg_color=COLOR_BTN_SECONDARY, button_color=COLOR_ACCENT,
                                             button_hover_color=COLOR_ACCENT_HOVER)
    settings_model_menu.pack(anchor="w", padx=20, pady=(4, 16), fill="x")

    ctk.CTkLabel(win, text="Max retries", font=ctk.CTkFont(family=FONT_MONO, size=12),
                 text_color=COLOR_TEXT_SECONDARY).pack(anchor="w", padx=20)
    settings_retry_entry = ctk.CTkEntry(win, textvariable=retry_var,
                                         fg_color=COLOR_PANEL, border_color=COLOR_BORDER,
                                         text_color=COLOR_TEXT_PRIMARY)
    settings_retry_entry.pack(anchor="w", padx=20, pady=(4, 20), fill="x")

    def save_settings_action():
        try:
            retries = int(retry_var.get())
            retry_var.set(str(max(1, min(retries, 20))))
        except ValueError:
            retry_var.set("5")

        app.settings["model"] = model_var.get()
        app.settings["max_retries"] = int(retry_var.get())
        persist_settings(app.settings)
        if hasattr(app, "current_project_dir"):
            save_project_settings(app.current_project_dir, {
                "model": app.settings["model"],
                "max_retries": app.settings["max_retries"]
            })

        write_log(f"⚙️ Settings updated — model: {app.settings['model']}, "
                   f"max retries: {app.settings['max_retries']}")
        win.destroy()

    save_btn = ctk.CTkButton(win, text="Save", height=36,
                              fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
                              corner_radius=8, font=ctk.CTkFont(size=13, weight="bold"),
                              command=save_settings_action)
    save_btn.pack(padx=20, pady=(0, 20), fill="x")

# ── LEFT PANEL ──
left_panel = ctk.CTkFrame(app, corner_radius=0, fg_color=COLOR_PANEL, border_width=0)
left_panel.grid(row=1, column=0, sticky="nsew")

# ── BODY: sidebar (left) + tabs/editor (right) ──
left_body = ctk.CTkFrame(left_panel, fg_color="transparent")
left_body.pack(fill="both", expand=True)

# Sidebar (file explorer) — spans full height
sidebar = ctk.CTkFrame(left_body, width=170, corner_radius=0, fg_color=COLOR_SIDEBAR, border_color=COLOR_BORDER)
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)

ctk.CTkLabel(sidebar, text="EXPLORER", font=ctk.CTkFont(family=FONT_MONO, size=10, weight="bold"),
             text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=12, pady=(12, 6))

sidebar_filter_var = ctk.StringVar()
sidebar_filter_entry = ctk.CTkEntry(sidebar, textvariable=sidebar_filter_var,
                                     placeholder_text="Filter files...", height=26,
                                     fg_color=COLOR_PANEL, border_color=COLOR_BORDER,
                                     text_color=COLOR_TEXT_PRIMARY,
                                     font=ctk.CTkFont(family=FONT_MONO, size=11))
sidebar_filter_entry.pack(fill="x", padx=8, pady=(0, 6))
sidebar_filter_var.trace_add("write", lambda *args: filter_sidebar())

sidebar_list = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
sidebar_list.pack(fill="both", expand=True, padx=4, pady=(0, 4))

divider = ctk.CTkFrame(left_body, width=1, fg_color=COLOR_BORDER)
divider.pack(side="left", fill="y")
# Draggable resize grip (VS Code style)
resize_grip = ctk.CTkFrame(left_body, width=4, fg_color="transparent", cursor="sb_h_double_arrow")
resize_grip.pack(side="left", fill="y")

def _on_drag(event):
    new_width = sidebar.winfo_width() + event.x
    new_width = max(120, min(new_width, 400))
    sidebar.configure(width=new_width)

resize_grip.bind("<B1-Motion>", _on_drag)
resize_grip.bind("<Enter>", lambda e: resize_grip.configure(fg_color=COLOR_ACCENT))
resize_grip.bind("<Leave>", lambda e: resize_grip.configure(fg_color="transparent"))

# Editor area — tabs, code, and the load buttons all live here now
editor_area = ctk.CTkFrame(left_body, fg_color="transparent")
editor_area.pack(side="left", fill="both", expand=True)

tab_bar = ctk.CTkFrame(editor_area, height=36, fg_color=COLOR_PANEL_ALT)
tab_bar.pack(fill="x")
tab_bar.pack_propagate(False)

# Unified container so line numbers + code look like ONE seamless box
code_container = ctk.CTkFrame(editor_area, corner_radius=0, fg_color=COLOR_BG, border_width=0)
code_container.pack(fill="both", expand=True)

line_numbers = tk.Text(code_container, width=4, padx=8, pady=10,
                        font=(FONT_MONO, 13), bg=COLOR_BG, fg=COLOR_LINE_NUMBERS,
                        bd=0, highlightthickness=0, wrap="none", state="disabled")
line_numbers.pack(side="left", fill="y")

code_box = ctk.CTkTextbox(code_container,
                           font=ctk.CTkFont(family=FONT_MONO, size=13),
                           fg_color=COLOR_BG, text_color=COLOR_TEXT_PRIMARY,
                           corner_radius=0, wrap="none", border_width=0)
code_box.pack(side="left", fill="both", expand=True, padx=(2, 4))

# Buttons now live at the bottom of the EDITOR area — not under the sidebar
editor_btn_row = ctk.CTkFrame(editor_area, fg_color="transparent")
editor_btn_row.pack(fill="x", padx=12, pady=10)


# ── TAB / SIDEBAR STATE ──
tab_buttons = {}
sidebar_buttons = {}

def update_line_numbers(content):
    line_count = content.count("\n") + 1
    numbers = "\n".join(str(i) for i in range(1, line_count + 1))
    line_numbers.configure(state="normal")
    line_numbers.delete("1.0", "end")
    line_numbers.insert("1.0", numbers)
    line_numbers.configure(state="disabled")

def _sync_scroll(event):
    delta = -1 if event.delta > 0 else 1
    code_box._textbox.yview_scroll(delta, "units")
    line_numbers.yview_scroll(delta, "units")
    return "break"

code_box._textbox.bind("<MouseWheel>", _sync_scroll)

def open_file_tab(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        write_log(f"⚠️ Couldn't open {os.path.basename(file_path)}.")
        return

    code_box.delete("1.0", "end")
    code_box.insert("1.0", content)
    highlight_python(code_box, content)
    update_line_numbers(content)

    app.current_file = file_path

    for path, btn in tab_buttons.items():
        is_active = (path == file_path)
        btn.configure(fg_color=COLOR_SUCCESS if is_active else COLOR_TAB_INACTIVE,
                    text_color=COLOR_BG if is_active else COLOR_TEXT_MUTED)
    for path, btn in sidebar_buttons.items():
        is_active = (path == file_path)
        btn.configure(fg_color=COLOR_TAB_ACTIVE if is_active else "transparent",
                      text_color=COLOR_TEXT_PRIMARY if is_active else COLOR_TEXT_SECONDARY)

def _populate_project(folder_path, abs_files, initial_file):
    """Shared logic for building the tab bar + sidebar + opening a file, used by both loaders."""
    for widget in tab_bar.winfo_children():
        widget.destroy()
    for widget in sidebar_list.winfo_children():
        widget.destroy()
    tab_buttons.clear()
    sidebar_buttons.clear()

    app.current_project_dir = folder_path
    app.loaded_files = abs_files
    app.settings["last_project_dir"] = folder_path
    persist_settings(app.settings)

    project_settings = load_project_settings(folder_path)
    if project_settings:
        if "model" in project_settings:
            model_var.set(project_settings["model"])
        if "max_retries" in project_settings:
            retry_var.set(str(project_settings["max_retries"]))
        if "test_file" in project_settings and os.path.exists(project_settings["test_file"]):
            app.current_test_file = project_settings["test_file"]
            test_file_label.configure(text=f"tests: {app.current_test_file}", text_color=COLOR_SUCCESS)
        write_log(f"⚙️ Loaded project settings from {folder_path}\\.greenline.json")
    app.loaded_files = abs_files

    for abs_path in abs_files:
        file_label = os.path.basename(abs_path)

        tab_btn = ctk.CTkButton(tab_bar, text=file_label, height=36, corner_radius=0,
                                 fg_color=COLOR_TAB_INACTIVE, text_color=COLOR_TEXT_MUTED,
                                 hover_color=COLOR_BTN_SECONDARY_HOVER,
                                 font=ctk.CTkFont(family=FONT_MONO, size=11),
                                 command=lambda p=abs_path: open_file_tab(p))
        tab_btn.pack(side="left")
        tab_buttons[abs_path] = tab_btn

        side_btn = ctk.CTkButton(sidebar_list, text=f"🐍 {file_label}", height=26,
                                  fg_color="transparent", text_color=COLOR_TEXT_SECONDARY,
                                  hover_color=COLOR_BTN_SECONDARY_HOVER, corner_radius=6,
                                  anchor="w", font=ctk.CTkFont(family=FONT_MONO, size=11),
                                  command=lambda p=abs_path: open_file_tab(p))
        side_btn.pack(fill="x", pady=1)
        sidebar_buttons[abs_path] = side_btn

    left_title.configure(text=f"{folder_path}  ({len(abs_files)} file(s))")
    show_toast(f"Loaded {len(abs_files)} file(s).", kind="success")
    open_file_tab(initial_file)

def _persist_test_file(file_path):
    if hasattr(app, "current_project_dir"):
        proj_settings = load_project_settings(app.current_project_dir) or {}
        proj_settings["test_file"] = file_path
        proj_settings.setdefault("model", app.settings["model"])
        proj_settings.setdefault("max_retries", app.settings["max_retries"])
        save_project_settings(app.current_project_dir, proj_settings)

def load_folder():
    folder_path = filedialog.askdirectory(title="Select project folder")
    if folder_path:
        py_files = [f for f in os.listdir(folder_path)
                    if (f.endswith(".py") or f.endswith(".js"))
                    and not f.startswith("test_")
                    and not f.endswith(".test.js")]

        if not py_files:
            write_log("⚠️ No source files found in that folder.")
            show_toast("No source files found in that folder.", kind="error")
            return

        abs_files = [os.path.join(folder_path, f) for f in py_files]
        _populate_project(folder_path, abs_files, abs_files[0])

def handle_drop(event):
    raw_path = event.data.strip("{}")  # Windows wraps paths with spaces in {}

    if not os.path.exists(raw_path):
        show_toast("Couldn't read the dropped item.", kind="error")
        return

    filename = os.path.basename(raw_path)
    is_test_file = filename.startswith("test_") or filename.endswith(".test.js")

    if os.path.isdir(raw_path):
        py_files = [f for f in os.listdir(raw_path)
                    if (f.endswith(".py") or f.endswith(".js"))
                    and not f.startswith("test_")
                    and not f.endswith(".test.js")]
        if not py_files:
            show_toast("No source files found in that folder.", kind="error")
            return
        abs_files = [os.path.join(raw_path, f) for f in py_files]
        _populate_project(raw_path, abs_files, abs_files[0])

    elif is_test_file:
        app.current_test_file = raw_path
        test_file_label.configure(text=f"tests: {raw_path}", text_color=COLOR_SUCCESS)
        _persist_test_file(raw_path)
        write_log(f"🧪 Test file set via drag-and-drop: {filename}")
        show_toast(f"Test file set: {filename}", kind="success")

    elif raw_path.endswith(".py") or raw_path.endswith(".js"):
        folder_path = os.path.dirname(raw_path)
        _populate_project(folder_path, [os.path.abspath(raw_path)], os.path.abspath(raw_path))

    else:
        show_toast("Drop a .py/.js file or a project folder.", kind="error")

def load_single_file():
    file_path = filedialog.askopenfilename(
        filetypes=[("Source files", "*.py *.js"), ("Python files", "*.py"), ("JavaScript files", "*.js")],
        title="Select a source file"
    )
    if file_path:
        folder_path = os.path.dirname(file_path)
        _populate_project(folder_path, [os.path.abspath(file_path)], os.path.abspath(file_path))

def load_test_file():
    file_path = filedialog.askopenfilename(
        filetypes=[
            ("All test files", "*.py *.js"),
            ("Python test files", "*.py"),
            ("JavaScript test files", "*.js")
        ],
        title="Select a test file"
    )
    if file_path:
        app.current_test_file = file_path
        test_file_label.configure(text=f"tests: {file_path}", text_color=COLOR_SUCCESS)
        _persist_test_file(file_path)

def filter_sidebar():
    query = sidebar_filter_var.get().strip().lower()
    for abs_path, btn in sidebar_buttons.items():
        filename = os.path.basename(abs_path).lower()
        if query in filename:
            btn.pack(fill="x", pady=1)
        else:
            btn.pack_forget()
            
load_folder_btn = ctk.CTkButton(editor_btn_row, text="📁  Load Folder",
                                 height=34,
                                 fg_color=COLOR_BTN_SECONDARY, hover_color=COLOR_BTN_SECONDARY_HOVER,
                                 corner_radius=8, text_color=COLOR_TEXT_PRIMARY,
                                 font=ctk.CTkFont(size=12, weight="bold"), command=load_folder)
load_folder_btn.pack(side="left", padx=(0, 8))

load_file_btn = ctk.CTkButton(editor_btn_row, text="📄  Load File",
                               height=34,
                               fg_color=COLOR_BTN_SECONDARY, hover_color=COLOR_BTN_SECONDARY_HOVER,
                               corner_radius=8, text_color=COLOR_TEXT_PRIMARY,
                               font=ctk.CTkFont(size=12, weight="bold"), command=load_single_file)
load_file_btn.pack(side="left", padx=(0, 8))

test_btn = ctk.CTkButton(editor_btn_row, text="🧪  Load Tests",
                          height=34,
                          fg_color=COLOR_BTN_SECONDARY, hover_color=COLOR_BTN_SECONDARY_HOVER,
                          corner_radius=8, text_color=COLOR_TEXT_PRIMARY,
                          font=ctk.CTkFont(size=12, weight="bold"), command=load_test_file)
test_btn.pack(side="left")

# ── RIGHT PANEL ──
right_panel = ctk.CTkFrame(app, corner_radius=0, fg_color=COLOR_PANEL_ALT)
right_panel.grid(row=1, column=1, sticky="nsew",padx=(1,0))

right_header = ctk.CTkFrame(right_panel, fg_color="transparent")
right_header.pack(fill="x", padx=16, pady=(16, 4))

right_title = ctk.CTkLabel(right_header, text="AGENT LOG",
                            font=ctk.CTkFont(family=FONT_MONO, size=11, weight="bold"),
                            text_color=COLOR_TEXT_MUTED)
right_title.pack(side="left")

# status badge (pill-shaped)
status_badge = ctk.CTkFrame(right_header, corner_radius=12, fg_color=COLOR_BTN_SECONDARY,
                             height=24)
status_badge.pack(side="right")
status_badge.pack_propagate(False)

status_label = ctk.CTkLabel(status_badge, text="●  idle",
                             font=ctk.CTkFont(family=FONT_MONO, size=11, weight="bold"),
                             text_color=COLOR_TEXT_MUTED)
status_label.pack(padx=10, pady=2)

test_file_label = ctk.CTkLabel(right_panel, text="tests: sample/test_code.py",
                                font=ctk.CTkFont(family=FONT_MONO, size=11),
                                text_color=COLOR_SUCCESS, anchor="w")
test_file_label.pack(anchor="w", padx=16, pady=(0, 8))

log_box = ctk.CTkTextbox(right_panel,
                          font=ctk.CTkFont(family=FONT_MONO, size=12),
                          fg_color=COLOR_BG, text_color=COLOR_TEXT_SECONDARY,
                          corner_radius=10, border_width=1, border_color=COLOR_BORDER)
log_box.pack(fill="both", expand=True, padx=16, pady=(0, 12))
log_box.configure(state="disabled")

diff_section = ctk.CTkFrame(right_panel, height=140, corner_radius=8,
                             fg_color=COLOR_BG, border_width=1, border_color=COLOR_BORDER)
diff_section.pack(side="bottom", fill="x", padx=16, pady=(0, 16))
diff_section.pack_propagate(False)

diff_title = ctk.CTkLabel(diff_section, text="CHANGES",
                           font=ctk.CTkFont(family=FONT_MONO, size=11, weight="bold"),
                           text_color=COLOR_TEXT_MUTED)
diff_title.pack(anchor="w", padx=12, pady=(8, 0))

diff_box = ctk.CTkTextbox(diff_section,
                           font=ctk.CTkFont(family=FONT_MONO, size=12),
                           fg_color=COLOR_BG, text_color=COLOR_TEXT_PRIMARY, corner_radius=0)
diff_box.pack(fill="both", expand=True, padx=12, pady=(4, 8))
diff_box.configure(state="disabled")

resize_grip_v = ctk.CTkFrame(right_panel, height=5, fg_color="transparent", cursor="sb_v_double_arrow")
resize_grip_v.pack(side="bottom", fill="x")

def _on_diff_drag(event):
    new_height = diff_section.winfo_height() - event.y
    new_height = max(80, min(new_height, 400))
    diff_section.configure(height=new_height)

resize_grip_v.bind("<B1-Motion>", _on_diff_drag)
resize_grip_v.bind("<Enter>", lambda e: resize_grip_v.configure(fg_color=COLOR_ACCENT))
resize_grip_v.bind("<Leave>", lambda e: resize_grip_v.configure(fg_color="transparent"))
# ── QUEUE + HEALING ──
log_queue = queue.Queue()

def write_log(message):
    log_queue.put(message)

active_toasts = []

def show_toast(message, kind="info", duration=3000):
    """
    Small auto-dismissing notification, stacked bottom-right.
    kind: "success" | "error" | "info"
    """
    accent = {"success": COLOR_SUCCESS, "error": COLOR_ERROR, "info": COLOR_TEXT_SECONDARY}.get(kind, COLOR_TEXT_SECONDARY)
    icon = {"success": "✅", "error": "⚠️", "info": "ℹ️"}.get(kind, "ℹ️")

    toast = ctk.CTkFrame(app, corner_radius=8, fg_color=COLOR_PANEL,
                          border_width=1, border_color=accent)
    label = ctk.CTkLabel(toast, text=f"{icon}  {message}",
                          font=ctk.CTkFont(size=12, weight="bold"),
                          text_color=COLOR_TEXT_PRIMARY, wraplength=280, justify="left")
    label.pack(padx=14, pady=10)

    active_toasts.append(toast)
    _reposition_toasts()
    toast.lift()

    def dismiss():
        if toast in active_toasts:
            active_toasts.remove(toast)
        toast.destroy()
        _reposition_toasts()

    toast.after(duration, dismiss)
    toast.bind("<Button-1>", lambda e: dismiss())
    label.bind("<Button-1>", lambda e: dismiss())

def _reposition_toasts():
    y_offset = 16
    for t in reversed(active_toasts):
        t.place(relx=1.0, rely=1.0, x=-16, y=-y_offset, anchor="se")
        t.update_idletasks()
        y_offset += t.winfo_height() + 8

def poll_queue():
    while not log_queue.empty():
        msg = log_queue.get()
        if msg.startswith("DIFF:REMOVED:"):
            line = msg.replace("DIFF:REMOVED:", "")
            diff_box.configure(state="normal")
            start = diff_box.index("end-1c")
            diff_box.insert("end", f"➖  {line}\n")
            diff_box._textbox.tag_add("diff_removed", start, "end-1c")
            diff_box._textbox.tag_configure("diff_removed", foreground=COLOR_ERROR)
            diff_box.configure(state="disabled")
        elif msg.startswith("DIFF:ADDED:"):
            line = msg.replace("DIFF:ADDED:", "")
            diff_box.configure(state="normal")
            start = diff_box.index("end-1c")
            diff_box.insert("end", f"➕  {line}\n")
            diff_box._textbox.tag_add("diff_added", start, "end-1c")
            diff_box._textbox.tag_configure("diff_added", foreground=COLOR_SUCCESS)
            diff_box.configure(state="disabled")
        elif msg.startswith("DIFF:HEADER:"):
            line = msg.replace("DIFF:HEADER:", "")
            diff_box.configure(state="normal")
            start = diff_box.index("end-1c")
            diff_box.insert("end", f"{line}\n")
            diff_box._textbox.tag_add("diff_header", start, "end-1c")
            diff_box._textbox.tag_configure("diff_header", foreground=COLOR_TEXT_MUTED)
            diff_box.configure(state="disabled")
        elif msg.startswith("ACTIVEFILE:"):
            path = msg.replace("ACTIVEFILE:", "")
            open_file_tab(path)
        else:
            log_box.configure(state="normal")
            log_box.insert("end", msg + "\n")
            log_box.see("end")
            log_box.configure(state="disabled")
    app.after(100, poll_queue)

def request_patch_approval(original_code, fixed_code, explanation, confidence):
    """
    Called from the background agent thread when confidence is low.
    Shows a modal approval dialog on the MAIN thread, and blocks the
    background thread until the user responds.
    """
    result_holder = {"approved": None}
    done_event = threading.Event()

    def show_dialog():
        win = ctk.CTkToplevel(app)
        win.title("Review Patch")
        win.geometry("600x500")
        win.configure(fg_color=COLOR_BG)
        win.grab_set()

        conf_color = COLOR_SUCCESS if confidence >= 70 else COLOR_WARNING
        ctk.CTkLabel(win, text=f"Confidence: {confidence}%",
                    font=ctk.CTkFont(family=FONT_MONO, size=14, weight="bold"),
                    text_color=conf_color).pack(anchor="w", padx=16, pady=(16, 4))

        ctk.CTkLabel(win, text=explanation or "No explanation provided.",
                     font=ctk.CTkFont(family=FONT_MONO, size=12),
                     text_color=COLOR_TEXT_SECONDARY, wraplength=560, justify="left").pack(
            anchor="w", padx=16, pady=(0, 8))

        diff_preview = ctk.CTkTextbox(win, font=ctk.CTkFont(family=FONT_MONO, size=11),
                                       fg_color=COLOR_PANEL_ALT, text_color=COLOR_TEXT_PRIMARY)
        diff_preview.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        diff_lines = list(difflib.unified_diff(
            original_code.splitlines(), fixed_code.splitlines(), fromfile="before", tofile="after", lineterm=""
        ))
        for line in diff_lines:
            if line.startswith("---") or line.startswith("+++"):
                continue
            diff_preview.insert("end", line + "\n")
        diff_preview.configure(state="disabled")

        btn_row = ctk.CTkFrame(win, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 16))

        def respond(approved):
            result_holder["approved"] = approved
            win.destroy()
            done_event.set()

        ctk.CTkButton(btn_row, text="✅ Approve", fg_color=COLOR_SUCCESS, text_color=COLOR_BG,
                      command=lambda: respond(True)).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row, text="🚫 Reject", fg_color=COLOR_ERROR, text_color=COLOR_BG,
                      command=lambda: respond(False)).pack(side="left")

    app.after(0, show_dialog)
    done_event.wait()
    return result_holder["approved"]

def run_healing():
    if not hasattr(app, "current_project_dir"):
        write_log("⚠️ No project loaded. Click Load File first.")
        show_toast("No project loaded — click Load Folder or Load File first.", kind="error")
        return

    test_file = getattr(app, "current_test_file", "sample")
    selected_model = model_var.get()

    try:
        max_retries = int(retry_var.get())
        max_retries = max(1, min(max_retries, 20))
    except ValueError:
        max_retries = 5
        retry_var.set("5")

    write_log("🟢 Greenline started...")
    app.settings["model"] = selected_model
    app.settings["max_retries"] = max_retries
    persist_settings(app.settings)

    if hasattr(app, "current_project_dir"):
        save_project_settings(app.current_project_dir, {
            "model": selected_model,
            "max_retries": max_retries
        })
    write_log(f"📁 Project: {app.current_project_dir}")
    write_log(f"🧪 Using test target: {test_file}")
    write_log(f"🧠 Model: {selected_model}  |  Max retries: {max_retries}")
    heal_btn.configure(state="disabled")
    status_label.configure(text="● healing...", text_color="#fac775")

    def agent_thread():
        from agent import run_agent
        result = run_agent(
            app.current_project_dir,
            test_file,
            max_retries=max_retries,
            model=selected_model,
            log_callback=write_log,
            approval_callback=request_patch_approval
        )

        save_session({
            "project_dir": app.current_project_dir,
            "test_target": test_file,
            "language": result.get("language", "unknown"),
            "model": selected_model,
            "max_retries": max_retries,
            "success": result["success"],
            "attempts": result["attempts"],
            "files_touched": result.get("files_touched", []),
            "duration_seconds": result.get("duration_seconds", 0),
            "backup_branch": result.get("backup_branch")
        })

# Reload whatever file was last touched, so the editor shows the final state
        try:
            open_file_tab(app.current_file)
        except Exception:
            pass

        if result["success"]:
            status_label.configure(text=f"● healed in {result['attempts']} attempt(s)", text_color="#5bcaa5")
            show_toast(f"Healed in {result['attempts']} attempt(s).", kind="success")
        else:
            status_label.configure(text=f"● failed after {result['attempts']} attempts", text_color="#f0997b")
            show_toast(f"Failed after {result['attempts']} attempts.", kind="error")

        write_log(f"📞 API calls this session: {get_call_count()}")

        heal_btn.configure(state="normal")

    threading.Thread(target=agent_thread, daemon=True).start()

def clear_logs():
    log_box.configure(state="normal")
    log_box.delete("1.0", "end")
    log_box.configure(state="disabled")
    
    diff_box.configure(state="normal")
    diff_box.delete("1.0", "end")
    diff_box.configure(state="disabled")
    
    status_label.configure(text="● idle", text_color="#666666")

def get_relative_path():
    """Returns app.current_file's path relative to the git repo root, plus the repo root itself."""
    abs_file = os.path.abspath(app.current_file)
    start_dir = os.path.dirname(abs_file)
    repo_root = get_repo_root(start_dir)

    if repo_root is None:
        # fallback — not actually a git repo
        return os.path.basename(app.current_file), start_dir

    repo_root = repo_root.replace("/", os.sep)
    rel_path = os.path.relpath(abs_file, repo_root).replace(os.sep, "/")
    return rel_path, repo_root

def open_history_window():
    if not hasattr(app, "current_file"):
        write_log("⚠️ No file loaded. Load a file first.")
        return

    file_name, repo_dir = get_relative_path()
    commits = get_commit_history(repo_dir, file_name)

    if not commits:
        write_log("ℹ️ No commit history found for this file.")
        return

    win = ctk.CTkToplevel(app)
    win.title("Commit History")
    win.geometry("480x400")
    win.configure(fg_color=COLOR_BG)

    ctk.CTkLabel(win, text="Select a version to restore",
                 font=ctk.CTkFont(family=FONT_MONO, size=13, weight="bold"),
                 text_color=COLOR_TEXT_PRIMARY).pack(anchor="w", padx=16, pady=(16, 8))

    scroll = ctk.CTkScrollableFrame(win, fg_color=COLOR_PANEL)
    scroll.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    for commit in commits:
        row = ctk.CTkFrame(scroll, fg_color=COLOR_PANEL_ALT, corner_radius=8)
        row.pack(fill="x", pady=4)

        label = ctk.CTkLabel(row, text=f"{commit['date']}  ·  {commit['message']}  ({commit['hash']})",
                              font=ctk.CTkFont(family=FONT_MONO, size=11),
                              text_color=COLOR_TEXT_SECONDARY, anchor="w")
        label.pack(side="left", padx=10, pady=8, fill="x", expand=True)

        restore_btn = ctk.CTkButton(row, text="Restore", width=80, height=28,
                                     fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
                                     corner_radius=6, font=ctk.CTkFont(size=11),
                                     command=lambda c=commit: do_restore(c["hash"], win))
        restore_btn.pack(side="right", padx=10, pady=8)

def do_restore(commit_hash, window):
    file_name, repo_dir = get_relative_path()
    success = restore_file_from_commit(repo_dir, file_name, commit_hash, app.current_file)

    if success:
        write_log(f"↩️ Restored to commit {commit_hash}")
        open_file_tab(app.current_file)
    else:
        write_log(f"⚠️ Restore failed for commit {commit_hash}")

    window.destroy()

def quick_undo():
    if not hasattr(app, "current_file"):
        write_log("⚠️ No file loaded.")
        return

    file_name, repo_dir = get_relative_path()
    commits = get_commit_history(repo_dir, file_name, limit=2)

    if len(commits) < 2:
        write_log("ℹ️ No earlier version to undo to.")
        return

    previous_commit = commits[1]["hash"]
    success = restore_file_from_commit(repo_dir, file_name, previous_commit, app.current_file)

    if success:
        write_log(f"↩️ Restored to commit {previous_commit}")
        open_file_tab(app.current_file)
    else:
        write_log("⚠️ Undo failed.")

def open_sessions_window():
    sessions = load_sessions()

    win = ctk.CTkToplevel(app)
    win.title("Session History")
    win.geometry("650x450")
    win.configure(fg_color=COLOR_BG)
    win.after(10, lambda: win.lift())
    win.after(10, lambda: win.focus_force())
    win.transient(app)

    ctk.CTkLabel(win, text="Past Healing Sessions",
                 font=ctk.CTkFont(family=FONT_MONO, size=14, weight="bold"),
                 text_color=COLOR_TEXT_PRIMARY).pack(anchor="w", padx=16, pady=(16, 8))

    if not sessions:
        ctk.CTkLabel(win, text="No sessions recorded yet.",
                     font=ctk.CTkFont(family=FONT_MONO, size=12),
                     text_color=COLOR_TEXT_MUTED).pack(padx=16, pady=20)
        return

    scroll = ctk.CTkScrollableFrame(win, fg_color=COLOR_PANEL)
    scroll.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    for s in sessions:
        card = ctk.CTkFrame(scroll, fg_color=COLOR_PANEL_ALT, corner_radius=8)
        card.pack(fill="x", pady=4)

        status_color = COLOR_SUCCESS if s["success"] else COLOR_ERROR
        status_text = "✅ Success" if s["success"] else "❌ Failed"

        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=12, pady=(8, 2))

        ctk.CTkLabel(top_row, text=os.path.basename(s["project_dir"]),
                     font=ctk.CTkFont(family=FONT_MONO, size=12, weight="bold"),
                     text_color=COLOR_TEXT_PRIMARY).pack(side="left")

        ctk.CTkLabel(top_row, text=status_text,
                     font=ctk.CTkFont(family=FONT_MONO, size=11, weight="bold"),
                     text_color=status_color).pack(side="right")

        detail_text = (
            f"{s['timestamp']}  ·  {s.get('language', '?')}  ·  {s.get('model', '?')}  ·  "
            f"{s['attempts']} attempt(s)  ·  {s.get('duration_seconds', 0)}s"
        )
        ctk.CTkLabel(card, text=detail_text,
                     font=ctk.CTkFont(family=FONT_MONO, size=10),
                     text_color=COLOR_TEXT_MUTED, anchor="w").pack(anchor="w", padx=12)

        files = s.get("files_touched", [])
        files_text = f"Files: {', '.join(files)}" if files else "Files: none"
        ctk.CTkLabel(card, text=files_text,
                     font=ctk.CTkFont(family=FONT_MONO, size=10),
                     text_color=COLOR_TEXT_SECONDARY, anchor="w").pack(anchor="w", padx=12, pady=(0, 8))

btn_row2 = ctk.CTkFrame(right_panel, fg_color="transparent")
btn_row2.pack(fill="x", padx=16, pady=(0, 16))

clear_btn = ctk.CTkButton(btn_row2, text="🗑  Clear",
                           height=36,
                           fg_color=COLOR_BTN_SECONDARY, hover_color=COLOR_BTN_SECONDARY_HOVER,
                           corner_radius=8, text_color=COLOR_TEXT_SECONDARY,
                           font=ctk.CTkFont(size=13), command=clear_logs)
clear_btn.pack(side="left")

history_btn = ctk.CTkButton(btn_row2, text="🕘  History",
                             height=36,
                             fg_color=COLOR_BTN_SECONDARY, hover_color=COLOR_BTN_SECONDARY_HOVER,
                             corner_radius=8, text_color=COLOR_TEXT_SECONDARY,
                             font=ctk.CTkFont(size=13), command=open_history_window)
history_btn.pack(side="left", padx=(8, 0))

undo_btn = ctk.CTkButton(btn_row2, text="↩️  Undo",
                          height=36,
                          fg_color=COLOR_BTN_SECONDARY, hover_color=COLOR_BTN_SECONDARY_HOVER,
                          corner_radius=8, text_color=COLOR_TEXT_SECONDARY,
                          font=ctk.CTkFont(size=13), command=quick_undo)
undo_btn.pack(side="left", padx=(8, 0))

sessions_btn = ctk.CTkButton(btn_row2, text="📋  Sessions",
                              height=36,
                              fg_color=COLOR_BTN_SECONDARY, hover_color=COLOR_BTN_SECONDARY_HOVER,
                              corner_radius=8, text_color=COLOR_TEXT_SECONDARY,
                              font=ctk.CTkFont(size=13), command=open_sessions_window)
sessions_btn.pack(side="left", padx=(8, 0))

heal_btn = ctk.CTkButton(btn_row2, text="⚡  Heal",
                          height=36, width=130,
                          fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
                          corner_radius=8,
                          font=ctk.CTkFont(size=13, weight="bold"), command=run_healing)
heal_btn.pack(side="right")

# ---- SHORTCUTS ---
def _shortcut_heal(event):
    if heal_btn.cget("state") == "normal":
        run_healing()

def _shortcut_undo(event):
    quick_undo()

app.bind("<Control-Return>", _shortcut_heal)
app.bind("<Control-z>", _shortcut_undo)

app.drop_target_register(DND_FILES)
app.dnd_bind("<<Drop>>", handle_drop)

last_dir = app.settings.get("last_project_dir")
if last_dir and os.path.isdir(last_dir):
    py_files = [f for f in os.listdir(last_dir)
                if (f.endswith(".py") or f.endswith(".js"))
                and not f.startswith("test_")
                and not f.endswith(".test.js")]
    if py_files:
        abs_files = [os.path.join(last_dir, f) for f in py_files]
        _populate_project(last_dir, abs_files, abs_files[0])
        write_log(f"📂 Restored last project: {last_dir}")
app.after(100, poll_queue)
app.mainloop()