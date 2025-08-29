# AutomationProject/core/recorder.py
import time
import threading
from pynput import mouse, keyboard
import win32gui
import win32process
import psutil
import pydirectinput

from data.models import Action

class Recorder(threading.Thread):
    def __init__(self, process_name, stop_key=keyboard.Key.esc, callback=None):
        super().__init__(daemon=True)
        self.process_name = process_name
        self.stop_key = stop_key
        self.callback = callback
        self.events = []
        self._mouse_listener = None
        self._keyboard_listener = None
        self.start_time = time.time()
        self.last_move_pos = None

    def get_client_rect_abs(self, hwnd):
        if not win32gui.IsWindow(hwnd): return None
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        client_origin = win32gui.ClientToScreen(hwnd, (left, top))
        client_end = win32gui.ClientToScreen(hwnd, (right, bottom))
        return (client_origin[0], client_origin[1], client_end[0], client_end[1])

    def find_target_window_at_pos(self, x, y):
        target_pids = {p.info['pid'] for p in psutil.process_iter(['pid', 'name']) if p.info['name'].lower() == self.process_name.lower()}
        if not target_pids: return None
        hwnd = win32gui.WindowFromPoint((x, y))
        while hwnd:
            try:
                if not win32gui.IsWindowVisible(hwnd) or not win32gui.GetWindowText(hwnd):
                    hwnd = win32gui.GetParent(hwnd)
                    continue
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid in target_pids:
                    client_rect_abs = self.get_client_rect_abs(hwnd)
                    if client_rect_abs and (client_rect_abs[0] <= x < client_rect_abs[2]) and (client_rect_abs[1] <= y < client_rect_abs[3]):
                        return {'hwnd': hwnd, 'rect': client_rect_abs}
            except Exception: pass
            hwnd = win32gui.GetParent(hwnd)
        return None

    def on_move(self, x, y):
        self.last_move_pos = (x, y)

    def on_click(self, x, y, button, pressed):
        if pressed:
            window_info = self.find_target_window_at_pos(x, y)
            if window_info:
                if self.last_move_pos:
                    self.events.append({
                        'time': time.time() - 0.01,
                        'type': 'move',
                        'pos': self.last_move_pos,
                        'window_info': window_info
                    })
                    self.last_move_pos = None

                self.events.append({
                    'time': time.time(),
                    'type': 'click',
                    'button': button,
                    'pos': (x, y),
                    'window_info': window_info
                })
            else:
                print(f"Info: Click at ({x},{y}) ignored (outside target window).")

    def on_press(self, key):
        if key == self.stop_key:
            self.stop()
            return False
        self.events.append({'time': time.time(), 'type': 'key', 'key': key})

    def run(self):
        self.start_time = time.time()
        pydirectinput.FAILSAFE = False
        with mouse.Listener(on_click=self.on_click, on_move=self.on_move) as m_listener, \
             keyboard.Listener(on_press=self.on_press) as k_listener:
            self._mouse_listener = m_listener
            self._keyboard_listener = k_listener
            k_listener.join()
            m_listener.join()

    def stop(self):
        if self._keyboard_listener: self._keyboard_listener.stop()
        if self._mouse_listener: self._mouse_listener.stop()
        self._process_events()

    def _process_events(self):
        if not self.events:
            if self.callback: self.callback([])
            return

        # <<< 수정: 모든 이벤트를 시간순으로 먼저 정렬하여 순서 보장 >>>
        self.events.sort(key=lambda e: e['time'])

        actions = []
        last_event_time = self.start_time

        text_buffer = ""
        text_buffer_start_time = 0

        # 텍스트 버퍼를 비우고 Action으로 변환하는 헬퍼 함수
        def flush_text_buffer():
            nonlocal text_buffer, last_event_time
            if text_buffer:
                delay = text_buffer_start_time - last_event_time
                if delay < 0: delay = 0
                actions.append(Action("Key Input", {'delay': round(delay, 2), 'text': text_buffer}))
                # 마지막 이벤트 시간은 텍스트 입력이 시작된 시간으로 설정
                last_event_time = text_buffer_start_time
                text_buffer = ""

        for event in self.events:
            # 현재 이벤트가 키 입력이 아니면, 이전에 쌓인 텍스트 버퍼를 먼저 처리
            if event['type'] != 'key':
                flush_text_buffer()

            delay = event['time'] - last_event_time
            if delay < 0: delay = 0
            action_params = {'delay': round(delay, 2)}

            if event['type'] == 'move':
                win_rect = event['window_info']['rect']
                rx = event['pos'][0] - win_rect[0]
                ry = event['pos'][1] - win_rect[1]
                action_params['relative_pos'] = (rx, ry)
                action_params['target_type'] = 'relative'
                actions.append(Action("Mouse Move", action_params))

            elif event['type'] == 'click':
                win_rect = event['window_info']['rect']
                rx = event['pos'][0] - win_rect[0]
                ry = event['pos'][1] - win_rect[1]
                action_params['relative_pos'] = (rx, ry)
                action_params['button'] = str(event['button'])
                action_params['target_type'] = 'relative'
                action_params['__event_time'] = event['time'] # 더블클릭 시간 비교용 임시 저장
                actions.append(Action("Mouse Click", action_params))

            elif event['type'] == 'key':
                key = event['key']
                if hasattr(key, 'char') and key.char is not None:
                    if not text_buffer:
                        text_buffer_start_time = event['time']
                    text_buffer += key.char
                else:
                    flush_text_buffer() # 특수키 입력 전에 버퍼 비우기
                    delay = event['time'] - last_event_time
                    action_params = {'delay': round(delay, 2)}
                    action_params['key'] = str(key).replace("Key.", "")
                    actions.append(Action("Key Special", action_params))

            last_event_time = event['time']

        flush_text_buffer()

        # 더블클릭 처리 (모든 Action 생성 후 후처리)
        final_actions = []
        i = 0
        while i < len(actions):
            current_action = actions[i]
            if current_action.type == "Mouse Click" and i + 1 < len(actions):
                next_action = actions[i+1]
                if next_action.type == "Mouse Click":
                    # __event_time을 사용하여 정확한 시간차 계산
                    time_diff = next_action.params.get('__event_time', 0) - current_action.params.get('__event_time', 0)
                    pos1 = current_action.params['relative_pos']
                    pos2 = next_action.params['relative_pos']
                    dist_sq = (pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2

                    if time_diff < 0.4 and dist_sq < 25:
                        current_action.type = "Mouse Double Click"
                        final_actions.append(current_action)
                        i += 2 # 두 개를 하나로 합쳤으므로 인덱스 2 증가
                        continue
            final_actions.append(current_action)
            i += 1
        
        # 임시 키 제거
        for action in final_actions:
            if '__event_time' in action.params:
                del action.params['__event_time']

        if self.callback:
            self.callback(final_actions)