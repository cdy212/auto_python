# AutomationProject/ui/conditions_frame.py
import tkinter as tk
from tkinter import ttk, filedialog
from data.models import Condition
import os
import shutil
import uuid

class ConditionsFrame(ttk.LabelFrame):
    # <<< __init__ 수정: log_callback 추가 >>>
    def __init__(self, parent, log_callback, *args, **kwargs):
        super().__init__(parent, text="Conditions", *args, **kwargs)
        self.current_job = None
        self.on_condition_select_callback = None
        self._is_programmatic_update = False
        self.log = log_callback # log 함수 저장

        self._create_widgets()

    def _create_widgets(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        
        self.param_editor = ttk.Frame(self, style='TFrame')
        self.param_editor.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        self._create_param_widgets()

        self.tree = ttk.Treeview(self, columns=("Enabled", "Type", "Parameters"), show="headings")
        self.tree.heading("Enabled", text="On"); self.tree.heading("Type", text="Type"); self.tree.heading("Parameters", text="Parameters")
        self.tree.column("Enabled", width=40, anchor="center"); self.tree.column("Type", width=120)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        
        control_frame = ttk.Frame(self, style='TFrame')
        control_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=(5,0))
        
        ttk.Button(control_frame, text="Image Similarity : 이미지 유사도", 
                   command=self.add_image_similarity_condition).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(control_frame, text="Remove", command=self.remove_condition).pack(side=tk.RIGHT)

    def _create_param_widgets(self):
        self.param_frames = {}
        frame = ttk.Frame(self.param_editor, style='TFrame')
        self.param_frames["Image Similarity"] = frame
        
        ttk.Label(frame, text="Image:").grid(row=0, column=0, sticky="w")
        self.image_path_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.image_path_var, state="readonly").grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Button(frame, text="Select...", command=self.select_image).grid(row=0, column=2)
        
        ttk.Label(frame, text="Threshold (%):").grid(row=1, column=0, sticky="w", pady=2)
        self.threshold_var = tk.StringVar(value="80.0")
        ttk.Entry(frame, textvariable=self.threshold_var).grid(row=1, column=1, sticky="ew", padx=5)
        self.threshold_var.trace_add("write", lambda *args: self.update_param('threshold', self.threshold_var.get()))
        
        ttk.Label(frame, text="Interval (s):").grid(row=2, column=0, sticky="w", pady=2)
        self.interval_var = tk.StringVar(value="2.0")
        ttk.Entry(frame, textvariable=self.interval_var).grid(row=2, column=1, sticky="ew", padx=5)
        self.interval_var.trace_add("write", lambda *args: self.update_param('interval', self.interval_var.get()))

        frame.columnconfigure(1, weight=1)

    def select_image(self):
        condition = self.get_selected_condition()
        if not condition: return
        filepath = filedialog.askopenfilename(title="Select an Image", filetypes=(("PNG files", "*.png"), ("All files", "*.*")))
        if not filepath: return
        workspace_dir = os.path.join("workspace", "images")
        os.makedirs(workspace_dir, exist_ok=True)
        filename = f"{uuid.uuid4()}{os.path.splitext(filepath)[1]}"
        new_path = os.path.join(workspace_dir, filename)
        shutil.copy(filepath, new_path)
        self.image_path_var.set(new_path)
        self.update_param('image_path', new_path)
        self.update_treeview()
        
    def update_param(self, key, value):
        if self._is_programmatic_update: return
        condition = self.get_selected_condition()
        if not condition: return
        try:
            if key == 'threshold': value = float(value)
            if key == 'interval': value = float(value)
        except (ValueError, TypeError): return
        condition.params[key] = value
        # <<< print 대신 self.log 사용 >>>
        self.log(f"UI: Param '{key}' updated to '{value}'")
        self.update_treeview()
        
    def get_selected_condition(self):
        if not self.current_job or not self.tree.selection(): return None
        cond_id = self.tree.selection()[0]
        return self.current_job.find_condition_by_id(cond_id)
        
    def on_tree_select(self, event=None):
        condition = self.get_selected_condition()
        for frame in self.param_frames.values(): frame.grid_forget()
            
        if condition:
            self._is_programmatic_update = True
            if condition.type in self.param_frames:
                self.param_frames[condition.type].grid(row=0, column=0, sticky="nsew")
                if condition.type == "Image Similarity":
                    self.image_path_var.set(condition.params.get('image_path', ''))
                    self.threshold_var.set(str(condition.params.get('threshold', 80.0)))
                    self.interval_var.set(str(condition.params.get('interval', 2.0)))
            self._is_programmatic_update = False

        if self.on_condition_select_callback:
            self.on_condition_select_callback(condition)

    def highlight_condition(self, condition_id):
        self.tree.item(condition_id, tags=('highlight',))
        self.tree.tag_configure('highlight', background='yellow', foreground='black')
        self.after(3000, lambda: self.tree.item(condition_id, tags=()))
        
    def load_job(self, job):
        self.current_job = job
        self.on_tree_select()
        self.update_treeview()
        if self.on_condition_select_callback: self.on_condition_select_callback(None)
        
    def update_treeview(self):
        selection = self.tree.selection()
        for i in self.tree.get_children(): self.tree.delete(i)
        if self.current_job:
            for condition in self.current_job.conditions:
                params_str = ", ".join([f"{k}:{v}" for k,v in condition.params.items()])
                self.tree.insert("", "end", iid=condition.id, values=("✅" if condition.enabled else "❌", condition.type, params_str))
        if selection:
            try: self.tree.selection_set(selection)
            except tk.TclError: pass

    def add_image_similarity_condition(self):
        if not self.current_job:
            self.log("⚠️ No job selected to add a condition.")
            return
            
        cond_type = "Image Similarity"
        params = {'image_path': '', 'threshold': 80.0, 'interval': 2.0}
        new_condition = Condition(condition_type=cond_type, params=params)
        self.current_job.add_condition(new_condition)
        self.update_treeview()
        self.tree.selection_set(new_condition.id)
        # <<< print 대신 self.log 사용 >>>
        self.log(f"UI: Added Condition '{cond_type}' to Job '{self.current_job.name}'")

    def remove_condition(self):
        if not self.current_job: 
            return
        selected_ids = self.tree.selection()
        if not selected_ids: return
        for cond_id in selected_ids: self.current_job.remove_condition_by_id(cond_id)
        self.update_treeview()
        self.on_tree_select()
        # <<< print 대신 self.log 사용 >>>
        self.log(f"UI: Removed {len(selected_ids)} condition(s).")