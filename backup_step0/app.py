import tkinter as tk
from tkinter import ttk, font
import threading
import time
import queue
import psutil
import win32gui
import win32process
import pygetwindow as gw
import os
import json

# --- 전역 변수 ---
overlay_queue = queue.Queue()
tracker_thread = None
stop_event = None
CONFIG_FILE = 'jobs_config.json'

# --- 핵심 로직: 창 추적 (변경 없음) ---
def track_windows_logic(process_name, queue, event):
    # (이전 코드와 동일)
    while not event.is_set():
        try:
            target_pids = {p.info['pid'] for p in psutil.process_iter(['pid', 'name']) if p.info['name'].lower() == process_name.lower()}
            all_window_info = []
            if target_pids:
                pid_to_hwnds = {}
                def callback(hwnd, _):
                    if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                        _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                        if found_pid in pid_to_hwnds: pid_to_hwnds[found_pid].append(hwnd)
                        else: pid_to_hwnds[found_pid] = [hwnd]
                    return True
                win32gui.EnumWindows(callback, None)
                found_hwnds = []
                for pid in target_pids:
                    if pid in pid_to_hwnds: found_hwnds.extend(pid_to_hwnds[pid])
                for hwnd in found_hwnds:
                    try:
                        window = gw.Win32Window(hwnd)
                        if not window.isMinimized:
                            all_window_info.append({'rect': window.box, 'title': window.title})
                    except gw.PyGetWindowException: continue
            queue.put(all_window_info)
        except Exception: queue.put([])
        if event.wait(0.5): break

# --- 시각화: 투명 오버레이 (변경 없음) ---
class VisualOverlay:
    # (이전 코드와 동일)
    def __init__(self, root):
        self.root = root; self.root.attributes('-fullscreen', True); self.root.attributes('-topmost', True)
        self.root.attributes('-transparentcolor', 'black'); self.root.config(bg='black'); self.root.overrideredirect(True)
        self.canvas = tk.Canvas(self.root, bg='black', highlightthickness=0); self.canvas.pack(fill=tk.BOTH, expand=True)
        self.update_overlay()
    def update_overlay(self):
        try:
            list_of_window_info = overlay_queue.get_nowait()
            self.canvas.delete("all")
            for info in list_of_window_info:
                x, y, width, height = info['rect']; x2, y2 = x + width, y + height
                self.canvas.create_rectangle(x, y, x2, y2, outline="#00FF00", width=3)
        except queue.Empty: pass
        self.root.after(100, self.update_overlay)

