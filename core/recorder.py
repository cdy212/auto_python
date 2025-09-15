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

        self.events.sort(key=lambda e: e['time'])

        actions = []
        last_event_time = self.start_time

        text_buffer = ""
        text_buffer_start_time = 0

        def flush_text_buffer():
            nonlocal text_buffer, last_event_time
            if text_buffer:
                delay = text_buffer_start_time - last_event_time
                if delay < 0: delay = 0
                actions.append(Action("Key Input", {'delay': round(delay, 2), 'text': text_buffer}))
                last_event_time = text_buffer_start_time
                text_buffer = ""

        for event in self.events:
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
                action_params['__event_time'] = event['time']
                actions.append(Action("Mouse Click", action_params))

            elif event['type'] == 'key':
                key = event['key']
                if hasattr(key, 'char') and key.char is not None:
                    if not text_buffer:
                        text_buffer_start_time = event['time']
                    text_buffer += key.char
                else:
                    flush_text_buffer()
                    delay = event['time'] - last_event_time
                    action_params = {'delay': round(delay, 2)}
                    action_params['key'] = str(key).replace("Key.", "")
                    actions.append(Action("Key Special", action_params))

            last_event_time = event['time']

        flush_text_buffer()

        final_actions = []
        i = 0
        while i < len(actions):
            current_action = actions[i]
            if current_action.type == "Mouse Click" and i + 1 < len(actions):
                next_action = actions[i+1]
                if next_action.type == "Mouse Click":
                    time_diff = next_action.params.get('__event_time', 0) - current_action.params.get('__event_time', 0)
                    pos1 = current_action.params['relative_pos']
                    pos2 = next_action.params['relative_pos']
                    dist_sq = (pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2

                    if time_diff < 0.4 and dist_sq < 25:
                        current_action.type = "Mouse Double Click"
                        final_actions.append(current_action)
                        i += 2
                        continue
            final_actions.append(current_action)
            i += 1
        
        for action in final_actions:
            if '__event_time' in action.params:
                del action.params['__event_time']

        # <<< 수정: Mouse Move와 Click/Double Click을 하나의 'Click'으로 병합 >>>
        merged_actions = []
        i = 0
        while i < len(final_actions):
            current_action = final_actions[i]
            
            # 다음 액션이 있는지, 현재 액션이 Mouse Move인지 확인
            if current_action.type == "Mouse Move" and i + 1 < len(final_actions):
                next_action = final_actions[i+1]
                
                # 다음 액션이 같은 위치의 Click 또는 Double Click인지 확인
                if next_action.type in ["Mouse Click", "Mouse Double Click"]:
                    pos1 = current_action.params.get('relative_pos')
                    pos2 = next_action.params.get('relative_pos')
                    if pos1 and pos2 and pos1 == pos2:
                        # Move의 delay를 Click의 delay로 합산하여 이전 액션과의 전체 지연 시간 유지
                        click_delay = next_action.params.get('delay', 0)
                        move_delay = current_action.params.get('delay', 0)
                        next_action.params['delay'] = round(move_delay + click_delay, 2)

                        # Click 액션만 추가하고, Move 액션은 건너뜀
                        merged_actions.append(next_action)
                        i += 2 # 두 개의 액션을 처리했으므로 인덱스 2 증가
                        continue
                        
            # 병합 대상이 아니면 현재 액션만 추가
            merged_actions.append(current_action)
            i += 1

        if self.callback:
            self.callback(merged_actions)