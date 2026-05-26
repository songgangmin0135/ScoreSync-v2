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

    def _has_staff_lines(self, region_gray):
        """
        오선보(5개 수평선) 패턴이 존재하는지 감지합니다.
        제목/작곡가 텍스트 영역과 실제 악보 영역을 구분하는 핵심 로직입니다.
        
        원리: 악보의 오선은 가로 방향으로 매우 길고 얇은 직선이 5개가 
        일정 간격으로 반복됩니다. 수평 모폴로지 연산으로 긴 수평선만 
        추출한 뒤, 수직 투영에서 5개 이상의 피크가 등간격으로 나타나면 
        오선보로 판정합니다.
        """
        _, bw = cv2.threshold(region_gray, 200, 255, cv2.THRESH_BINARY_INV)
        
        # 수평 방향으로 긴 직선만 남기는 모폴로지 연산
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (region_gray.shape[1] // 4, 1))
        horizontal_lines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, h_kernel)
        
        # 세로 방향 투영: 각 행(row)에 수평선 픽셀이 얼마나 있는지
        v_proj = np.sum(horizontal_lines, axis=1)
        threshold = region_gray.shape[1] * 0.3  # 가로 폭의 30% 이상이면 수평선
        peaks = v_proj > threshold
        
        # 연속된 피크 수 카운트 (5개 이상이면 오선보)
        peak_count = 0
        in_peak = False
        for val in peaks:
            if val and not in_peak:
                peak_count += 1
                in_peak = True
            elif not val:
                in_peak = False
        
        return peak_count >= 4  # 최소 4선 이상 감지되면 오선보로 판정

    def _normalize_slices(self, line_images):
        """
        모든 슬라이스 이미지의 가로/세로 크기를 통일합니다.
        가장 큰 세로 높이와 가장 넓은 가로 폭을 기준으로,
        모든 이미지에 중앙 정렬 기준 흰색 패딩(White Padding)을 입힙니다.
        """
        if not line_images:
            return line_images
        
        # 전체 슬라이스에서 최대 높이와 최대 너비 결정
        max_h = max(img.shape[0] for img in line_images)
        max_w = max(img.shape[1] for img in line_images)
        
        normalized = []
        for img in line_images:
            h, w = img.shape[:2]
            
            # 흰색(255) 캔버스 생성
            canvas = np.full((max_h, max_w, 3), 255, dtype=np.uint8)
            
            # 원본 이미지를 캔버스 중앙에 배치
            y_offset = (max_h - h) // 2
            x_offset = (max_w - w) // 2
            canvas[y_offset:y_offset + h, x_offset:x_offset + w] = img
            
            normalized.append(canvas)
        
        return normalized

    def slice_pdf_to_lines(self, pdf_file, skip_header=True):
        """
        PDF를 고해상도로 읽어 악보의 줄을 정밀하게 추출합니다.
        
        Args:
            pdf_file: PDF 파일 객체
            skip_header: True이면 첫 페이지의 제목/작곡가 등 
                         비-악보 헤더 영역을 자동으로 건너뜁니다.
        """
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        raw_images = []   # 정규화 전 원본 이미지 리스트
        is_first_staff_found = False  # 첫 번째 오선보 발견 여부
        
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
                    
                    # === 기능 1: 헤더(제목/작곡가) 자동 제외 ===
                    if skip_header and p_idx == 0 and not is_first_staff_found:
                        region_gray = cv2.cvtColor(line_img, cv2.COLOR_RGB2GRAY)
                        if not self._has_staff_lines(region_gray):
                            # 오선보가 없는 영역 → 제목/작곡가 텍스트 → 건너뜀
                            continue
                        else:
                            is_first_staff_found = True
                    
                    raw_images.append(line_img)
        
        # === 기능 2: 모든 슬라이스 크기/비율 통일 (White Padding) ===
        normalized_images = self._normalize_slices(raw_images)
        
        # 정규화된 이미지를 디스크에 저장
        line_paths = []
        for idx, norm_img in enumerate(normalized_images):
            path = f"{self.temp_dir}/line_{idx:04d}.png"
            cv2.imwrite(path, cv2.cvtColor(norm_img, cv2.COLOR_RGB2BGR))
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

