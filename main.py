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

app = ctk.CTk()
app.title("Greenline")
app.geometry("1100x700")
app.minsize(900, 600)
app.iconbitmap(r"E:\greenline\logo.ico")
app.configure(fg_color=COLOR_BG)
app.grid_rowconfigure(0, weight=0)   # top bar — fixed
app.grid_rowconfigure(1, weight=1)   # panels — expandable
app.grid_rowconfigure(2, weight=0)   # diff — fixed
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

# ── LEFT PANEL ──
left_panel = ctk.CTkFrame(app, corner_radius=0, fg_color=COLOR_PANEL,
                           border_width=0)
left_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 1))

left_header = ctk.CTkFrame(left_panel, fg_color="transparent")
left_header.pack(fill="x", padx=16, pady=(16, 8))

left_title = ctk.CTkLabel(left_header, text="No file loaded",
                           font=ctk.CTkFont(family=FONT_MONO, size=13, weight="bold"),
                           text_color=COLOR_TEXT_SECONDARY, anchor="w")
left_title.pack(side="left", fill="x", expand=True)

code_box = ctk.CTkTextbox(left_panel,
                           font=ctk.CTkFont(family=FONT_MONO, size=13),
                           fg_color=COLOR_BG, text_color=COLOR_TEXT_PRIMARY,
                           corner_radius=10, wrap="none",
                           border_width=1, border_color=COLOR_BORDER)
code_box.pack(fill="both", expand=True, padx=16, pady=(0, 12))

btn_row = ctk.CTkFrame(left_panel, fg_color="transparent")
btn_row.pack(fill="x", padx=16, pady=(0, 16))

def load_file():
    file_path = filedialog.askopenfilename(filetypes=[("Python files", "*.py")])
    if file_path:
        with open(file_path, "r",encoding="utf-8") as f:
            content = f.read()
        code_box.delete("1.0", "end")
        code_box.insert("1.0", content)
        highlight_python(code_box, content)
        left_title.configure(text=file_path)
        app.current_file = file_path

def load_test_file():
    file_path = filedialog.askopenfilename(
        filetypes=[("Python test files", "*.py")],
        title="Select a test file"
    )
    if file_path:
        app.current_test_file = file_path
        test_file_label.configure(text=f"tests: {file_path}")

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
                                text_color=COLOR_TEXT_MUTED, anchor="w")
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
diff_panel.grid(row=2, column=0, columnspan=2, sticky="ew")
diff_panel.grid_propagate(False)

diff_border = ctk.CTkFrame(app, height=1, corner_radius=0, fg_color=COLOR_BORDER)
diff_border.grid(row=2, column=0, columnspan=2, sticky="new")

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
        else:
            log_box.configure(state="normal")
            log_box.insert("end", msg + "\n")
            log_box.see("end")
            log_box.configure(state="disabled")
    app.after(100, poll_queue)

def run_healing():
    if not hasattr(app, "current_file"):
        write_log("⚠️ No file loaded. Click Load File first.")
        return

    test_file = getattr(app, "current_test_file", "sample/test_code.py")

    write_log("🟢 Greenline started...")
    write_log(f"🧪 Using test file: {test_file}")
    heal_btn.configure(state="disabled")
    status_label.configure(text="● healing...", text_color="#fac775")

    def agent_thread():
        from agent import run_agent
        
        result = run_agent(app.current_file, test_file, log_callback=write_log)
        
        with open(app.current_file, "r",encoding="utf-8") as f:
            healed_code = f.read()
        code_box.delete("1.0", "end")
        code_box.insert("1.0", healed_code)
        highlight_python(code_box, healed_code)  
        
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
        with open(app.current_file, "r", encoding="utf-8") as f:
            content = f.read()
        code_box.delete("1.0", "end")
        code_box.insert("1.0", content)
        highlight_python(code_box, content)
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
        write_log(f"↩️ Quick undo → restored to {previous_commit}")
        with open(app.current_file, "r", encoding="utf-8") as f:
            content = f.read()
        code_box.delete("1.0", "end")
        code_box.insert("1.0", content)
        highlight_python(code_box, content)
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