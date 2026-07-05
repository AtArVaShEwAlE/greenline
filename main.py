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

app = ctk.CTk()
app.title("Greenline")
app.geometry("1100x700")
app.minsize(900, 600)
app.iconbitmap(r"E:\greenline\logo.ico")
app.configure(fg_color=COLOR_BG)
app.grid_rowconfigure(0, weight=0)   # top bar — fixed
app.grid_rowconfigure(1, weight=0)   # settings bar — fixed (NEW)
app.grid_rowconfigure(2, weight=1)   # panels — expandable
app.grid_rowconfigure(3, weight=0)
app.grid_columnconfigure(0, weight=3)
app.grid_columnconfigure(1, weight=2)

# Top bar
top_bar = ctk.CTkFrame(app, height=56, corner_radius=0, fg_color=COLOR_BG, border_width=0)
top_bar.grid(row=0, column=0, columnspan=2, sticky="ew")
top_bar.grid_propagate(False)

wm_image = CTkImage(light_image=Image.open("wordmark.png"),
                    dark_image=Image.open("wordmark.png"),
                    size=(173, 32))
wordmark_label = ctk.CTkLabel(top_bar, image=wm_image, text="")
wordmark_label.pack(side="left", padx=20, pady=10)

# subtle separator line under the top bar
top_bar_border = ctk.CTkFrame(app, height=1, corner_radius=0, fg_color=COLOR_BORDER)
top_bar_border.grid(row=0, column=0, columnspan=2, sticky="sew")

# ── SETTINGS BAR ──
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]

app.settings = {
    "model": GROQ_MODELS[0],
    "max_retries": 5
}

settings_bar = ctk.CTkFrame(app, height=48, corner_radius=0, fg_color=COLOR_PANEL_ALT)
settings_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
settings_bar.grid_propagate(False)

settings_border = ctk.CTkFrame(app, height=1, corner_radius=0, fg_color=COLOR_BORDER)
settings_border.grid(row=1, column=0, columnspan=2, sticky="sew")

ctk.CTkLabel(settings_bar, text="Model", font=ctk.CTkFont(family=FONT_MONO, size=11),
             text_color=COLOR_TEXT_MUTED).pack(side="left", padx=(20, 8), pady=10)

model_var = ctk.StringVar(value=GROQ_MODELS[0])
model_menu = ctk.CTkOptionMenu(settings_bar, values=GROQ_MODELS, variable=model_var,
                                width=200, height=28,
                                fg_color=COLOR_BTN_SECONDARY, button_color=COLOR_ACCENT,
                                button_hover_color=COLOR_ACCENT_HOVER,
                                font=ctk.CTkFont(family=FONT_MONO, size=11))
model_menu.pack(side="left", padx=(0, 24), pady=10)

ctk.CTkLabel(settings_bar, text="Max retries", font=ctk.CTkFont(family=FONT_MONO, size=11),
             text_color=COLOR_TEXT_MUTED).pack(side="left", padx=(0, 8), pady=10)

retry_var = ctk.StringVar(value="5")
retry_entry = ctk.CTkEntry(settings_bar, textvariable=retry_var, width=50, height=28,
                            fg_color=COLOR_PANEL, border_color=COLOR_BORDER,
                            text_color=COLOR_TEXT_PRIMARY,
                            font=ctk.CTkFont(family=FONT_MONO, size=11))
retry_entry.pack(side="left", pady=10)

def open_settings_window():
    win = ctk.CTkToplevel(app)
    win.title("Settings")
    win.geometry("380x280")
    win.configure(fg_color=COLOR_BG)

    ctk.CTkLabel(win, text="Settings",
                 font=ctk.CTkFont(family=FONT_MONO, size=15, weight="bold"),
                 text_color=COLOR_TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(20, 16))

    # Model selector
    ctk.CTkLabel(win, text="Model", font=ctk.CTkFont(family=FONT_MONO, size=12),
                 text_color=COLOR_TEXT_SECONDARY).pack(anchor="w", padx=20)

    model_var = ctk.StringVar(value=app.settings["model"])
    model_menu = ctk.CTkOptionMenu(win, values=GROQ_MODELS, variable=model_var,
                                    fg_color=COLOR_BTN_SECONDARY, button_color=COLOR_ACCENT,
                                    button_hover_color=COLOR_ACCENT_HOVER)
    model_menu.pack(anchor="w", padx=20, pady=(4, 16), fill="x")

    # Retry limit
    ctk.CTkLabel(win, text="Max retries", font=ctk.CTkFont(family=FONT_MONO, size=12),
                 text_color=COLOR_TEXT_SECONDARY).pack(anchor="w", padx=20)

    retry_var = ctk.StringVar(value=str(app.settings["max_retries"]))
    retry_entry = ctk.CTkEntry(win, textvariable=retry_var,
                                fg_color=COLOR_PANEL, border_color=COLOR_BORDER,
                                text_color=COLOR_TEXT_PRIMARY)
    retry_entry.pack(anchor="w", padx=20, pady=(4, 20), fill="x")

    def save_settings():
        app.settings["model"] = model_var.get()
        try:
            retries = int(retry_var.get())
            app.settings["max_retries"] = max(1, min(retries, 20))  # clamp 1–20
        except ValueError:
            app.settings["max_retries"] = 5  # fallback if user typed garbage

        write_log(f"⚙️ Settings updated — model: {app.settings['model']}, "
                   f"max retries: {app.settings['max_retries']}")
        win.destroy()

    save_btn = ctk.CTkButton(win, text="Save", height=36,
                              fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
                              corner_radius=8, font=ctk.CTkFont(size=13, weight="bold"),
                              command=save_settings)
    save_btn.pack(padx=20, pady=(0, 20), fill="x")

