# AutomationProject/main.py
import tkinter as tk
from ui.main_view import AutomationUI
import pygetwindow as gw
import ctypes

if __name__ == "__main__":
    # <<< 수정: DPI 인식 설정을 다시 활성화하고 v2로 강화합니다. >>>
    # এটি Windows স্কেলিং সমস্যা সমাধান করে।
    try:
        # Per-Monitor DPI Aware v2 (Windows 10 Creators Update 이상)
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        print("DPI Awareness set to Per-Monitor V2.")
    except AttributeError:
        # 이전 버전 Windows 호환용
        try:
            ctypes.windll.user32.SetProcessDPIAware()
            print("DPI Awareness set to System-Aware.")
        except Exception as e:
            print(f"Warning: Could not set DPI awareness. Error: {e}")

    gw.FAILSAFE = False
    root = tk.Tk()
    app = AutomationUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()