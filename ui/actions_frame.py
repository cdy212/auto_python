# AutomationProject/ui/actions_frame.py
import tkinter as tk
from tkinter import ttk, simpledialog
from data.models import Action
from core.recorder import Recorder
import copy
import uuid

# (ActionEditorDialog 클래스는 변경 없음)
class ActionEditorDialog(tk.Toplevel):
    def __init__(self, parent, action):
        super().__init__(parent)
        self.transient(parent)
        self.title(f"Edit Action - {action.type}")
        self.action = action
        self.result = None
        self.create_widgets()
        self.load_data()
        self.grab_set()
        self.wait_window(self)
    def create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(padx=15, pady=15, fill=tk.BOTH, expand=True)
        ttk.Label(main_frame, text="Delay (s):").grid(row=0, column=0, sticky="w", pady=2)
        self.delay_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.delay_var).grid(row=0, column=1, sticky="ew")
        if "Mouse" in self.action.type:
            ttk.Label(main_frame, text="Relative X:").grid(row=1, column=0, sticky="w", pady=2)
            self.rx_var = tk.StringVar()
            ttk.Entry(main_frame, textvariable=self.rx_var).grid(row=1, column=1, sticky="ew")
            ttk.Label(main_frame, text="Relative Y:").grid(row=2, column=0, sticky="w", pady=2)
            self.ry_var = tk.StringVar()
            ttk.Entry(main_frame, textvariable=self.ry_var).grid(row=2, column=1, sticky="ew")
        elif self.action.type == "Key Input":
            ttk.Label(main_frame, text="Text:").grid(row=1, column=0, sticky="w", pady=2)
            self.text_var = tk.StringVar()
            ttk.Entry(main_frame, textvariable=self.text_var).grid(row=1, column=1, sticky="ew")
        elif self.action.type == "Key Special":
            ttk.Label(main_frame, text="Special Key:").grid(row=1, column=0, sticky="w", pady=2)
            self.key_var = tk.StringVar()
            ttk.Entry(main_frame, textvariable=self.key_var).grid(row=1, column=1, sticky="ew")
        main_frame.columnconfigure(1, weight=1)
        btn_frame = ttk.Frame(self)
        btn_frame.pack(padx=15, pady=(0, 15), fill=tk.X)
        ttk.Button(btn_frame, text="OK", command=self.on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT)
    def load_data(self):
        self.delay_var.set(str(self.action.params.get('delay', 0.0)))
        if "Mouse" in self.action.type:
            rx, ry = self.action.params.get('relative_pos', (0, 0))
            self.rx_var.set(str(rx)); self.ry_var.set(str(ry))
        elif self.action.type == "Key Input": self.text_var.set(self.action.params.get('text', ''))
        elif self.action.type == "Key Special": self.key_var.set(self.action.params.get('key', ''))
    def on_ok(self):
        try:
            self.action.params['delay'] = float(self.delay_var.get())
            if "Mouse" in self.action.type:
                self.action.params['relative_pos'] = (int(self.rx_var.get()), int(self.ry_var.get()))
            elif self.action.type == "Key Input": self.action.params['text'] = self.text_var.get()
            elif self.action.type == "Key Special": self.action.params['key'] = self.key_var.get()
            self.result = self.action
        except (ValueError, TypeError) as e:
            print(f"Invalid input: {e}"); return
        self.destroy()

