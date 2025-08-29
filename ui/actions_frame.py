# AutomationProject/ui/actions_frame.py
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from data.models import Action
from core.recorder import Recorder
import copy
import uuid

# (ActionEditorDialog 클래스는 이전 코드와 동일)
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
    def __init__(self, parent, get_process_name_callback, log_callback, *args, **kwargs):
        super().__init__(parent, text="Actions", *args, **kwargs)
        self.current_condition = None
        self.get_process_name = get_process_name_callback
        self.log = log_callback
        self.recorder_thread = None
        self._create_widgets()
        self._bind_dnd_events()

    def _create_widgets(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # <<< 수정: selectmode를 'extended'로 변경하여 다중 선택 활성화 >>>
        self.tree = ttk.Treeview(self, columns=("#", "Delay", "Type", "Details"), show="headings", selectmode='extended')
        self.tree.heading("#", text="#"); self.tree.heading("Delay", text="Delay(s)"); self.tree.heading("Type", text="Type"); self.tree.heading("Details", text="Details")
        self.tree.column("#", width=40, anchor="center", stretch=False); self.tree.column("Delay", width=60, anchor="center", stretch=False); self.tree.column("Type", width=120, stretch=False); self.tree.column("Details", width=100)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(5,0), pady=5)
        
        self.tree.bind("<Double-1>", self.on_double_click_edit)
        
        order_control_frame = ttk.Frame(self, style='TFrame')
        order_control_frame.grid(row=0, column=1, sticky="ns", padx=(0,5), pady=5)
        ttk.Button(order_control_frame, text="▲", width=2, command=self.move_action_up).pack(pady=(0,2))
        ttk.Button(order_control_frame, text="▼", width=2, command=self.move_action_down).pack()

        control_frame = ttk.Frame(self, style='TFrame')
        control_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=(5,0))

        self.record_button = ttk.Button(control_frame, text="Record Actions", command=self.toggle_recording)
        self.record_button.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(control_frame, text="Add New", command=self.add_new_action).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Copy Selected", command=self.copy_action).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Remove Selected", command=self.remove_action).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="Clear All", command=self.clear_all_actions).pack(side=tk.RIGHT, padx=5)

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
        if not self._dnd_item or not self.current_condition: return
        try:
            dragged_item_index = int(self._dnd_item)
            moved_action = self.current_condition.actions.pop(dragged_item_index)
            target_id = self.tree.identify_row(event.y)
            new_index = self.tree.index(target_id) if target_id else len(self.current_condition.actions)
            self.current_condition.actions.insert(new_index, moved_action)
            self.log(f"Action '{moved_action.type}' moved.")
            self.update_treeview()
        except (ValueError, IndexError) as e:
            print(f"DND Error: {e}"); self.update_treeview()
        finally: self._dnd_item = None

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

    def load_condition(self, condition):
        self.current_condition = condition
        self.update_treeview()
        
    def update_treeview(self):
        selected_items = self.tree.selection()
        for i in self.tree.get_children(): self.tree.delete(i)
        if self.current_condition:
            for i, action in enumerate(self.current_condition.actions):
                delay = action.params.get('delay', 0)
                details = ", ".join([f"{k}: {v}" for k, v in action.params.items() if k != 'delay' and not k.startswith('__')])
                self.tree.insert("", "end", iid=i, values=(i + 1, f"{delay:.2f}", action.type, details))
        if selected_items:
            try: self.tree.selection_set(selected_items)
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
        if not self.current_condition: self.log("❌ ERROR: A condition must be selected to add a new action."); return
        action_type = simpledialog.askstring("Add New Action", "Enter Action Type:", initialvalue="Mouse Click", parent=self)
        if action_type:
            params = {'delay': 0.5}
            if "Mouse" in action_type:
                params['target_type'] = 'relative'; params['relative_pos'] = (0, 0); params['button'] = 'Button.left'
            new_action = Action(action_type, params=params)
            self.current_condition.actions.append(new_action)
            self.update_treeview()
            self.log(f"Added new '{action_type}' action.")

    def copy_action(self):
        if not self.current_condition or not self.tree.selection(): self.log("⚠️ No action selected to copy."); return
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

    def clear_all_actions(self):
        if not self.current_condition: self.log("⚠️ No condition selected to clear actions from."); return
        if messagebox.askyesno("Confirm Clear", "Are you sure you want to delete all actions for this condition?"):
            self.current_condition.actions.clear()
            self.update_treeview()
            self.log("🗑️ All actions have been cleared.")

    def move_action_up(self):
        if not self.current_condition or not self.tree.selection(): return
        selected_iids = self.tree.selection()
        selected_indices = sorted([int(iid) for iid in selected_iids])
        if selected_indices[0] == 0: return
        for index in selected_indices:
            action_to_move = self.current_condition.actions.pop(index)
            self.current_condition.actions.insert(index - 1, action_to_move)
        self.update_treeview()
        new_selection = [str(i-1) for i in selected_indices]
        self.tree.selection_set(new_selection)

    def move_action_down(self):
        if not self.current_condition or not self.tree.selection(): return
        selected_iids = self.tree.selection()
        selected_indices = sorted([int(iid) for iid in selected_iids], reverse=True)
        if selected_indices[0] >= len(self.current_condition.actions) - 1: return
        for index in selected_indices:
            action_to_move = self.current_condition.actions.pop(index)
            self.current_condition.actions.insert(index + 1, action_to_move)
        self.update_treeview()
        new_selection = [str(i+1) for i in selected_indices]
        self.tree.selection_set(new_selection)