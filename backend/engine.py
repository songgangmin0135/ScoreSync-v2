import os
import fitz  # PyMuPDF
import cv2
import numpy as np
from moviepy import ImageClip, concatenate_videoclips

class ScoreSyncEngine:
    def __init__(self, bpm):
        self.bpm = bpm
        self.temp_dir = "temp_slices"
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

    def slice_pdf_to_lines(self, pdf_file):
        """PDF를 고해상도로 읽어 악보의 줄을 정밀하게 추출합니다."""
        # PDF 읽기 (기존보다 해상도를 3배 높임)
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        line_paths = []
        
        for p_idx in range(len(doc)):
            page = doc.load_page(p_idx)
            # Matrix(3, 3)으로 렌더링하여 작은 음표도 깨지지 않게 함
            pix = page.get_pixmap(matrix=fitz.Matrix(3, 3)) 
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.h, pix.w, 3))
            
            # 전처리: 그레이스케일 -> 이진화 (임계값 230으로 상향하여 배경 노이즈 제거)
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            _, binary = cv2.threshold(gray, 230, 255, cv2.THRESH_BINARY_INV)
            
            # 가로 픽셀 합계 계산
            h_sum = np.sum(binary, axis=1)
            # 줄로 판정할 최소 픽셀 (전체 너비의 5% 이상 콘텐츠가 있는 경우)
            is_line = h_sum > (pix.w * 0.05)
            
            # 연속된 영역 추출
            changes = np.where(is_line[:-1] != is_line[1:])[0]
            for i in range(0, len(changes), 2):
                if i+1 < len(changes):
                    top, bottom = changes[i], changes[i+1]
                    # 너무 짧은 영역(노이즈)은 무시
                    if (bottom - top) < 30: continue 
                    
                    # 위아래 여백을 넉넉히 주어 음표 꼬리가 잘리지 않게 함
                    margin = 60
                    y1 = max(0, top - margin)
                    y2 = min(pix.h, bottom + margin)
                    
                    line_img = img[y1:y2, :]
                    path = f"{self.temp_dir}/line_{p_idx}_{i}.png"
                    cv2.imwrite(path, cv2.cvtColor(line_img, cv2.COLOR_RGB2BGR))
                    line_paths.append(path)
        return line_paths

    def assemble_and_render(self, line_paths, cuts_info, lines_per_screen, output_name):
        """MoviePy 최신 버전 문법에 맞춰 영상을 합성합니다."""
        clips = []
        for idx, cut in enumerate(cuts_info):
            if cut.get('img') and os.path.exists(cut['img']):
                duration = (60 / self.bpm) * cut['beats']
                # MoviePy 2.0+ 에서는 생성자에서 duration과 fps를 지정하는 것이 안전합니다.
                clip = ImageClip(cut['img'], duration=duration).with_fps(24)
                clips.append(clip)
        
        if not clips:
            return None

        final_video = concatenate_videoclips(clips, method="compose")
        output_path = f"{output_name}.mp4"
        # libx264 코덱을 명시하여 대부분의 플레이어에서 재생 가능하게 함
        final_video.write_videofile(output_path, fps=24, codec="libx264", audio=False)
        return output_path