class ActionsFrame(ttk.LabelFrame):
    def __init__(self, parent, get_process_name_callback, log_callback, on_preview_update_callback, *args, **kwargs):
        super().__init__(parent, text="Actions", *args, **kwargs)
        self.current_condition = None
        self.get_process_name = get_process_name_callback
        self.log = log_callback
        self.on_preview_update_callback = on_preview_update_callback
        self.recorder_thread = None
        self._create_widgets()
        self._bind_dnd_events()

    def _create_widgets(self):
        self.columnconfigure(0, weight=1)
        # <<< 행 구성을 2개로 변경 (목록, 하단 버튼 프레임) >>>
        self.rowconfigure(0, weight=1)
        
        # --- 상단 프레임 (Treeview + 순서 변경 버튼) ---
        top_frame = ttk.Frame(self)
        top_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        top_frame.columnconfigure(0, weight=1)
        top_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(top_frame, columns=("#", "Delay", "Type", "Details"), show="headings")
        self.tree.heading("#", text="#")
        self.tree.heading("Delay", text="Delay(s)")
        self.tree.heading("Type", text="Type")
        self.tree.heading("Details", text="Details")
        self.tree.column("#", width=40, anchor="center", stretch=False)
        self.tree.column("Delay", width=60, anchor="center", stretch=False)
        self.tree.column("Type", width=120, stretch=False)
        self.tree.column("Details", width=100)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<Double-1>", self.on_double_click_edit)

        # --- 순서 변경 버튼 프레임 ---
        move_btn_frame = ttk.Frame(top_frame)
        move_btn_frame.grid(row=0, column=1, sticky="ns", padx=(5,0))
        ttk.Button(move_btn_frame, text="▲", command=self.move_action_up, width=3).pack(pady=2, padx=2)
        ttk.Button(move_btn_frame, text="▼", command=self.move_action_down, width=3).pack(pady=2, padx=2)

        # --- 하단 제어 버튼 프레임 ---
        control_frame = ttk.Frame(self, style='TFrame')
        control_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(5,0))
        
        self.record_button = ttk.Button(control_frame, text="Record Actions", command=self.toggle_recording)
        self.record_button.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(control_frame, text="Add New", command=self.add_new_action).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Copy Selected", command=self.copy_action).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Remove Selected", command=self.remove_action).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Clear All", command=self.clear_all_actions).pack(side=tk.LEFT, padx=5)
        
        # --- 위치 확인 버튼 (오른쪽 정렬) ---
        ttk.Button(control_frame, text="위치확인", command=self.check_positions).pack(side=tk.RIGHT, padx=5)

    def _bind_dnd_events(self):
        self.tree.bind("<ButtonPress-1>", self.on_dnd_press)
        self.tree.bind("<B1-Motion>", self.on_dnd_motion)
        self.tree.bind("<ButtonRelease-1>", self.on_dnd_release)
        self._dnd_item = None

    def on_dnd_press(self, event):
        item_id = self.tree.identify_row(event.y)
        if item_id: self._dnd_item = item_id

    def on_dnd_motion(self, event):
        if not self._dnd_item: return
        target_id = self.tree.identify_row(event.y)
        if target_id and target_id != self._dnd_item:
            self.tree.move(self._dnd_item, '', self.tree.index(target_id))

    def on_dnd_release(self, event):
        if not self._dnd_item or not self.current_condition:
            self._dnd_item = None
            return
        
        try:
            reordered_actions = []
            for iid in self.tree.get_children():
                original_index = int(iid)
                reordered_actions.append(self.current_condition.actions[original_index])
            
            self.current_condition.actions = reordered_actions
            self.log("Actions reordered.")
            self.update_treeview()
        except (ValueError, IndexError) as e:
            print(f"DND Error: {e}")
            self.update_treeview()
        finally:
            self._dnd_item = None

    def on_double_click_edit(self, event):
        if not self.current_condition: return
        item_id = self.tree.identify_row(event.y)
        if not item_id: return
        try:
            item_index = int(item_id)
            action_to_edit = self.current_condition.actions[item_index]
            action_copy = copy.deepcopy(action_to_edit)
            dialog = ActionEditorDialog(self, action_copy)
            if dialog.result:
                self.current_condition.actions[item_index] = dialog.result
                self.update_treeview()
                self.log("Action updated successfully.")
        except (ValueError, IndexError) as e: print(f"Edit Error: {e}")

    # <<< '위치확인' 버튼과 연결될 메서드 >>>
    def check_positions(self):
        """ 현재 목록의 모든 마우스 위치를 오버레이에 표시하도록 요청합니다. """
        if not self.current_condition:
            self.log("⚠️ No condition selected.")
            return
        self.log("ACTION: Checking all mouse positions...")
        self.on_preview_update_callback(self.get_all_mouse_actions())

    # <<< 순서 변경 메서드들 추가 >>>
    def move_action_up(self):
        selection = self.tree.selection()
        if not selection:
            self.log("⚠️ Please select an action to move.")
            return
        
        for iid in selection:
            index = int(iid)
            if index > 0:
                self.current_condition.actions.insert(index - 1, self.current_condition.actions.pop(index))
        
        self.update_treeview()
        # 선택 유지
        new_selection_index = int(selection[0]) - 1
        if new_selection_index >= 0:
            self.tree.selection_set(str(new_selection_index))

    def move_action_down(self):
        selection = self.tree.selection()
        if not selection:
            self.log("⚠️ Please select an action to move.")
            return

        # 아래에서 위로 순회해야 인덱스가 꼬이지 않음
        for iid in reversed(selection):
            index = int(iid)
            if index < len(self.current_condition.actions) - 1:
                self.current_condition.actions.insert(index + 1, self.current_condition.actions.pop(index))

        self.update_treeview()
        # 선택 유지
        new_selection_index = int(selection[0]) + 1
        if new_selection_index < len(self.current_condition.actions):
            self.tree.selection_set(str(new_selection_index))

    def clear_all_actions(self):
        if not self.current_condition:
            self.log("⚠️ No condition selected to clear actions.")
            return

        if not self.current_condition.actions:
            self.log("ℹ️ Action list is already empty.")
            return

        self.current_condition.actions.clear()
        self.update_treeview()
        self.log("🗑️ All actions have been cleared.")
        self.on_preview_update_callback([]) # 미리보기 클리어

    def get_all_mouse_actions(self):
        if not self.current_condition:
            return []
        
        mouse_actions_data = []
        for i, action in enumerate(self.current_condition.actions):
            if "Mouse" in action.type and 'relative_pos' in action.params:
                mouse_actions_data.append({
                    'seq': i + 1,
                    'pos': action.params['relative_pos']
                })
        return mouse_actions_data

    def load_condition(self, condition):
        self.current_condition = condition
        self.update_treeview()
        # Condition 로드 시 자동 위치 표시는 제거
        self.on_preview_update_callback([])

    def update_treeview(self):
        # 선택 상태와 스크롤 위치 저장
        selection = self.tree.selection()
        
        # Treeview 클리어
        for i in self.tree.get_children(): self.tree.delete(i)
        
        # 데이터 다시 채우기
        if self.current_condition:
            for i, action in enumerate(self.current_condition.actions):
                delay = action.params.get('delay', 0)
                details = ", ".join([f"{k}: {v}" for k, v in action.params.items() if k != 'delay' and not k.startswith('__')])
                self.tree.insert("", "end", iid=str(i), values=(i + 1, f"{delay:.2f}", action.type, details))
        
        # 선택 상태 복원
        if selection:
            try: 
                self.tree.selection_set(selection)
                self.tree.focus(selection[0])
                self.tree.see(selection[0])
            except tk.TclError: pass

    def toggle_recording(self):
        if self.recorder_thread and self.recorder_thread.is_alive(): return
        process_name = self.get_process_name()
        if not process_name: self.log("❌ ERROR: Process Name must be set to start recording."); return
        if not self.current_condition: self.log("❌ ERROR: A condition must be selected to add recorded actions."); return
        self.log("🔴 Recording... (Press ESC to Stop)")
        self.record_button.config(state=tk.DISABLED)
        self.recorder_thread = Recorder(process_name=process_name, callback=self.on_recording_complete)
        self.recorder_thread.start()

    def on_recording_complete(self, recorded_actions):
        self.after(0, self._update_ui_after_recording, recorded_actions)

    def _update_ui_after_recording(self, recorded_actions):
        self.log(f"✅ Recording finished. {len(recorded_actions)} actions captured.")
        if self.current_condition:
            self.current_condition.actions.extend(recorded_actions)
            self.update_treeview()
        self.record_button.config(state=tk.NORMAL)
        
    def add_new_action(self):
        if not self.current_condition:
            self.log("❌ ERROR: A condition must be selected to add a new action.")
            return
        
        action_type = simpledialog.askstring("Add New Action", "Enter Action Type:", initialvalue="Mouse Click", parent=self)
        if action_type:
            params = {'delay': 0.5}
            if "Mouse" in action_type:
                params['target_type'] = 'relative'
                params['relative_pos'] = (0, 0)
                params['button'] = 'Button.left'
            new_action = Action(action_type, params=params)
            self.current_condition.actions.append(new_action)
            self.update_treeview()
            self.log(f"Added new '{action_type}' action.")

    def copy_action(self):
        if not self.current_condition or not self.tree.selection():
            self.log("⚠️ No action selected to copy.")
            return

        selected_indices = sorted([int(iid) for iid in self.tree.selection()])
        for index in reversed(selected_indices):
            action_to_copy = self.current_condition.actions[index]
            new_action = copy.deepcopy(action_to_copy)
            new_action.id = str(uuid.uuid4())
            self.current_condition.actions.insert(index + 1, new_action)
        
        self.update_treeview()
        self.log(f"Copied {len(selected_indices)} action(s).")
        
    def remove_action(self):
        if not self.current_condition or not self.tree.selection(): return
        selected_iids = self.tree.selection()
        indices_to_delete = sorted([int(iid) for iid in selected_iids], reverse=True)

        for index in indices_to_delete:
            del self.current_condition.actions[index]
        
        self.update_treeview()
        self.log(f"Removed {len(indices_to_delete)} action(s).")