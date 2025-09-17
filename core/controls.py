# AutomationProject/core/controls.py
import time
import threading # stop_event를 위해 추가
import pydirectinput

pydirectinput.PAUSE = 0.05

# <<< stop_event 파라미터 추가 >>>
def execute_action_sequence(actions, target_window, stop_event=None):
    """
    주어진 Action 리스트를 순차적으로 실행합니다.
    stop_event가 설정되면 각 Action 실행 전에 중지 여부를 확인합니다.
    """
    if stop_event is None:
        stop_event = threading.Event() # 기본값 설정

    window_rect = target_window['rect']
    print(f"CONTROL: Executing actions for window '{target_window['title']}' Client Rect: {window_rect}")

    for action in actions:
        # <<< Action 실행 전, 중지 신호 확인 >>>
        if stop_event.is_set():
            print("CONTROL: Stop event received, halting action sequence.")
            return

        time.sleep(action.params.get('delay', 0.1))

        action_type = action.type
        params = action.params
        
        if "Mouse" in action_type:
            target_abs_x, target_abs_y = None, None

            if params.get('target_type') == 'relative' and 'relative_pos' in params and window_rect:
                rx, ry = params['relative_pos']
                target_abs_x = window_rect[0] + rx
                target_abs_y = window_rect[1] + ry
            
            elif 'abs_pos' in params:
                target_abs_x, target_abs_y = params['abs_pos']

            if target_abs_x is not None and target_abs_y is not None:
                pydirectinput.moveTo(target_abs_x, target_abs_y)

                if action_type in ["Mouse Click", "Mouse Double Click"]:
                    time.sleep(1.0)
                
                if stop_event.is_set():
                    print("CONTROL: Stop event received, halting action sequence.")
                    return

                if action_type == "Mouse Click":
                    pydirectinput.click()
                    print(f"  - Clicked at ({target_abs_x}, {target_abs_y})")
                elif action_type == "Mouse Double Click":
                    pydirectinput.doubleClick()
                    print(f"  - Double Clicked at ({target_abs_x}, {target_abs_y})")
            else:
                 print(f"  - WARNING: Could not calculate coordinates for {action_type}. Skipping mouse action.")

        elif action_type == "Key Input":
            text = params.get('text', '')
            if text:
                pydirectinput.write(text, interval=0.01)
                print(f"  - Typed '{text}'")
        elif action_type == "Key Special":
            key_name = params.get('key', '')
            if key_name:
                pydirectinput.press(key_name)
                print(f"  - Pressed special key '{key_name}'")