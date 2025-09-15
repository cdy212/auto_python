# AutomationProject/main.py
import tkinter as tk
from ui.main_view import AutomationUI
import pygetwindow as gw
import ctypes
import sys
import traceback
import logging
from datetime import datetime
import os

# --- 전역 에러 로깅 설정 ---

LOG_FILE = "error_log.txt"
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=LOG_FILE,
    filemode='a',
    encoding='utf-8'
)

ui_log_func = None

def handle_exception(exc_type, exc_value, exc_traceback):
    sys.__excepthook__(exc_type, exc_value, exc_traceback)
    error_message = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logging.error("Unhandled exception:\n" + error_message)
    if ui_log_func:
        ui_log_func(f"💥 UNHANDLED ERROR:\n{error_message}")

# <<< Logger 클래스 수정 >>>
class Logger:
    def __init__(self, widget, original_stream):
        self.widget = widget
        self.original_stream = original_stream

    def write(self, text):
        # original_stream이 None이 아닐 때만 콘솔에 출력
        if self.original_stream:
            self.original_stream.write(text)
            self.original_stream.flush()
        
        if ui_log_func:
            if text.strip():
                ui_log_func(text)

    def flush(self):
        if self.original_stream:
            self.original_stream.flush()

if __name__ == "__main__":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        print("DPI Awareness set to Per-Monitor V2.")
    except AttributeError:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
            print("DPI Awareness set to System-Aware.")
        except Exception as e:
            print(f"Warning: Could not set DPI awareness. Error: {e}")

    sys.excepthook = handle_exception

    gw.FAILSAFE = False
    root = tk.Tk()
    app = AutomationUI(root)
    
    ui_log_func = app.log

    sys.stdout = Logger(app.log_text, sys.stdout)
    sys.stderr = Logger(app.log_text, sys.stderr)

    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    try:
        root.mainloop()
    except Exception as e:
        handle_exception(type(e), e, e.__traceback__)