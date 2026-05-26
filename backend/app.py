import streamlit as st
import os
from engine import ScoreSyncEngine

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="ScoreSync Studio", layout="wide")

# CSS: 프리뷰 레이어(Z-index) 고정 및 디자인 개선
st.markdown("""
    <style>
    .block-container { padding-top: 5rem; }
    /* [해결] Streamlit Native Column Sticky 속성 주입 */
    [data-testid="stColumn"]:nth-of-type(1) {
        position: sticky;
        top: 5rem;
        z-index: 99;
        align-self: flex-start;
    }
    
    /* 프리뷰 컨테이너: 배경 위에 이미지가 오도록 설정 */
    .preview-container {
        position: relative; 
        width: 100%; 
        border-radius: 15px; 
        overflow: hidden; 
        border: 2px solid #333;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    .preview-bg { 
        position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; 
    }
    
    .preview-score-wrapper {
        position: absolute;
        width: 100%;
        height: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        z-index: 10;
        gap: 15px;
        box-sizing: border-box;
    }
    .wrapper-pos-top { justify-content: flex-start; padding-top: 10%; }
    .wrapper-pos-center { justify-content: center; }
    .wrapper-pos-bottom { justify-content: flex-end; padding-bottom: 10%; }

    .preview-score, .preview-dummy {
        width: 90%; 
        transform: scale(var(--img-scale, 1.0));
        transition: transform 0.2s ease;
    }
    .preview-score {
        filter: drop-shadow(0 0 5px rgba(0,0,0,0.1));
    }
    .preview-dummy {
        background-color: rgba(255, 255, 255, 0.8);
        border: 2px dashed #666;
        border-radius: 10px;
        height: 15%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        color: #333;
        font-size: 1.2rem;
    }

    /* 타임라인 카드 디자인 */
    .cut-card { 
        background: #FFFFFF; border: 2px solid #EEE; border-radius: 12px; 
        padding: 15px; margin-bottom: 12px; 
    }
    .selected-card { 
        border-color: #E74C3C !important; 
        background: #FFF5F4 !important; 
        box-shadow: 0 4px 12px rgba(231, 76, 60, 0.1);
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. 세션 상태 초기화 ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'bpm' not in st.session_state: st.session_state.bpm = 60
if 'title' not in st.session_state: st.session_state.title = "Score_Project"
if 'cuts' not in st.session_state: st.session_state.cuts = []
if 'current_idx' not in st.session_state: st.session_state.current_idx = 0
if 'color_val' not in st.session_state: st.session_state.color_val = "검은색"
if 'score_position' not in st.session_state: st.session_state.score_position = "중앙"
if 'time_signature' not in st.session_state: st.session_state.time_signature = "4/4"
if 'aspect_ratio' not in st.session_state: st.session_state.aspect_ratio = "16:9 가로 화면"
if 'lines_per_screen' not in st.session_state: st.session_state.lines_per_screen = 1
if 'image_scale' not in st.session_state: st.session_state.image_scale = 100
if 'line_gap' not in st.session_state: st.session_state.line_gap = 0

# --- 3. 단계별 로직 ---

# [STEP 1] 설정 및 단일 업로드
if st.session_state.step == 1:
    v_col, e_col = st.columns([5, 5])
    
    with v_col:
        st.markdown("<h3 style='text-align: center;'>화면 렌더링 시뮬레이션</h3>", unsafe_allow_html=True)
        st.write("<br>", unsafe_allow_html=True)
        
        pos_class_map = {"상단": "wrapper-pos-top", "중앙": "wrapper-pos-center", "하단": "wrapper-pos-bottom"}
        pos_class = pos_class_map.get(st.session_state.score_position, "wrapper-pos-center")
        is_916 = "9:16" in st.session_state.aspect_ratio
        ar_css =  "9/16" if is_916 else "16/9"
        max_style = "max-height: 60vh; max-width: 450px; margin: 0 auto; display: flex; align-items: stretch;" if is_916 else "max-width: 100%;"
        
        scale_val = st.session_state.image_scale / 100.0
        
        dummy_items = "\\n".join([f'<div class="preview-dummy">악보 렌더링 구역 ({i+1})</div>' for i in range(st.session_state.lines_per_screen)])
        
        st.markdown(f"""
            <div class="preview-container" style="aspect-ratio: {ar_css}; --img-scale: {scale_val}; {max_style} margin-bottom: 20px; outline: 3px solid #555;">
                <div class="preview-bg" style="background-color: #000000;"></div>
                <div class="preview-score-wrapper {pos_class}">
                    {dummy_items}
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.components.v1.html("""
            <script>
            // Sticky 해킹: 프리뷰 부모 윈도우 스크롤 고정
            setTimeout(function() {
                const doc = window.parent.document;
                const my_anchor = doc.querySelector('.sticky-anchor1');
                if(my_anchor) {
                    const col = my_anchor.closest('[data-testid="column"]');
                    if(col) {
                        col.style.position = 'sticky';
                        col.style.top = '3rem';
                        col.style.alignSelf = 'flex-start';
                        col.style.zIndex = '999';
                    }
                }
            }, 500);
            </script>
        """, height=0)

    with e_col:
        st.title("🎼 ScoreSync Studio")
        st.subheader("초기 설정")
        
        uploaded = st.file_uploader("작업할 PDF 악보를 업로드하세요", type=['pdf'], key="main_loader")
        
        col1, col2 = st.columns(2)
        with col1: st.session_state.title = st.text_input("프로젝트 이름", value=st.session_state.title)
        with col2: st.session_state.bpm = st.number_input("기준 BPM", min_value=30, max_value=300, value=st.session_state.bpm)
        
        col3, col4 = st.columns(2)
        with col3: 
            opt_ts = ["4/4", "3/4", "2/4", "6/8", "9/8", "12/8"]
            st.session_state.time_signature = st.selectbox("박자 정보", opt_ts, index=opt_ts.index(st.session_state.time_signature))
        with col4:
            opt_lines = [1, 2, 3, 4]
            st.session_state.lines_per_screen = st.selectbox("한 화면 악보 줄 수", opt_lines, index=opt_lines.index(st.session_state.lines_per_screen))
            
        col5, col6 = st.columns(2)
        with col5:
            opt_ar = ["16:9 가로 화면", "9:16 세로 화면"]
            st.session_state.aspect_ratio = st.selectbox("화면 비율", opt_ar, index=opt_ar.index(st.session_state.aspect_ratio))
        with col6:
            opt_pos = ["상단", "중앙", "하단"]
            st.session_state.score_position = st.selectbox("악보 렌더링 위치", opt_pos, index=opt_pos.index(st.session_state.score_position))
            
        st.session_state.image_scale = st.slider("악보 이미지 크기 확대/축소 배율 (%)", min_value=50, max_value=150, value=st.session_state.image_scale)
        st.session_state.color_val = "검은색" # 고정
        
        st.write("<br>", unsafe_allow_html=True)
        if st.button("악보 분석 및 편집 시작 🚀", use_container_width=True, type="primary"):
            if uploaded:
                engine = ScoreSyncEngine(st.session_state.bpm)
                with st.spinner("악보의 줄을 정밀 분석 중입니다..."):
                    lines = engine.slice_pdf_to_lines(uploaded)
                    # [해결] FLAT 배열 (개별 이미지 분리) + 기본 BPM 할당
                    st.session_state.cuts = [{"id": i+1, "beats": 16.0, "bpm": st.session_state.bpm, "img": img} for i, img in enumerate(lines)]
                    st.session_state.current_idx = 0 
                    st.session_state.step = 2
                    st.rerun()
            else:
                st.error("분석할 PDF 파일을 업로드해주세요.")

# [STEP 2] 편집 모드
elif st.session_state.step == 2:
    # 플랫 cuts 데이터를 기반으로 화면에 그릴 묶음(scene) 생성
    n = st.session_state.lines_per_screen
    scenes = []
    for i in range(0, len(st.session_state.cuts), n):
        sub_cuts = st.session_state.cuts[i:i+n]
        scenes.append({
            "idx": i // n,
            "scene_beats": sum(c['beats'] for c in sub_cuts),
            "cuts": sub_cuts,
            "start_cut_idx": i
        })
    v_col, e_col = st.columns([5, 5])
    
    # --- 좌측: 고정 프리뷰 ---
    with v_col:
        st.markdown("<h3 style='text-align: center;'>실시간 프리뷰</h3>", unsafe_allow_html=True)
        
        bg_color = "#000000"
        
        # 현재 current_idx(flat index)가 속하는 씬 찾기
        curr_scene_idx = 0
        if scenes:
            curr_scene_idx = min(st.session_state.current_idx // n, len(scenes) - 1)
        curr_scene = scenes[curr_scene_idx] if scenes else None
        
        pos_class_map = {"상단": "wrapper-pos-top", "중앙": "wrapper-pos-center", "하단": "wrapper-pos-bottom"}
        pos_class = pos_class_map.get(st.session_state.score_position, "wrapper-pos-center")
        is_916 = "9:16" in st.session_state.aspect_ratio
        ar_css =  "9/16" if is_916 else "16/9"
        max_style = "max-height: 60vh; max-width: 450px; margin: 0 auto; display: flex; align-items: stretch;" if is_916 else "max-width: 100%;"
        
        scale_val = st.session_state.image_scale / 100.0
        gap_val = st.session_state.line_gap
        
        import base64
        def get_image_base64(path):
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()

        score_html_items = []
        if curr_scene:
            for cut in curr_scene['cuts']:
                img_b64 = get_image_base64(cut['img'])
                score_html_items.append(f"<img src='data:image/png;base64,{img_b64}' class='preview-score'>")
        
        score_html = "\\n".join(score_html_items)

        st.markdown(f"""
            <div class="preview-container" style="aspect-ratio: {ar_css}; --img-scale: {scale_val}; {max_style} margin-bottom: 20px;">
                <div class="preview-bg" style="background-color: {bg_color};"></div>
                <div class="preview-score-wrapper {pos_class}" style="gap: {gap_val}px;">
                    {score_html}
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # 설정들을 프리뷰 아래로 이동
        st.markdown("### 🛠️ 영상 시각 설정 세부 조정")
        st.session_state.image_scale = st.slider("기본 확대/축소 배율 (%)", min_value=50, max_value=150, value=st.session_state.image_scale, key="step2_scale")
        if st.session_state.lines_per_screen > 1:
            st.session_state.line_gap = st.slider("다중 악보 간격 조절 (픽셀)", min_value=0, max_value=200, value=st.session_state.line_gap, key="step2_gap")
        else:
            st.session_state.line_gap = 0
            
        opt_pos = ["상단", "중앙", "하단"]
        st.session_state.score_position = st.selectbox("악보 렌더링 위치", opt_pos, index=opt_pos.index(st.session_state.score_position), key="step2_pos")
        
        # --- 스크러버(재생 바) 구현 ---
        def get_scene_duration(sc):
            return sum((60.0 / c.get('bpm', st.session_state.bpm)) * c['beats'] for c in sc['cuts'])
            
        def update_idx_from_time():
            val = st.session_state.loc_scrubber
            accum = 0.0
            for sc in scenes:
                d = get_scene_duration(sc)
                accum += d
                if val <= accum + 0.001:
                    st.session_state.current_idx = sc['start_cut_idx']
                    break

        total_time_calc = sum(get_scene_duration(sc) for sc in scenes) if scenes else 0.0
        curr_time_calc = sum(get_scene_duration(sc) for sc in scenes[:curr_scene_idx]) if scenes else 0.0
        st.session_state.loc_scrubber = float(curr_time_calc)
        
        st.write("<br>", unsafe_allow_html=True)
        st.slider("영상 탐색 시뮬레이터 (초)", min_value=0.0, max_value=float(max(0.1, total_time_calc)), key="loc_scrubber", on_change=update_idx_from_time)
        
        st.write("<br>", unsafe_allow_html=True)
        if st.button("최종 영상 렌더링", use_container_width=True, type="primary"):
            st.session_state.step = 3
            st.rerun()

        st.components.v1.html("""
            <script>
            // Sticky 전용 해킹 (left column fixed)
            setTimeout(function() {
                const doc = window.parent.document;
                const my_anchor = doc.querySelector('.sticky-anchor2');
                if(my_anchor) {
                    const col = my_anchor.closest('[data-testid="column"]');
                    if(col) {
                        col.style.position = 'sticky';
                        col.style.top = '3rem';
                        col.style.alignSelf = 'flex-start';
                        col.style.zIndex = '999';
                    }
                }
            }, 500);
            </script>
        """, height=0)

    # --- 우측: 스크롤 타임라인 ---
    with e_col:
        st.write("<br>", unsafe_allow_html=True)
        colT_top1, colT_top2 = st.columns([7, 3])
        with colT_top1:
            st.subheader(f"렌더링 타임라인 ({len(scenes)} 개 씬)")
        with colT_top2:
            if 'history_cuts' not in st.session_state:
                st.session_state.history_cuts = []
            if st.session_state.history_cuts:
                if st.button("↩️ 방금 전 삭제 되돌리기", use_container_width=True):
                    st.session_state.cuts = st.session_state.history_cuts.pop()
                    st.rerun()

        # 오토스크롤을 수행하는 전역 JS 스니펫 주입
        st.components.v1.html("""
            <script>
            setInterval(function(){
                const doc = window.parent.document;
                const activeCard = doc.querySelector('.selected-card');
                if(activeCard && !activeCard.dataset.scrolled) {
                    activeCard.scrollIntoView({behavior: "smooth", block: "center"});
                    activeCard.dataset.scrolled = "true";
                }
            }, 600);
            </script>
        """, height=0)
        
        for sc in scenes:
            is_sel = (curr_scene_idx == sc['idx'])
            # 사용자가 요청한 "선택된 카드뷰 표시" 복원
            card_border = "#E74C3C" if is_sel else "#DDDDDD"
            card_bg = "#FFF5F4" if is_sel else "#FFFFFF"
            sel_class = "selected-card" if is_sel else ""
            shadow_css = "box-shadow: 0 4px 10px rgba(0,0,0,0.1);" if is_sel else "opacity: 0.8;"
            
            st.markdown(f"<div class='cut-card {sel_class}' style='border: 2px solid {card_border}; background: {card_bg}; padding: 15px; border-radius: 12px; margin-bottom: 12px; {shadow_css}'>", unsafe_allow_html=True)
            
            # 카드의 헤더 버튼 (클릭하여 선택)
            colT1, colT2 = st.columns([7, 3])
            with colT1:
                st.markdown(f"**🎬 씬 {sc['idx'] + 1}** ({len(sc['cuts'])}줄 묶음)")
            with colT2:
                if not is_sel:
                    if st.button("👆 카드로 이동 (편집)", key=f"sel_sc_{sc['start_cut_idx']}", use_container_width=True):
                        st.session_state.current_idx = sc['start_cut_idx']
                        st.rerun()
                else:
                    st.markdown("<div style='color:#E74C3C; font-weight:bold; text-align:right;'>현재 편집 중</div>", unsafe_allow_html=True)

            sc_bpm = sc['cuts'][0].get('bpm', st.session_state.bpm)
            sc_beats = sum(c['beats'] for c in sc['cuts'])
            sc_duration = (60.0 / sc_bpm) * sc_beats
            
            st.markdown(f"<div style='font-weight:bold; color:#444; margin-bottom:5px;'>소요시간 : {sc_duration:.1f}초 ({sc_beats:.1f}박자, bpm {int(sc_bpm)})</div>", unsafe_allow_html=True)
            
            c_d, c_b, c_m = st.columns(3)
            with c_d:
                new_dur = st.number_input("초", min_value=0.1, value=float(round(sc_duration, 2)), step=0.5, format="%.2f", key=f"d_{sc['idx']}")
            with c_b:
                new_beats = st.number_input("박자", min_value=0.1, value=float(round(sc_beats, 1)), step=0.5, format="%.1f", key=f"b_{sc['idx']}")
            with c_m:
                new_bpm = st.number_input("bpm", min_value=10, max_value=300, value=int(sc_bpm), key=f"m_{sc['idx']}")
                
            if round(new_dur, 2) != round(sc_duration, 2):
                updated_beats = (new_dur * sc_bpm) / 60.0
                pts = len(sc['cuts'])
                for ac in st.session_state.cuts:
                    if ac in sc['cuts']:
                        ac['beats'] = updated_beats / pts
                st.rerun()
            elif round(new_beats, 1) != round(sc_beats, 1):
                pts = len(sc['cuts'])
                for ac in st.session_state.cuts:
                    if ac in sc['cuts']:
                        ac['beats'] = new_beats / pts
                st.rerun()
            elif int(new_bpm) != int(sc_bpm):
                for ac in st.session_state.cuts:
                    if ac in sc['cuts']:
                        ac['bpm'] = new_bpm
                st.rerun()

            st.write("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
            
            # 각 줄별 이미지 및 개별 삭제 (Undo 기능 추가)
            for i, cut in enumerate(sc['cuts']):
                rc1, rc2 = st.columns([8, 2])
                with rc1:
                    st.image(cut['img'], use_container_width=True)
                with rc2:
                    st.write("<br>", unsafe_allow_html=True)
                    if st.button("🗑️ 제거", key=f"del_ind_{cut['id']}_{sc['idx']}_{i}", use_container_width=True):
                        import copy
                        st.session_state.history_cuts.append(copy.deepcopy(st.session_state.cuts))
                        st.session_state.cuts = [c for c in st.session_state.cuts if c['id'] != cut['id']]
                        if st.session_state.current_idx >= len(st.session_state.cuts):
                            st.session_state.current_idx = max(0, len(st.session_state.cuts) - 1)
                        st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

# [STEP 3] 렌더링 완료
elif st.session_state.step == 3:
    st.header("⚙️ 영상 생성 완료")
    with st.status("렌더링을 진행 중입니다...", expanded=True) as status:
        engine = ScoreSyncEngine(st.session_state.bpm)
        out_path = engine.assemble_and_render(
            cuts_info=st.session_state.cuts,
            lines_per_screen=st.session_state.lines_per_screen,
            aspect_ratio=st.session_state.aspect_ratio,
            score_position=st.session_state.score_position,
            image_scale=st.session_state.image_scale,
            line_gap=st.session_state.line_gap,
            output_name=st.session_state.title
        )
        status.update(label="렌더링 완료!", state="complete")
    
    if out_path:
        st.balloons()
        with open(out_path, "rb") as f:
            st.download_button("📥 완성된 MP4 다운로드", f, file_name=f"{st.session_state.title}.mp4", type="primary")
    
    if st.button("🔄 처음으로 돌아가기"):
        st.session_state.step = 1
        st.session_state.cuts = []
        st.rerun()
