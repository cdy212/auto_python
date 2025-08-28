# AutomationProject/main.py
import tkinter as tk
from ui.main_view import AutomationUI
import pygetwindow as gw
import ctypes

if __name__ == "__main__":
    # <<< 수정: DPI 인식 설정 추가 >>>
    # Windows 배율 설정에 따른 좌표 왜곡 문제를 해결합니다.
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception as e:
        print(f"Warning: Could not set DPI awareness. Coordinates may be incorrect on scaled displays. Error: {e}")

    gw.FAILSAFE = False
    root = tk.Tk()
    app = AutomationUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()