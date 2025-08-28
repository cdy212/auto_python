import tkinter as tk
from tkinter import ttk
from data.models import Action

class ActionsFrame(ttk.LabelFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, text="Actions", *args, **kwargs)
        self.current_condition = None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Action 목록을 보여줄 Listbox
        self.listbox = tk.Listbox(self, bg="#3c3c3c", fg="#f0f0f0", selectbackground="#005a9e", borderwidth=0, highlightthickness=0)
        self.listbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5) # padx, pady 추가
        
        # 스크롤바 추가
        self.listbox_scroll_y = ttk.Scrollbar(self, orient="vertical", command=self.listbox.yview)
        self.listbox_scroll_y.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=self.listbox_scroll_y.set)

        # 컨트롤 프레임 (추가/삭제)
        control_frame = ttk.Frame(self, style='TFrame') # 배경색 통일을 위해 style 적용
        control_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=(5,0)) # columnspan=2로 스크롤바 영역까지 확장

        # Combobox 스타일 적용
        self.action_type_combo = ttk.Combobox(control_frame, state="readonly", values=[
            "Mouse Move", "Coordinate Click", "Mouse Double Click", "Mouse Click", "Key Input"
        ], style='TCombobox') # TCombobox 스타일 적용
        self.action_type_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.action_type_combo.set("Mouse Click")
        
        ttk.Button(control_frame, text="Add", command=self.add_action).pack(side=tk.LEFT)
        ttk.Button(control_frame, text="Remove", command=self.remove_action).pack(side=tk.LEFT, padx=5)

    def load_condition(self, condition):
        self.current_condition = condition
        self.update_listbox()
        
    def update_listbox(self):
        self.listbox.delete(0, tk.END)
        if self.current_condition:
            for action in self.current_condition.actions:
                params_str = str(action.params)
                self.listbox.insert(tk.END, f"  {action.type} - {params_str}")
                
    def add_action(self):
        if not self.current_condition: return
        action_type = self.action_type_combo.get()
        new_action = Action(action_type=action_type)
        self.current_condition.add_action(new_action)
        self.update_listbox()
        print(f"UI: Added Action '{action_type}' to Condition '{self.current_condition.type}'")
        
    def remove_action(self):
        if not self.current_condition or not self.listbox.curselection(): return
        selected_index = self.listbox.curselection()[0]
        del self.current_condition.actions[selected_index]
        self.update_listbox()
        print(f"UI: Removed action at index {selected_index}.")