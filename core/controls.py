# AutomationProject/core/controls.py
import time
import pydirectinput

pydirectinput.PAUSE = 0.05

def execute_action_sequence(actions, target_window):
    """
    주어진 Action 리스트를 순차적으로 실행합니다.
    """
    window_rect = target_window['rect']
    print(f"CONTROL: Executing actions for window '{target_window['title']}' Client Rect: {window_rect}")

    for action in actions:
        time.sleep(action.params.get('delay', 0.1))

        action_type = action.type
        params = action.params
        
        # <<< 수정: 마우스 동작 Action일 경우에만 좌표 계산 및 이동을 수행하도록 로직 변경 >>>
        if "Mouse" in action_type:
            target_abs_x, target_abs_y = None, None

            if params.get('target_type') == 'relative' and 'relative_pos' in params and window_rect:
                rx, ry = params['relative_pos']
                target_abs_x = window_rect[0] + rx
                target_abs_y = window_rect[1] + ry
                print(f"  - Relative target: ({rx}, {ry}) -> Absolute: ({target_abs_x}, {target_abs_y})")
            
            elif 'abs_pos' in params:
                target_abs_x, target_abs_y = params['abs_pos']
                print(f"  - Fallback to Absolute target: ({target_abs_x}, {target_abs_y})")

            if target_abs_x is not None and target_abs_y is not None:
                pydirectinput.moveTo(target_abs_x, target_abs_y)

                if action_type == "Mouse Click":
                    pydirectinput.click()
                    print(f"  - Clicked at ({target_abs_x}, {target_abs_y})")
                elif action_type == "Mouse Double Click":
                    pydirectinput.doubleClick()
                    print(f"  - Double Clicked at ({target_abs_x}, {target_abs_y})")
            else:
                 # 좌표 계산에 실패한 경우
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