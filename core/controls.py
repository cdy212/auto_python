# AutomationProject/core/controls.py
import time

def execute_action_sequence(actions, target_window):
    """
    주어진 Action 리스트를 순차적으로 실행합니다.
    :param actions: 실행할 Action 객체들의 리스트
    :param target_window: Condition이 충족된 창의 정보 (제목, 좌표 등)
    """
    window_rect = target_window['rect'] # Action의 기준이 될 창의 좌표
    print(f"CONTROL: Executing actions for window '{target_window['title']}' at {window_rect}")

    for action in actions:
        if action.type == "Mouse Click":
            # action.params에 {'rx': 50, 'ry': 100} 과 같은 상대 좌표가 있다면,
            # 아래와 같이 절대 좌표를 계산하여 사용합니다.
            # target_x = window_rect[0] + action.params.get('rx', 0)
            # target_y = window_rect[1] + action.params.get('ry', 0)
            
            # 현재는 로그만 남김
            print(f"CONTROL: Executing {action.type} with params {action.params}")
            time.sleep(0.5) # 실제 Action처럼 딜레이를 줌
        
        # ... 다른 Action 타입들에 대한 처리 ...