# AutomationProject/ui/actions_frame.py
import tkinter as tk
from tkinter import ttk
from data.models import Action
from core.recorder import Recorder

class ActionsFrame(ttk.LabelFrame):
    def __init__(self, parent, get_process_name_callback, log_callback, *args, **kwargs):
        super().__init__(parent, text="Actions", *args, **kwargs)
        self.current_condition = None
        self.get_process_name = get_process_name_callback
        self.log = log_callback
        self.recorder_thread = None

        self._create_widgets()

    def _create_widgets(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Treeview로 변경하여 세부 정보 표시
        self.tree = ttk.Treeview(self, columns=("Delay", "Type", "Details"), show="headings")
        self.tree.heading("Delay", text="Delay(s)")
        self.tree.heading("Type", text="Type")
        self.tree.heading("Details", text="Details")
        self.tree.column("Delay", width=60, anchor="center")
        self.tree.column("Type", width=120)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        control_frame = ttk.Frame(self, style='TFrame')
        control_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(5,0))

        # Record 버튼 추가
        self.record_button = ttk.Button(control_frame, text="Record Actions", command=self.toggle_recording)
        self.record_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Add/Remove 버튼 (수동 조작용)
        ttk.Button(control_frame, text="Remove Selected", command=self.remove_action).pack(side=tk.LEFT)

    def load_condition(self, condition):
        self.current_condition = condition
        self.update_treeview()
        
    def update_treeview(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        if self.current_condition:
            for action in self.current_condition.actions:
                delay = action.params.get('delay', 0)
                details = ", ".join([f"{k}:{v}" for k, v in action.params.items() if k != 'delay'])
                self.tree.insert("", "end", values=(f"{delay:.2f}", action.type, details))

    def toggle_recording(self):
        if self.recorder_thread and self.recorder_thread.is_alive():
            # 이 기능은 ESC로만 중지되므로 버튼은 비활성화 상태를 유지
            return

        process_name = self.get_process_name()
        if not process_name:
            self.log("❌ ERROR: Process Name must be set to start recording.")
            return

        if not self.current_condition:
            self.log("❌ ERROR: A condition must be selected to add recorded actions.")
            return

        self.log("🔴 Recording... (Press ESC to Stop)")
        self.record_button.config(state=tk.DISABLED)
        self.recorder_thread = Recorder(process_name=process_name, callback=self.on_recording_complete)
        self.recorder_thread.start()

    def on_recording_complete(self, recorded_actions):
        # 백그라운드 스레드에서 호출되므로, UI 업데이트는 self.after 사용
        self.after(0, self._update_ui_after_recording, recorded_actions)

    def _update_ui_after_recording(self, recorded_actions):
        self.log(f"✅ Recording finished. {len(recorded_actions)} actions captured.")
        if self.current_condition:
            self.current_condition.actions.extend(recorded_actions)
            self.update_treeview()
        self.record_button.config(state=tk.NORMAL)

    def remove_action(self):
        if not self.current_condition or not self.tree.selection(): return
        
        selected_iids = self.tree.selection()
        # Treeview의 iid는 객체 id가 아니므로, index를 기반으로 삭제
        indices_to_delete = sorted([self.tree.index(iid) for iid in selected_iids], reverse=True)

        for index in indices_to_delete:
            del self.current_condition.actions[index]
        
        self.update_treeview()
        print(f"UI: Removed {len(indices_to_delete)} action(s).")