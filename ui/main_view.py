# AutomationProject/ui/main_view.py
import tkinter as tk
from tkinter import ttk, font
import os
import psutil
import threading
import time
import queue

# 다른 모듈들 import
from data import config_manager
from data.models import Job
from ui.conditions_frame import ConditionsFrame
from ui.actions_frame import ActionsFrame
from core.vision import find_image_in_area
from core import controls

# 기존 추적 관련 클래스/함수 포함
import pygetwindow as gw
import win32gui
import win32process

feedback_queue = queue.Queue()
overlay_queue = queue.Queue()
action_queue = queue.Queue()

# (VisualOverlay, JobRunner, ActionExecutor 클래스는 이전 코드와 동일합니다.)
# ... (생략) ...
class VisualOverlay:
    def __init__(self, root, stop_callback):
        self.root = root; self.stop_callback = stop_callback; self.root.attributes('-fullscreen', True); self.root.attributes('-topmost', True); self.root.attributes('-transparentcolor', 'black'); self.root.config(bg='black'); self.root.overrideredirect(True)
        self.canvas = tk.Canvas(self.root, bg='black', highlightthickness=0); self.canvas.pack(fill=tk.BOTH, expand=True)
        self.image_highlight_timer = None; self.process_rect_ids = []; self.root.bind('<Escape>', self.on_exit); self.root.focus_set(); self.update_overlay()
    def update_overlay(self):
        try:
            while not overlay_queue.empty():
                item = overlay_queue.get_nowait()
                if item['type'] == 'process_windows':
                    for rect_id in self.process_rect_ids: self.canvas.delete(rect_id)
                    self.process_rect_ids = []
                    for window_info in item['data']:
                        x1, y1, x2, y2 = window_info['rect']; title = window_info['title']
                        rect_id = self.canvas.create_rectangle(x1, y1, x2, y2, outline="#00FF00", width=3)
                        self.process_rect_ids.append(rect_id)
                        text_bg_id = self.canvas.create_rectangle(x1, y1 - 30, x1 + 400, y1, fill="black", outline="")
                        self.process_rect_ids.append(text_bg_id)
                        text_id = self.canvas.create_text(x1 + 5, y1 - 25, text=title, font=("Arial", 12, "bold"), fill="#00FF00", anchor="nw")
                        self.process_rect_ids.append(text_id)
                elif item['type'] == 'found_image':
                    rect, similarity = item['data']; x1, y1, x2, y2 = rect
                    self.canvas.delete("image_highlight")
                    self.canvas.create_rectangle(x1, y1, x2, y2, outline="#FF0000", width=4, tags="image_highlight")
                    sim_text = f"Sim: {similarity*100:.1f}%"; self.canvas.create_text(x1, y1 - 15, text=sim_text, font=("Arial", 10, "bold"), fill="red", anchor="sw", tags="image_highlight")
                    if self.image_highlight_timer: self.root.after_cancel(self.image_highlight_timer)
                    self.image_highlight_timer = self.root.after(2000, lambda: self.canvas.delete("image_highlight"))
        except queue.Empty: pass
        self.root.after(100, self.update_overlay)
    def on_exit(self, event=None): print("User requested exit via ESC key."); self.stop_callback()

