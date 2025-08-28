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

    def get_client_rect_abs(self, hwnd):
        """hWnd의 클라이언트 영역(테두리/제목표시줄 제외) 절대 화면 좌표를 반환합니다."""
        if not win32gui.IsWindow(hwnd):
            return None
        
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        client_origin = win32gui.ClientToScreen(hwnd, (left, top))
        client_end = win32gui.ClientToScreen(hwnd, (right, bottom))
        
        return (client_origin[0], client_origin[1], client_end[0], client_end[1])

    def find_target_window_at_pos(self, x, y):
        """지정된 좌표(x, y)에 있는 타겟 프로세스의 창 정보를 반환합니다."""
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
                    # <<< 수정: 클릭 좌표가 클라이언트 영역 내에 있는지 확인 >>>
                    if client_rect_abs and (client_rect_abs[0] <= x < client_rect_abs[2]) and (client_rect_abs[1] <= y < client_rect_abs[3]):
                        return {'hwnd': hwnd, 'rect': client_rect_abs}
            except Exception:
                pass
            hwnd = win32gui.GetParent(hwnd)
        return None

    def on_click(self, x, y, button, pressed):
        if pressed:
            window_info = self.find_target_window_at_pos(x, y)
            
            # <<< 수정: 반드시 타겟 프로세스 창 안에서 클릭했을 때만 이벤트를 기록합니다. >>>
            if window_info:
                self.events.append({
                    'time': time.time(),
                    'type': 'click',
                    'button': button,
                    'pos': (x, y),
                    'window_info': window_info
                })
            else:
                print(f"Info: Click at ({x},{y}) ignored (outside target process window).")


    def on_press(self, key):
        if key == self.stop_key:
            self.stop()
            return False

        self.events.append({
            'time': time.time(),
            'type': 'key',
            'key': key
        })

    def run(self):
        self.start_time = time.time()
        pydirectinput.FAILSAFE = False
        with mouse.Listener(on_click=self.on_click) as m_listener, \
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
        
        actions = []
        last_event_time = self.start_time
        
        i = 0
        while i < len(self.events):
            event = self.events[i]
            delay = event['time'] - last_event_time
            if delay < 0: delay = 0
            
            action_params = {'delay': round(delay, 2)}
            action_type = None

            if event['type'] == 'click' and i + 1 < len(self.events) and self.events[i+1]['type'] == 'click':
                next_event = self.events[i+1]
                if abs(next_event['pos'][0] - event['pos'][0]) < 5 and \
                   abs(next_event['pos'][1] - event['pos'][1]) < 5 and \
                   (next_event['time'] - event['time']) < 0.4:
                    action_type = "Mouse Double Click"
                    i += 1
            elif event['type'] == 'click':
                action_type = "Mouse Click"

            if action_type:
                action_params['button'] = str(event['button'])
                # <<< 수정: 이제 window_info는 항상 존재하므로, 상대 좌표만 저장합니다. >>>
                win_rect = event['window_info']['rect']
                relative_x = event['pos'][0] - win_rect[0]
                relative_y = event['pos'][1] - win_rect[1]
                action_params['target_type'] = 'relative'
                action_params['relative_pos'] = (relative_x, relative_y)
                actions.append(Action(action_type, action_params))

            elif event['type'] == 'key':
                # (키 입력 병합 로직은 이전과 동일)
                # ... (생략) ...
                text_sequence = ""; key_events_in_sequence = []
                j = i
                while j < len(self.events) and self.events[j]['type'] == 'key':
                    current_key_event = self.events[j]; key = current_key_event['key']
                    try: text_sequence += key.char; key_events_in_sequence.append(current_key_event)
                    except AttributeError:
                        if text_sequence:
                            first_seq_time = key_events_in_sequence[0]['time'] if key_events_in_sequence else current_key_event['time']
                            actions.append(Action("Key Input", {'delay': round(first_seq_time - last_event_time, 2), 'text': text_sequence}))
                            last_event_time = first_seq_time + (key_events_in_sequence[-1]['time'] - first_seq_time) if key_events_in_sequence else current_key_event['time']
                            text_sequence = ""; key_events_in_sequence = []
                        actions.append(Action("Key Special", {'delay': round(current_key_event['time'] - last_event_time, 2), 'key': str(key).replace("Key.", "")}))
                        last_event_time = current_key_event['time']
                    j += 1
                if text_sequence:
                    first_seq_time = key_events_in_sequence[0]['time'] if key_events_in_sequence else event['time']
                    actions.append(Action("Key Input", {'delay': round(first_seq_time - last_event_time, 2), 'text': text_sequence}))
                    last_event_time = first_seq_time + (key_events_in_sequence[-1]['time'] - first_seq_time) if key_events_in_sequence else event['time']
                i = j - 1
            
            last_event_time = event['time']
            i += 1

        if self.callback:
            self.callback(actions)