# ── LEFT PANEL ──
left_panel = ctk.CTkFrame(app, corner_radius=0, fg_color=COLOR_PANEL, border_width=0)
left_panel.grid(row=2, column=0, sticky="nsew", padx=(0, 1))

left_header = ctk.CTkFrame(left_panel, fg_color="transparent")
left_header.pack(fill="x", padx=16, pady=(16, 8))

left_title = ctk.CTkLabel(left_header, text="No project loaded",
                           font=ctk.CTkFont(family=FONT_MONO, size=13, weight="bold"),
                           text_color=COLOR_TEXT_SECONDARY, anchor="w")
left_title.pack(side="left", fill="x", expand=True)

# ── BODY: sidebar (left) + tabs/editor (right) ──
left_body = ctk.CTkFrame(left_panel, fg_color="transparent")
left_body.pack(fill="both", expand=True, padx=16, pady=(0, 8))

# Sidebar (file explorer)
sidebar = ctk.CTkFrame(left_body, width=150, corner_radius=8, fg_color=COLOR_SIDEBAR,
                        border_width=1, border_color=COLOR_BORDER)
sidebar.pack(side="left", fill="y", padx=(0, 8))
sidebar.pack_propagate(False)

ctk.CTkLabel(sidebar, text="EXPLORER", font=ctk.CTkFont(family=FONT_MONO, size=10, weight="bold"),
             text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=10, pady=(10, 4))

sidebar_list = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
sidebar_list.pack(fill="both", expand=True, padx=4, pady=(0, 4))

# Editor area (tabs + line numbers + code)
editor_area = ctk.CTkFrame(left_body, fg_color="transparent")
editor_area.pack(side="left", fill="both", expand=True)

tab_bar = ctk.CTkFrame(editor_area, height=34, fg_color="transparent")
tab_bar.pack(fill="x", pady=(0, 4))
tab_bar.pack_propagate(False)

code_row = ctk.CTkFrame(editor_area, fg_color="transparent")
code_row.pack(fill="both", expand=True)

line_numbers = tk.Text(code_row, width=4, padx=6, pady=10,
                        font=(FONT_MONO, 13), bg=COLOR_BG, fg=COLOR_LINE_NUMBERS,
                        bd=0, highlightthickness=0, wrap="none", state="disabled")
line_numbers.pack(side="left", fill="y")

code_box = ctk.CTkTextbox(code_row,
                           font=ctk.CTkFont(family=FONT_MONO, size=13),
                           fg_color=COLOR_BG, text_color=COLOR_TEXT_PRIMARY,
                           corner_radius=10, wrap="none",
                           border_width=1, border_color=COLOR_BORDER)
code_box.pack(side="left", fill="both", expand=True)

btn_row = ctk.CTkFrame(left_panel, fg_color="transparent")
btn_row.pack(fill="x", padx=16, pady=(0, 16))

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
        btn.configure(fg_color=COLOR_TAB_ACTIVE if is_active else COLOR_TAB_INACTIVE,
                      text_color=COLOR_TEXT_PRIMARY if is_active else COLOR_TEXT_MUTED)
    for path, btn in sidebar_buttons.items():
        is_active = (path == file_path)
        btn.configure(fg_color=COLOR_TAB_ACTIVE if is_active else "transparent",
                      text_color=COLOR_TEXT_PRIMARY if is_active else COLOR_TEXT_SECONDARY)

