# AutomationProject/core/controls.py1
import time
import pydirectinput

pydirectinput.PAUSE = 0.05

def execute_action_sequence(actions, target_window):
    window_rect = target_window['rect']
    print(f"CONTROL: Executing actions for window '{target_window['title']}' Client Rect: {window_rect}")

    for action in actions:
        time.sleep(action.params.get('delay', 0.1))

        action_type = action.type
        params = action.params
        
        target_abs_x, target_abs_y = None, None

        # <<< 수정: 이제 target_type은 항상 'relative'라고 가정하고 처리 >>>
        if params.get('target_type') == 'relative' and 'relative_pos' in params and window_rect:
            rx, ry = params['relative_pos']
            target_abs_x = window_rect[0] + rx
            target_abs_y = window_rect[1] + ry
            print(f"  - Relative target: ({rx}, {ry}) -> Absolute: ({target_abs_x}, {target_abs_y})")
        
        # 'abs_pos'는 이제 사용하지 않으므로 관련 로직 제거 가능 (안정성을 위해 유지)
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