# --- UI 애플리케이션 ---
class AutomationUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Automation Project UI (v5.0)")
        self.root.geometry("1024x768")
        self.overlay_root = None
        self.all_processes = []
        self.saved_jobs = {}

        self.load_jobs()
        self.setup_styles()
        self.root.configure(bg=self.BG_COLOR)
        main_frame = ttk.Frame(root, style='Main.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        main_frame.grid_columnconfigure(1, weight=1); main_frame.grid_rowconfigure(0, weight=1)
        left_panel = self.create_left_panel(main_frame)
        left_panel.grid(row=0, column=0, sticky="nsw", padx=(0, 10))
        right_panel = self.create_right_panel(main_frame)
        right_panel.grid(row=0, column=1, sticky="nsew")
        
        self.log("Application UI Initialized.")
        if self.saved_jobs:
            self.log(f"Loaded {len(self.saved_jobs)} saved job(s) from {CONFIG_FILE}")
        self.refresh_process_list()

    def setup_styles(self):
        # 스타일 설정 (Combobox 관련 스타일 제거)
        self.BG_COLOR = "#212121"; self.FRAME_BG = "#2c2c2c"; self.TEXT_COLOR = "#f0f0f0"
        self.BUTTON_BG = "#4a4a4a"; self.LISTBOX_BG = "#3c3c3c"; self.ENTRY_BG = "#333333"
        self.LISTBOX_SELECT_BG = "#005a9e"; style = ttk.Style(); style.theme_use('clam')
        default_font = font.nametofont("TkDefaultFont"); default_font.configure(family="Segoe UI", size=11)
        style.configure('.', background=self.BG_COLOR, foreground=self.TEXT_COLOR, font=default_font)
        style.configure('TFrame', background=self.BG_COLOR); style.configure('Main.TFrame', background=self.BG_COLOR)
        style.configure('Control.TFrame', background=self.FRAME_BG)
        style.configure('TLabel', background=self.FRAME_BG, foreground=self.TEXT_COLOR, padding=5)
        style.configure('Bold.TLabel', background=self.FRAME_BG, foreground=self.TEXT_COLOR, font=("Segoe UI", 11, "bold"))
        style.configure('TLabelframe', background=self.FRAME_BG, borderwidth=1, relief="solid")
        style.configure('TLabelframe.Label', background=self.FRAME_BG, foreground=self.TEXT_COLOR, font=("Segoe UI", 12, "bold"))
        style.configure('TButton', background=self.BUTTON_BG, foreground=self.TEXT_COLOR, borderwidth=1, padding=(10, 5))
        style.map('TButton', background=[('active', '#6a6a6a')])
        style.configure('TEntry', fieldbackground=self.ENTRY_BG, foreground=self.TEXT_COLOR, borderwidth=1, relief='solid', insertcolor=self.TEXT_COLOR)
        style.configure('TCheckbutton', background=self.FRAME_BG, foreground=self.TEXT_COLOR)
        # Condition Combobox 스타일은 유지
        self.root.option_add('*TCombobox*Listbox.background', self.LISTBOX_BG)
        self.root.option_add('*TCombobox*Listbox.foreground', self.TEXT_COLOR)
        style.configure('TCombobox', fieldbackground=self.ENTRY_BG, foreground=self.TEXT_COLOR, selectbackground=self.LISTBOX_BG, borderwidth=1, relief='solid')


    def create_left_panel(self, parent):
        left_frame = ttk.Frame(parent, style='TFrame')
        left_frame.rowconfigure(2, weight=1)

        # <<< 수정: 1. 상단: 저장된 Job 목록 (Listbox로 변경)
        load_job_frame = ttk.LabelFrame(left_frame, text="Saved Jobs")
        load_job_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.saved_jobs_listbox = tk.Listbox(load_job_frame, bg=self.LISTBOX_BG, fg=self.TEXT_COLOR,
                                             selectbackground=self.LISTBOX_SELECT_BG, height=5,
                                             borderwidth=0, highlightthickness=0)
        self.saved_jobs_listbox.pack(fill=tk.X, expand=True, padx=5, pady=5)
        self.saved_jobs_listbox.bind('<<ListboxSelect>>', self.on_saved_job_select)
        self.update_saved_jobs_list()

        # 2. 중단: Job Control
        control_frame = ttk.LabelFrame(left_frame, text="Job Control")
        control_frame.grid(row=1, column=0, sticky="ew", pady=10)
        control_btn_frame = ttk.Frame(control_frame, style='Control.TFrame')
        control_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        self.start_button = ttk.Button(control_btn_frame, text="Start Selected Job", command=self.start_tracking)
        self.start_button.pack(side=tk.LEFT, expand=True, padx=(0, 5))
        self.stop_button = ttk.Button(control_btn_frame, text="Stop Selected Job", command=self.stop_tracking, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, expand=True, padx=(5, 0))
        
        # 3. 하단: Find 및 List
        process_list_frame = ttk.LabelFrame(left_frame, text="Processes & Jobs")
        process_list_frame.grid(row=2, column=0, sticky="nsew", pady=(10, 0))
        process_list_frame.rowconfigure(1, weight=1); process_list_frame.columnconfigure(0, weight=1)
        find_frame = ttk.Frame(process_list_frame, style='Control.TFrame')
        find_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        find_frame.columnconfigure(1, weight=1)
        ttk.Label(find_frame, text="Find:", style='Bold.TLabel').grid(row=0, column=0)
        self.find_entry = ttk.Entry(find_frame)
        self.find_entry.grid(row=0, column=1, sticky="ew", padx=5)
        self.find_entry.bind("<KeyRelease>", self.filter_processes)
        self.jobs_listbox = tk.Listbox(process_list_frame, bg=self.LISTBOX_BG, fg=self.TEXT_COLOR,
                                       selectbackground=self.LISTBOX_SELECT_BG,
                                       borderwidth=0, highlightthickness=0)
        self.jobs_listbox.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.jobs_listbox.bind('<<ListboxSelect>>', self.on_process_select)
        return left_frame
        
    def create_right_panel(self, parent):
        # (이전 코드와 동일)
        right_frame = ttk.Frame(parent, style='TFrame')
        right_frame.grid_rowconfigure(3, weight=1); right_frame.grid_columnconfigure(0, weight=1)
        config_frame = ttk.LabelFrame(right_frame, text="Job Configuration")
        config_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10)); config_frame.columnconfigure(1, weight=1)
        ttk.Label(config_frame, text="Job Name:", style='Bold.TLabel').grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.job_name_entry = ttk.Entry(config_frame); self.job_name_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        ttk.Label(config_frame, text="Process Name:", style='Bold.TLabel').grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.process_name_entry = ttk.Entry(config_frame); self.process_name_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        enabled_var = tk.IntVar(value=1)
        ttk.Checkbutton(config_frame, text="Enabled", variable=enabled_var).grid(row=2, column=1, sticky="w", padx=5, pady=5)
        condition_frame = ttk.LabelFrame(right_frame, text="Condition")
        condition_frame.grid(row=1, column=0, sticky="ew", pady=10)
        ttk.Label(condition_frame, text="Condition Type:", style='Bold.TLabel').pack(side=tk.LEFT, padx=5, pady=5)
        self.condition_type = ttk.Combobox(condition_frame, values=["always_true"], state="readonly")
        self.condition_type.set("always_true"); self.condition_type.pack(side=tk.LEFT, padx=5, pady=5)
        actions_frame = ttk.LabelFrame(right_frame, text="Actions")
        actions_frame.grid(row=2, column=0, sticky="ew", pady=10)
        ttk.Label(actions_frame, text="Action Sequence Editor will be here.").pack(padx=5, pady=20)
        logs_frame = ttk.LabelFrame(right_frame, text="Real-time Logs")
        logs_frame.grid(row=3, column=0, sticky="nsew", pady=(10, 0)); logs_frame.grid_rowconfigure(0, weight=1); logs_frame.grid_columnconfigure(0, weight=1)
        self.log_text = tk.Text(logs_frame, bg="#1e1e1e", fg=self.TEXT_COLOR, state=tk.DISABLED, borderwidth=0, highlightthickness=0, font=("Consolas", 10))
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        ttk.Button(logs_frame, text="Save Changes", command=self.save_jobs).grid(row=1, column=0, sticky="se", padx=5, pady=5)
        return right_frame

    # <<< 추가/수정된 메서드들 >>>
    def load_jobs(self):
        if not os.path.exists(CONFIG_FILE): return
        try:
            with open(CONFIG_FILE, 'r') as f:
                self.saved_jobs = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config file: {e}"); self.saved_jobs = {}
    
    def update_saved_jobs_list(self):
        """저장된 Job 목록으로 상단 리스트박스를 업데이트합니다."""
        self.saved_jobs_listbox.delete(0, tk.END)
        for job_name in sorted(self.saved_jobs.keys()):
            self.saved_jobs_listbox.insert(tk.END, f"  {job_name}")

    def on_saved_job_select(self, event=None):
        """상단 리스트박스에서 저장된 Job을 선택했을 때 UI를 업데이트합니다."""
        if not self.saved_jobs_listbox.curselection(): return
        
        # 다른 리스트의 선택 해제
        self.jobs_listbox.selection_clear(0, tk.END)

        selected_job_name = self.saved_jobs_listbox.get(self.saved_jobs_listbox.curselection()[0]).strip()
        job_config = self.saved_jobs.get(selected_job_name)

        if job_config:
            self.job_name_entry.delete(0, tk.END); self.job_name_entry.insert(0, selected_job_name)
            self.process_name_entry.delete(0, tk.END); self.process_name_entry.insert(0, job_config['process_name'])
            self.condition_type.set(job_config['condition'])
            self.log(f"Loaded saved job: '{selected_job_name}'")

    def save_jobs(self):
        job_name = self.job_name_entry.get().strip()
        process_name = self.process_name_entry.get().strip()
        if not job_name or not process_name:
            self.log("ERROR: Job Name and Process Name are required to save.")
            return
        
        self.saved_jobs[job_name] = {"process_name": process_name, "condition": self.condition_type.get(), "actions": []}
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.saved_jobs, f, indent=4)
            self.log(f"✅ Job '{job_name}' saved successfully.")
        except IOError as e:
            self.log(f"❌ ERROR: Failed to save config file: {e}")
        
        self.update_saved_jobs_list() # 상단 리스트 갱신
        self.refresh_process_list(is_manual_refresh=True)

    def refresh_process_list(self, is_manual_refresh=False):
        try:
            running_processes = {p.info['name'] for p in psutil.process_iter(['name'])}
            saved_processes = {job['process_name'] for job in self.saved_jobs.values()}
            self.all_processes = sorted(list(running_processes.union(saved_processes)))
            self.filter_processes()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess): pass
        if not is_manual_refresh:
            self.root.after(5000, self.refresh_process_list)

    def filter_processes(self, event=None):
        search_term = self.find_entry.get().lower()
        self.jobs_listbox.delete(0, tk.END)
        saved_process_names = {job['process_name'] for job in self.saved_jobs.values()}
        for process in self.all_processes:
            if search_term in process.lower():
                prefix = "[S] " if process in saved_process_names else "    "
                self.jobs_listbox.insert(tk.END, f"{prefix}{process}")

    def on_process_select(self, event=None):
        if not self.jobs_listbox.curselection(): return
        
        # 다른 리스트의 선택 해제
        self.saved_jobs_listbox.selection_clear(0, tk.END)

        full_process_name = self.jobs_listbox.get(self.jobs_listbox.curselection()[0]).strip()
        is_saved = full_process_name.startswith("[S]")
        if is_saved:
            full_process_name = full_process_name.replace("[S]", "").strip()

        base_name, _ = os.path.splitext(full_process_name)
        
        found_saved_job = False
        if is_saved:
            for job_name, config in self.saved_jobs.items():
                if config['process_name'] == full_process_name:
                    self.on_saved_job_select_logic(job_name) # 로직 분리
                    found_saved_job = True
                    break
        
        if not found_saved_job:
            self.job_name_entry.delete(0, tk.END); self.job_name_entry.insert(0, base_name)
            self.process_name_entry.delete(0, tk.END); self.process_name_entry.insert(0, full_process_name)
            self.condition_type.set("always_true")
            self.log(f"Selected running process: {full_process_name}")

    def on_saved_job_select_logic(self, job_name):
        """선택된 Job 이름으로 UI를 채우는 로직 (중복 제거용)"""
        job_config = self.saved_jobs.get(job_name)
        if job_config:
            self.job_name_entry.delete(0, tk.END); self.job_name_entry.insert(0, job_name)
            self.process_name_entry.delete(0, tk.END); self.process_name_entry.insert(0, job_config['process_name'])
            self.condition_type.set(job_config['condition'])
            self.log(f"Loaded saved job: '{job_name}'")

    def log(self, message):
        self.log_text.config(state=tk.NORMAL); self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END); self.log_text.config(state=tk.DISABLED)

    def start_tracking(self):
        global tracker_thread, stop_event
        process_name = self.process_name_entry.get().strip()
        if not process_name:
            self.log("ERROR: Process Name is empty. Please select a process or a job.")
            return
        self.log(f"Job for '{process_name}' started.")
        self.start_button.config(state=tk.DISABLED); self.stop_button.config(state=tk.NORMAL)
        if self.overlay_root is None or not self.overlay_root.winfo_exists():
            self.overlay_root = tk.Toplevel(self.root); VisualOverlay(self.overlay_root)
        stop_event = threading.Event()
        tracker_thread = threading.Thread(target=track_windows_logic, args=(process_name, overlay_queue, stop_event), daemon=True)
        tracker_thread.start()

    def stop_tracking(self):
        global tracker_thread, stop_event
        job_name = self.job_name_entry.get().strip()
        self.log(f"Job '{job_name}' stopping...")
        if tracker_thread and tracker_thread.is_alive():
            stop_event.set(); tracker_thread.join(timeout=1)
        if self.overlay_root and self.overlay_root.winfo_exists():
            self.overlay_root.destroy(); self.overlay_root = None
        self.start_button.config(state=tk.NORMAL); self.stop_button.config(state=tk.DISABLED)
        self.log(f"Job '{job_name}' stopped.")

    def on_closing(self):
        if tracker_thread and tracker_thread.is_alive():
            self.stop_tracking()
        self.root.destroy()

if __name__ == "__main__":
    gw.FAILSAFE = False
    root = tk.Tk()
    app = AutomationUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()