def load_file():
    folder_path = filedialog.askdirectory(title="Select project folder")
    if folder_path:
        py_files = [f for f in os.listdir(folder_path)
                    if f.endswith(".py") and not f.startswith("test_")]

        if not py_files:
            write_log("⚠️ No source .py files found in that folder.")
            return

        for widget in tab_bar.winfo_children():
            widget.destroy()
        for widget in sidebar_list.winfo_children():
            widget.destroy()
        tab_buttons.clear()
        sidebar_buttons.clear()

        abs_files = [os.path.join(folder_path, f) for f in py_files]
        app.current_project_dir = folder_path
        app.loaded_files = abs_files

        for abs_path in abs_files:
            file_label = os.path.basename(abs_path)

            tab_btn = ctk.CTkButton(tab_bar, text=file_label, height=30,
                                     fg_color=COLOR_TAB_INACTIVE, text_color=COLOR_TEXT_MUTED,
                                     hover_color=COLOR_BTN_SECONDARY_HOVER, corner_radius=6,
                                     font=ctk.CTkFont(family=FONT_MONO, size=11),
                                     command=lambda p=abs_path: open_file_tab(p))
            tab_btn.pack(side="left", padx=(0, 4))
            tab_buttons[abs_path] = tab_btn

            side_btn = ctk.CTkButton(sidebar_list, text=f"🐍 {file_label}", height=26,
                                      fg_color="transparent", text_color=COLOR_TEXT_SECONDARY,
                                      hover_color=COLOR_BTN_SECONDARY_HOVER, corner_radius=6,
                                      anchor="w", font=ctk.CTkFont(family=FONT_MONO, size=11),
                                      command=lambda p=abs_path: open_file_tab(p))
            side_btn.pack(fill="x", pady=1)
            sidebar_buttons[abs_path] = side_btn

        left_title.configure(text=f"{folder_path}  ({len(py_files)} file(s))")
        open_file_tab(abs_files[0])

def load_test_file():
    file_path = filedialog.askopenfilename(
        filetypes=[("Python test files", "*.py")],
        title="Select a test file"
    )
    if file_path:
        app.current_test_file = file_path
        test_file_label.configure(text=f"tests: {file_path}", text_color=COLOR_SUCCESS)

load_btn = ctk.CTkButton(btn_row, text="📂  Load File",
                          height=34,
                          fg_color=COLOR_BTN_SECONDARY, hover_color=COLOR_BTN_SECONDARY_HOVER,
                          corner_radius=8, text_color=COLOR_TEXT_PRIMARY,
                          font=ctk.CTkFont(size=12, weight="bold"), command=load_file)
load_btn.pack(side="left", padx=(0, 8))

test_btn = ctk.CTkButton(btn_row, text="🧪  Load Tests",
                          height=34,
                          fg_color=COLOR_BTN_SECONDARY, hover_color=COLOR_BTN_SECONDARY_HOVER,
                          corner_radius=8, text_color=COLOR_TEXT_PRIMARY,
                          font=ctk.CTkFont(size=12, weight="bold"), command=load_test_file)
test_btn.pack(side="left")

# ── RIGHT PANEL ──
right_panel = ctk.CTkFrame(app, corner_radius=0, fg_color=COLOR_PANEL_ALT)
right_panel.grid(row=2, column=1, sticky="nsew",padx=(1,0))

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

# ── DIFF PANEL ──
diff_panel = ctk.CTkFrame(app, height=130, corner_radius=0, fg_color=COLOR_BG,
                           border_width=0)
diff_panel.grid(row=3, column=0, columnspan=2, sticky="ew")
diff_panel.grid_propagate(False)

diff_border = ctk.CTkFrame(app, height=1, corner_radius=0, fg_color=COLOR_BORDER)
diff_border.grid(row=3, column=0, columnspan=2, sticky="new")

diff_title = ctk.CTkLabel(diff_panel, text="CHANGES",
                           font=ctk.CTkFont(family=FONT_MONO, size=11, weight="bold"),
                           text_color=COLOR_TEXT_MUTED)
diff_title.pack(anchor="w", padx=20, pady=(10, 0))

diff_box = ctk.CTkTextbox(diff_panel,
                           font=ctk.CTkFont(family=FONT_MONO, size=12),
                           fg_color=COLOR_BG, text_color=COLOR_TEXT_PRIMARY,
                           corner_radius=0)
diff_box.pack(fill="both", expand=True, padx=20, pady=(4, 10))
diff_box.configure(state="disabled")

# ── QUEUE + HEALING ──
log_queue = queue.Queue()

def write_log(message):
    log_queue.put(message)

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

def run_healing():
    if not hasattr(app, "current_project_dir"):
        write_log("⚠️ No project loaded. Click Load File first.")
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
            log_callback=write_log
        )

        # Reload whatever file was last touched, so the editor shows the final state
        try:
            open_file_tab(app.current_file)
        except Exception:
            pass

        if result["success"]:
            status_label.configure(text=f"● healed in {result['attempts']} attempt(s)", text_color="#5bcaa5")
        else:
            status_label.configure(text=f"● failed after {result['attempts']} attempts", text_color="#f0997b")

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

heal_btn = ctk.CTkButton(btn_row2, text="⚡  Heal",
                          height=36, width=130,
                          fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
                          corner_radius=8,
                          font=ctk.CTkFont(size=13, weight="bold"), command=run_healing)
heal_btn.pack(side="right")

app.after(100, poll_queue)
app.mainloop()