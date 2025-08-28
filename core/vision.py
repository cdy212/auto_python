import cv2
import numpy as np
from PIL import ImageGrab

def find_image_in_area(image_path, bbox, threshold=0.8):
    """
    지정된 영역(bbox) 내부에서 템플릿 이미지를 찾아 유사도를 확인합니다.
    :param image_path: 찾을 이미지 파일 경로
    :param bbox: 탐색할 영역의 좌표 (x1, y1, x2, y2)
    :param threshold: 유사도 임계값 (0.0 ~ 1.0)
    :return: (True, (x1, y1, x2, y2), max_val) or (False, None, 0) - 화면 전체 기준 좌표로 반환
    """
    try:
        # 지정된 영역만 스크린샷
        screen = ImageGrab.grab(bbox=bbox)
        screen_np = np.array(screen)
        screen_gray = cv2.cvtColor(screen_np, cv2.COLOR_RGB2GRAY)

        template = cv2.imread(image_path, 0)
        if template is None:
            print(f"Vision Error: Template image not found at {image_path}")
            return False, None, 0

        h, w = template.shape
        res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if max_val >= threshold:
            # 발견된 좌표는 스크린샷 내부의 상대 좌표이므로,
            # bbox의 시작점을 더해 화면 전체 기준의 절대 좌표로 변환
            abs_x1 = bbox[0] + max_loc[0]
            abs_y1 = bbox[1] + max_loc[1]
            abs_x2 = abs_x1 + w
            abs_y2 = abs_y1 + h
            return True, (abs_x1, abs_y1, abs_x2, abs_y2), max_val
        else:
            return False, None, max_val
            
    except Exception as e:
        print(f"Vision Error in area {bbox}: {e}")
        return False, None, 0