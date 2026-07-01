import ctypes
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('greenline.app.v1')
import customtkinter as ctk
from tkinter import filedialog
import threading
import queue
from PIL import Image
from customtkinter import CTkImage

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

app = ctk.CTk()
app.title("Greenline")
app.geometry("1000x650")
app.iconbitmap(r"E:\greenline\logo.ico")
app.grid_rowconfigure(0, weight=0)   # top bar — fixed
app.grid_rowconfigure(1, weight=1)   # panels — expandable
app.grid_rowconfigure(2, weight=0)   # diff — fixed
app.grid_columnconfigure(0, weight=3)
app.grid_columnconfigure(1, weight=2)

# Top bar
top_bar = ctk.CTkFrame(app, height=52, corner_radius=0, fg_color="#0a0a0e")
top_bar.grid(row=0, column=0, columnspan=2, sticky="ew")
top_bar.grid_propagate(False)

# Wordmark image
wm_image = CTkImage(light_image=Image.open("wordmark.png"),
                    dark_image=Image.open("wordmark.png"),
                    size=(173, 32))  # adjust size to fit your wordmark
wordmark_label = ctk.CTkLabel(top_bar, image=wm_image, text="")
wordmark_label.pack(side="left", padx=16, pady=8)
# ── LEFT PANEL ──
left_panel = ctk.CTkFrame(app, corner_radius=0)
left_panel.grid(row=1, column=0, sticky="nsew")

left_title = ctk.CTkLabel(left_panel, text="buggy_code.py",
                           font=ctk.CTkFont(family="Consolas", size=12),
                           text_color="#999999")
left_title.pack(anchor="w", padx=12, pady=(10, 0))

code_box = ctk.CTkTextbox(left_panel,
                           font=ctk.CTkFont(family="Consolas", size=13),
                           fg_color="#111114", text_color="#c8c8d0",
                           corner_radius=8, wrap="none")
code_box.pack(fill="both", expand=True, padx=10, pady=10)

def load_file():
    file_path = filedialog.askopenfilename(filetypes=[("Python files", "*.py")])
    if file_path:
        with open(file_path, "r") as f:
            content = f.read()
        code_box.delete("1.0", "end")
        code_box.insert("1.0", content)
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

load_btn = ctk.CTkButton(left_panel, text="📂 Load File",
                          width=120, height=30,
                          fg_color="#2a2a32", hover_color="#3a3a42",
                          font=ctk.CTkFont(size=12), command=load_file)
load_btn.pack(anchor="w", padx=10, pady=(0, 10))
test_btn = ctk.CTkButton(left_panel, text="🧪 Load Tests",
                          width=120, height=30,
                          fg_color="#2a2a32", hover_color="#3a3a42",
                          font=ctk.CTkFont(size=12), command=load_test_file)
test_btn.pack(side="left", anchor="w", padx=(0, 10), pady=(0, 10))

# ── RIGHT PANEL ──
right_panel = ctk.CTkFrame(app, corner_radius=0, fg_color="#0e0e12")
right_panel.grid(row=1, column=1, sticky="nsew")

right_title = ctk.CTkLabel(right_panel, text="agent log",
                            font=ctk.CTkFont(family="Consolas", size=12),
                            text_color="#555555")
right_title.pack(anchor="w", padx=12, pady=(10, 0))

test_file_label = ctk.CTkLabel(right_panel, text="tests: sample/test_code.py",
                                font=ctk.CTkFont(family="Consolas", size=11),
                                text_color="#6a6a78")
test_file_label.pack(anchor="w", padx=12, pady=(0, 6))


log_box = ctk.CTkTextbox(right_panel,
                          font=ctk.CTkFont(family="Consolas", size=12),
                          fg_color="#0a0a0e", text_color="#8a8a98",
                          corner_radius=8)
log_box.pack(fill="both", expand=True, padx=10, pady=10)
log_box.configure(state="disabled")

# ── DIFF PANEL ──
diff_panel = ctk.CTkFrame(app, height=160, corner_radius=0, fg_color="#0d1a0d")
diff_panel.grid(row=2, column=0, columnspan=2, sticky="ew")
diff_panel.grid_propagate(False)

diff_title = ctk.CTkLabel(diff_panel, text="📋 changes",
                           font=ctk.CTkFont(family="Consolas", size=11),
                           text_color="#3a6a3a")
diff_title.pack(anchor="w", padx=12, pady=(6, 0))

diff_box = ctk.CTkTextbox(diff_panel,
                           font=ctk.CTkFont(family="Consolas", size=12),
                           fg_color="#0d1a0d", text_color="#cccccc",
                           corner_radius=0)
diff_box.pack(fill="both", expand=True, padx=10, pady=(4, 8))
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
            diff_box.insert("end", f"➖  {line}\n")
            diff_box.configure(state="disabled")
        elif msg.startswith("DIFF:ADDED:"):
            line = msg.replace("DIFF:ADDED:", "")
            diff_box.configure(state="normal")
            diff_box.insert("end", f"➕  {line}\n")
            diff_box.configure(state="disabled")
        elif msg.startswith("DIFF:HEADER:"):
            line = msg.replace("DIFF:HEADER:", "")
            diff_box.configure(state="normal")
            diff_box.insert("end", f"{line}\n")
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
        status_label.configure(text="● healing...", text_color="#fac775")
        
        result = run_agent(app.current_file, "sample/test_code.py", log_callback=write_log)
        
        with open(app.current_file, "r") as f:
            healed_code = f.read()
        code_box.delete("1.0", "end")
        code_box.insert("1.0", healed_code)
        
        if result["success"]:
            status_label.configure(text=f"● healed in {result['attempts']} attempt(s)", text_color="#5bcaa5")
        else:
            status_label.configure(text=f"● failed after {result['attempts']} attempts", text_color="#f0997b")
        
        heal_btn.configure(state="normal")

    threading.Thread(target=agent_thread, daemon=True).start()


status_label = ctk.CTkLabel(right_panel, text="● idle",
                             font=ctk.CTkFont(family="Consolas", size=12),
                             text_color="#666666")
status_label.pack(anchor="w", padx=10, pady=(0, 4))

def clear_logs():
    log_box.configure(state="normal")
    log_box.delete("1.0", "end")
    log_box.configure(state="disabled")
    
    diff_box.configure(state="normal")
    diff_box.delete("1.0", "end")
    diff_box.configure(state="disabled")
    
    status_label.configure(text="● idle", text_color="#666666")

clear_btn = ctk.CTkButton(right_panel, text="🗑 Clear",
                           width=90, height=34,
                           fg_color="#2a2a32",
                           hover_color="#3a3a42",
                           font=ctk.CTkFont(size=13),
                           command=clear_logs)
clear_btn.pack(side="left", padx=10, pady=(0, 10))


heal_btn = ctk.CTkButton(right_panel, text="⚡ Heal",
                          width=120, height=34,
                          fg_color="#534AB7", hover_color="#6258c4",
                          font=ctk.CTkFont(size=13, weight="bold"),
                          command=run_healing)
heal_btn.pack(anchor="e", padx=10, pady=(0, 10))

app.after(100, poll_queue)
app.mainloop()