class JobRunner(threading.Thread):
    def __init__(self, job, feedback_q, overlay_q, action_q):
        super().__init__(daemon=True)
        self.job = job; self.feedback_queue = feedback_q
        self.overlay_queue = overlay_q; self.action_queue = action_q
        self.stop_event = threading.Event(); self.last_checked = {}
    def get_client_rect_abs(self, hwnd):
        if not win32gui.IsWindow(hwnd): return None
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        client_origin_screen = win32gui.ClientToScreen(hwnd, (left, top))
        client_end_screen = win32gui.ClientToScreen(hwnd, (right, bottom))
        return (client_origin_screen[0], client_origin_screen[1], client_end_screen[0], client_end_screen[1])
    def run(self):
        print(f"Runner: Starting job '{self.job.name}'")
        while not self.stop_event.is_set():
            process_name = self.job.process_name
            target_pids = {p.info['pid'] for p in psutil.process_iter(['pid', 'name']) if p.info['name'].lower() == process_name.lower()}
            tracked_windows = []
            if target_pids:
                def callback(hwnd, hwnds):
                    try:
                        _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                        if found_pid in target_pids and win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                            hwnds.append(hwnd)
                    except: pass
                    return True
                hwnds = []; win32gui.EnumWindows(callback, hwnds)
                for hwnd in hwnds[:2]:
                    full_rect = win32gui.GetWindowRect(hwnd)
                    search_rect = self.get_client_rect_abs(hwnd) 
                    title = win32gui.GetWindowText(hwnd)
                    tracked_windows.append({'full_rect': full_rect, 'search_rect': search_rect, 'title': title})
            overlay_data = [{'rect': win['full_rect'], 'title': win['title']} for win in tracked_windows]
            self.overlay_queue.put({'type': 'process_windows', 'data': overlay_data})
            triggered_events = []
            for condition in self.job.conditions:
                if not condition.enabled: continue
                now = time.time(); last_run = self.last_checked.get(condition.id, 0)
                try: interval = float(condition.params.get('interval', 2.0))
                except (ValueError, TypeError): interval = 2.0
                if now - last_run > interval:
                    self.last_checked[condition.id] = now
                    if condition.type == "Image Similarity":
                        image_path = condition.params.get('image_path')
                        threshold = float(condition.params.get('threshold', 80.0)) / 100.0
                        if image_path and os.path.exists(image_path) and tracked_windows:
                            for window in tracked_windows:
                                found, coords, max_val = find_image_in_area(image_path, bbox=window['search_rect'], threshold=threshold)
                                if found:
                                    self.feedback_queue.put({"status": "condition_met", "condition_id": condition.id, "condition_type": condition.type, "details": f"Image found in '{window['title']}' (Sim: {max_val*100:.1f}%)"})
                                    self.overlay_queue.put({'type': 'found_image', 'data': (coords, max_val)})
                                    event_data = {"condition": condition, "target_window": {"title": window['title'],"rect": window['search_rect'],}}
                                    triggered_events.append(event_data)
            if triggered_events: self.action_queue.put(triggered_events)
            if self.stop_event.wait(1): break
        self.overlay_queue.put({'type': 'process_windows', 'data': []})
        print(f"Runner: Stopping job '{self.job.name}'")
    def stop(self): self.stop_event.set()

class ActionExecutor(threading.Thread):
    def __init__(self, action_q, ui_logger):
        super().__init__(daemon=True)
        self.action_queue = action_q; self.ui_logger = ui_logger; self.stop_event = threading.Event()
    def run(self):
        print("Executor: Starting...")
        while not self.stop_event.is_set():
            try:
                events_to_process = self.action_queue.get(timeout=1)
                for event in events_to_process:
                    self.ui_logger(f"EXECUTOR: Processing actions for '{event['target_window']['title']}'")
                    controls.execute_action_sequence(actions=event['condition'].actions, target_window=event['target_window'])
            except queue.Empty: continue
        print("Executor: Stopping...")
    def stop(self): self.stop_event.set()

class AutomationUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Automation Project UI (v8.5 - Layout Improved)")
        
        screen_height = self.root.winfo_screenheight()
        screen_width = self.root.winfo_screenwidth()
        win_height = int(screen_height * 0.9)
        win_width = min(int(win_height * (16 / 9)), int(screen_width * 0.95))
        self.root.geometry(f"{win_width}x{win_height}")
        self.root.update_idletasks()
        x_cordinate = int((screen_width - win_width) / 2)
        y_cordinate = int((screen_height - win_height) / 2)
        self.root.geometry(f"+{x_cordinate}+{y_cordinate}")

        self.all_processes = []
        self.saved_jobs = config_manager.load_jobs()
        self.current_job = None
        self.job_runner = None
        self.overlay_window = None
        self.action_executor = None
        self.setup_styles()
        self.create_widgets()
        self.log("Application UI Initialized.")
        if self.saved_jobs: self.log(f"Loaded {len(self.saved_jobs)} saved job(s).")
        self.check_feedback_queue()
        self.refresh_process_list()

    def check_feedback_queue(self):
        try:
            message = feedback_queue.get_nowait()
            if message["status"] == "condition_met":
                self.log(f"🔥 Condition Met: {message['condition_type']} - {message['details']}")
                self.conditions_frame.highlight_condition(message['condition_id'])
        except queue.Empty: pass
        self.root.after(100, self.check_feedback_queue)

    def setup_styles(self):
        self.BG_COLOR = "#212121"; self.FRAME_BG = "#2c2c2c"; self.TEXT_COLOR = "#f0f0f0"
        self.BUTTON_BG = "#4a4a4a"; self.LISTBOX_BG = "#3c3c3c"; self.ENTRY_BG = "#333333"
        self.LISTBOX_SELECT_BG = "#005a9e"; style = ttk.Style(); style.theme_use('clam')
        default_font = font.nametofont("TkDefaultFont"); default_font.configure(family="Segoe UI", size=11)
        style.configure('.', background=self.BG_COLOR, foreground=self.TEXT_COLOR, font=default_font)
        style.configure('TFrame', background=self.BG_COLOR)
        style.configure('TLabelframe', background=self.FRAME_BG, borderwidth=1, relief="solid")
        style.configure('TLabelframe.Label', background=self.FRAME_BG, foreground=self.TEXT_COLOR, font=("Segoe UI", 12, "bold"))
        style.configure('TButton', background=self.BUTTON_BG, foreground=self.TEXT_COLOR, borderwidth=1, padding=(10, 5))
        style.map('TButton', background=[('active', '#6a6a6a')])
        style.configure('TEntry', fieldbackground=self.ENTRY_BG, foreground=self.TEXT_COLOR, borderwidth=1, relief='solid', insertcolor=self.TEXT_COLOR)
        style.configure('TCombobox', fieldbackground=self.ENTRY_BG, foreground=self.TEXT_COLOR, selectbackground=self.LISTBOX_BG, borderwidth=1, relief='solid')
        self.root.option_add('*TCombobox*Listbox.background', self.LISTBOX_BG)
        style.configure('Treeview', background=self.LISTBOX_BG, foreground=self.TEXT_COLOR, fieldbackground=self.LISTBOX_BG, borderwidth=0)
        style.map('Treeview', background=[('selected', self.LISTBOX_SELECT_BG)])
        style.configure('Treeview.Heading', font=("Segoe UI", 10, "bold"), background=self.BUTTON_BG, foreground=self.TEXT_COLOR, relief="flat")
        
        # <<< 추가: 붉은색 테두리 스타일 >>>
        style.configure('RedBorder.TLabelframe', background=self.FRAME_BG, bordercolor="red", borderwidth=2)
        style.configure('RedBorder.TLabelframe.Label', background=self.FRAME_BG, foreground="red", font=("Segoe UI", 12, "bold"))
    
    def create_widgets(self):
        self.root.configure(bg=self.BG_COLOR)
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        left_panel = self._create_left_panel(main_pane)
        main_pane.add(left_panel, weight=2) 
        right_panel = self._create_right_panel(main_pane)
        main_pane.add(right_panel, weight=3)

    def _create_left_panel(self, parent):
        # <<< 수정: 모든 Job 관련 위젯을 담는 하나의 큰 프레임으로 변경 >>>
        left_frame = ttk.Frame(parent, style='TFrame')
        left_frame.rowconfigure(0, weight=1)
        left_frame.columnconfigure(0, weight=1)

        # (1) Job 설정 영역
        job_settings_frame = ttk.LabelFrame(left_frame, text="(1) Job 설정 영역", style='RedBorder.TLabelframe')
        job_settings_frame.grid(row=0, column=0, sticky="nsew")
        job_settings_frame.columnconfigure(0, weight=1)
        # 영역 내부 그리드 행 가중치 설정
        job_settings_frame.rowconfigure(0, weight=1) # Processes & Jobs
        job_settings_frame.rowconfigure(2, weight=1) # Saved Jobs

        # (2) Processes & Jobs
        process_list_frame = ttk.LabelFrame(job_settings_frame, text="Processes & Jobs")
        process_list_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10,5))
        process_list_frame.rowconfigure(1, weight=1); process_list_frame.columnconfigure(0, weight=1)
        find_frame = ttk.Frame(process_list_frame); find_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5); find_frame.columnconfigure(1, weight=1)
        ttk.Label(find_frame, text="Find:").grid(row=0, column=0); self.find_entry = ttk.Entry(find_frame); self.find_entry.grid(row=0, column=1, sticky="ew", padx=5)
        self.find_entry.bind("<KeyRelease>", self.filter_processes)
        self.jobs_listbox = tk.Listbox(process_list_frame, bg=self.LISTBOX_BG, fg=self.TEXT_COLOR, selectbackground=self.LISTBOX_SELECT_BG)
        self.jobs_listbox.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.jobs_listbox.bind('<<ListboxSelect>>', self.on_process_select)
        
        # (3) Job Configuration
        config_frame = ttk.LabelFrame(job_settings_frame, text="Job Configuration")
        config_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        config_frame.columnconfigure(1, weight=1)
        ttk.Label(config_frame, text="Job Name:", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.job_name_entry = ttk.Entry(config_frame); self.job_name_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        ttk.Label(config_frame, text="Process Name:", font=("Segoe UI", 11, "bold")).grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.process_name_entry = ttk.Entry(config_frame); self.process_name_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        # (1) Saved Jobs
        saved_jobs_frame = ttk.LabelFrame(job_settings_frame, text="Saved Jobs")
        saved_jobs_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        saved_jobs_frame.rowconfigure(0, weight=1); saved_jobs_frame.columnconfigure(0, weight=1)
        self.saved_jobs_listbox = tk.Listbox(saved_jobs_frame, bg=self.LISTBOX_BG, fg=self.TEXT_COLOR, selectbackground=self.LISTBOX_SELECT_BG, height=5)
        self.saved_jobs_listbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.saved_jobs_listbox.bind('<<ListboxSelect>>', self.on_saved_job_select)
        self.update_saved_jobs_list()


        # Job Control
        control_frame = ttk.LabelFrame(job_settings_frame, text="Job Control")
        control_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=5)
        control_frame.columnconfigure((0, 1), weight=1)
        ttk.Button(control_frame, text="Save", command=self.save_current_job).grid(row=0, column=0, sticky="ew", padx=(5,2), pady=5)
        ttk.Button(control_frame, text="Delete", command=self.delete_job).grid(row=0, column=1, sticky="ew", padx=(2,5), pady=5)
        self.start_button = ttk.Button(control_frame, text="Start Job", command=self.start_tracking)
        self.start_button.grid(row=1, column=0, sticky="ew", padx=5, pady=(0,5))
        self.stop_button = ttk.Button(control_frame, text="Stop Job", command=self.stop_tracking, state=tk.DISABLED)
        self.stop_button.grid(row=1, column=1, sticky="ew", padx=5, pady=(0,5))
        
        return left_frame

    def _create_right_panel(self, parent):
        # <<< 수정: Job Configuration 부분이 빠지고, 로그 프레임이 하단에 고정됨 >>>
        right_frame = ttk.Frame(parent, style='TFrame')
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1) # Conditions
        right_frame.rowconfigure(1, weight=1) # Actions

        self.conditions_frame = ConditionsFrame(right_frame)
        self.conditions_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        self.conditions_frame.on_condition_select_callback = self.on_condition_select
        
        self.actions_frame = ActionsFrame(right_frame, get_process_name_callback=self.get_current_process_name, log_callback=self.log)
        self.actions_frame.grid(row=1, column=0, sticky="nsew", pady=5)
        
        logs_frame = ttk.LabelFrame(right_frame, text="Real-time Logs")
        logs_frame.grid(row=2, column=0, sticky="sew", pady=(5, 0))
        logs_frame.rowconfigure(0, weight=1); logs_frame.columnconfigure(0, weight=1)
        self.log_text = tk.Text(logs_frame, bg="#1e1e1e", fg=self.TEXT_COLOR, height=8, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        return right_frame

    # (나머지 모든 로직 함수는 이전과 동일)
    # ... (생략) ...
    def get_current_process_name(self):
        return self.process_name_entry.get().strip()
    def start_tracking(self):
        if self.job_runner and self.job_runner.is_alive(): self.log("A job is already running."); return
        if not self.current_job: self.log("ERROR: No job selected."); return
        self.log(f"Starting job '{self.current_job.name}'...")
        self.job_runner = JobRunner(self.current_job, feedback_queue, overlay_queue, action_queue)
        self.job_runner.start()
        self.action_executor = ActionExecutor(action_queue, self.log)
        self.action_executor.start()
        if self.overlay_window is None or not self.overlay_window.winfo_exists():
            self.overlay_window = tk.Toplevel(self.root)
            VisualOverlay(self.overlay_window, self.stop_tracking)
        self.start_button.config(state=tk.DISABLED); self.stop_button.config(state=tk.NORMAL)
    def stop_tracking(self):
        if self.job_runner and self.job_runner.is_alive():
            self.log(f"Stopping job runner..."); self.job_runner.stop(); self.job_runner = None
        if self.action_executor and self.action_executor.is_alive():
            self.log("Stopping action executor..."); self.action_executor.stop(); self.action_executor = None
        if self.overlay_window and self.overlay_window.winfo_exists():
            self.overlay_window.destroy(); self.overlay_window = None
        self.start_button.config(state=tk.NORMAL); self.stop_button.config(state=tk.DISABLED)
        self.log("Job stopped.")
    def update_saved_jobs_list(self):
        self.saved_jobs_listbox.delete(0, tk.END)
        for job_name in sorted(self.saved_jobs.keys()): self.saved_jobs_listbox.insert(tk.END, f"  {job_name}")
    def on_saved_job_select(self, event=None):
        if not self.saved_jobs_listbox.curselection(): return
        self.jobs_listbox.selection_clear(0, tk.END)
        job_name = self.saved_jobs_listbox.get(self.saved_jobs_listbox.curselection()[0]).strip()
        self.load_job_into_ui(job_name)
    def on_process_select(self, event=None):
        if not self.jobs_listbox.curselection(): return
        self.saved_jobs_listbox.selection_clear(0, tk.END)
        full_process_name = self.jobs_listbox.get(self.jobs_listbox.curselection()[0]).strip()
        is_saved = full_process_name.startswith("[S]")
        if is_saved: full_process_name = full_process_name.replace("[S]", "").strip()
        base_name, _ = os.path.splitext(full_process_name)
        found_job_name = None
        if is_saved:
            for name, job_obj in self.saved_jobs.items():
                if job_obj.process_name == full_process_name: found_job_name = name; break
        if found_job_name: self.load_job_into_ui(found_job_name)
        else:
            self.current_job = None
            self.job_name_entry.delete(0, tk.END); self.job_name_entry.insert(0, base_name)
            self.process_name_entry.delete(0, tk.END); self.process_name_entry.insert(0, full_process_name)
            self.conditions_frame.load_job(None)
            self.log(f"Selected running process: {full_process_name}")
    def load_job_into_ui(self, job_name):
        self.current_job = self.saved_jobs.get(job_name)
        if self.current_job:
            self.job_name_entry.delete(0, tk.END); self.job_name_entry.insert(0, self.current_job.name)
            self.process_name_entry.delete(0, tk.END); self.process_name_entry.insert(0, self.current_job.process_name)
            self.log(f"Loaded job: '{job_name}'")
        self.conditions_frame.load_job(self.current_job)
    def on_condition_select(self, condition):
        self.actions_frame.load_condition(condition)
    def create_new_job(self):
        self.saved_jobs_listbox.selection_clear(0, tk.END); self.jobs_listbox.selection_clear(0, tk.END)
        self.job_name_entry.delete(0, tk.END); self.process_name_entry.delete(0, tk.END)
        self.current_job = None; self.conditions_frame.load_job(None)
        self.log("Initialized for new job. Enter details and save.")
    def save_current_job(self):
        job_name = self.job_name_entry.get().strip(); process_name = self.process_name_entry.get().strip()
        if not job_name or not process_name: self.log("ERROR: Job Name and Process Name are required."); return
        if self.current_job and self.current_job.name == job_name: self.current_job.process_name = process_name
        else:
            new_job = Job(name=job_name, process_name=process_name)
            if self.current_job: new_job.conditions = self.current_job.conditions
            self.current_job = new_job
        self.saved_jobs[job_name] = self.current_job
        success, msg = config_manager.save_jobs(self.saved_jobs)
        self.log(f"✅ {msg}" if success else f"❌ {msg}")
        self.update_saved_jobs_list(); self.refresh_process_list(is_manual_refresh=True)
    def delete_job(self):
        if not self.saved_jobs_listbox.curselection(): self.log("⚠️ No saved job selected to delete."); return
        selected_job_name = self.saved_jobs_listbox.get(self.saved_jobs_listbox.curselection()[0]).strip()
        if selected_job_name in self.saved_jobs:
            del self.saved_jobs[selected_job_name]
            success, msg = config_manager.save_jobs(self.saved_jobs)
            if success:
                self.log(f"🗑️ Job '{selected_job_name}' deleted successfully.")
                self.create_new_job(); self.update_saved_jobs_list(); self.refresh_process_list(is_manual_refresh=True)
            else: self.log(f"❌ {msg}")
    def refresh_process_list(self, is_manual_refresh=False):
        try:
            running_processes = {p.info['name'] for p in psutil.process_iter(['name'])}
            saved_processes = {job.process_name for job in self.saved_jobs.values()}
            self.all_processes = sorted(list(running_processes.union(saved_processes)))
            self.filter_processes()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess): pass
        if not is_manual_refresh: self.root.after(5000, self.refresh_process_list)
    def filter_processes(self, event=None):
        search_term = self.find_entry.get().lower()
        self.jobs_listbox.delete(0, tk.END)
        saved_process_names = {job.process_name for job in self.saved_jobs.values()}
        for process in self.all_processes:
            if search_term in process.lower():
                prefix = "[S] " if process in saved_process_names else "    "
                self.jobs_listbox.insert(tk.END, f"{prefix}{process}")
    def log(self, message):
        self.log_text.config(state=tk.NORMAL); self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END); self.log_text.config(state=tk.DISABLED)
    def on_closing(self):
        if self.job_runner or self.action_executor: self.stop_tracking()
        self.root.destroy()