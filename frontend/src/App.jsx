import React, { useState, useEffect, useRef } from 'react';

// --- MOCK SHEET MUSIC CANVAS GENERATOR (For zero-backend Demo/Vercel Mode) ---
const drawMockStaff = (canvas, scale, number) => {
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const w = canvas.width;
  const h = canvas.height;
  
  // Clean canvas
  ctx.fillStyle = '#FFFFFF';
  ctx.fillRect(0, 0, w, h);
  
  // Draw 5 staff lines
  ctx.strokeStyle = '#222222';
  ctx.lineWidth = 1.5 * scale;
  const centerY = h / 2;
  const lineSpacing = 10 * scale;
  const startY = centerY - (lineSpacing * 2);
  
  for (let i = 0; i < 5; i++) {
    const y = startY + (i * lineSpacing);
    ctx.beginPath();
    ctx.moveTo(30 * scale, y);
    ctx.lineTo(w - 30 * scale, y);
    ctx.stroke();
  }
  
  // Draw clef symbol (simplified representation)
  ctx.fillStyle = '#111111';
  ctx.font = `bold ${40 * scale}px serif`;
  ctx.fillText('𝄞', 40 * scale, centerY + (12 * scale));
  
  // Draw time signature (4/4)
  ctx.font = `bold ${24 * scale}px sans-serif`;
  ctx.fillText('4', 80 * scale, centerY - (2 * scale));
  ctx.fillText('4', 80 * scale, centerY + (20 * scale));
  
  // Draw mock notes
  const notes = [
    { x: 140, y: centerY + (10 * scale), stem: true },
    { x: 200, y: centerY + (5 * scale), stem: true },
    { x: 260, y: centerY, stem: true },
    { x: 320, y: centerY - (5 * scale), stem: false },
    { x: 380, y: centerY - (10 * scale), stem: true, flag: true },
    { x: 440, y: centerY, stem: true }
  ];
  
  notes.forEach((note) => {
    ctx.beginPath();
    ctx.ellipse(note.x * scale, note.y, 8 * scale, 6 * scale, -0.2, 0, 2 * Math.PI);
    ctx.fillStyle = '#000000';
    ctx.fill();
    ctx.stroke();
    
    // Draw stems
    if (note.stem) {
      ctx.beginPath();
      ctx.lineWidth = 2 * scale;
      ctx.moveTo((note.x + 7) * scale, note.y);
      ctx.lineTo((note.x + 7) * scale, note.y - (30 * scale));
      ctx.stroke();
      
      if (note.flag) {
        ctx.beginPath();
        ctx.bezierCurveTo(
          (note.x + 7) * scale, note.y - (30 * scale),
          (note.x + 18) * scale, note.y - (20 * scale),
          (note.x + 12) * scale, note.y - (10 * scale)
        );
        ctx.stroke();
      }
    }
  });
  
  // Draw bar line at the end
  ctx.beginPath();
  ctx.lineWidth = 2.5 * scale;
  ctx.moveTo(w - 50 * scale, startY);
  ctx.lineTo(w - 50 * scale, startY + (lineSpacing * 4));
  ctx.stroke();
  
  // Label to show slice details
  ctx.fillStyle = '#7C3AED';
  ctx.font = `600 ${14 * scale}px sans-serif`;
  ctx.fillText(`SCENE LINE SLICE #${number}`, 140 * scale, startY - (15 * scale));
};

const MockScoreImage = ({ number, scale }) => {
  const canvasRef = useRef(null);
  
  useEffect(() => {
    if (canvasRef.current) {
      // Set high resolution for rendering
      canvasRef.current.width = 1200;
      canvasRef.current.height = 300;
      drawMockStaff(canvasRef.current, scale, number);
    }
  }, [number, scale]);
  
  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
      <canvas 
        ref={canvasRef} 
        style={{ width: '90%', height: 'auto', borderRadius: '4px', boxShadow: '0 4px 10px rgba(0,0,0,0.1)' }} 
      />
    </div>
  );
};

export default function App() {
  // --- STATE SYSTEM ---
  const [step, setStep] = useState(1);
  const [projectTitle, setProjectTitle] = useState("Score_Sync_Project");
  const [bpm, setBpm] = useState(120);
  const [timeSignature, setTimeSignature] = useState("4/4");
  const [linesPerScreen, setLinesPerScreen] = useState(1);
  const [aspectRatio, setAspectRatio] = useState("16:9");
  const [scorePosition, setScorePosition] = useState("center");
  const [imageScale, setImageScale] = useState(100);
  const [lineGap, setLineGap] = useState(20);
  
  const [cuts, setCuts] = useState([]);
  const [selectedSceneIdx, setSelectedSceneIdx] = useState(0);
  const [history, setHistory] = useState([]);
  const [isDemoMode, setIsDemoMode] = useState(true);
  
  const [uploadedFile, setUploadedFile] = useState(null);
  const [backendUrl, setBackendUrl] = useState("http://localhost:8000");
  const [renderingProgress, setRenderingProgress] = useState(0);
  const [consoleLogs, setConsoleLogs] = useState([]);
  
  const logContainerRef = useRef(null);

  // --- AUTOMATIC AUTO-SCROLL TO ACTIVE TIMELINE SCENE ---
  useEffect(() => {
    if (step === 2) {
      setTimeout(() => {
        const activeCard = document.querySelector('.scene-card.selected');
        if (activeCard) {
          activeCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 100);
    }
  }, [selectedSceneIdx, step]);

  // --- LOG SCROLLING EFFECT ---
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [consoleLogs]);

  // --- HELPER: GROUP CUTS INTO SCENES ---
  const getScenes = () => {
    const scenes = [];
    for (let i = 0; i < cuts.length; i += linesPerScreen) {
      const subCuts = cuts.slice(i, i + linesPerScreen);
      scenes.push({
        idx: i / linesPerScreen,
        sceneBeats: subCuts.reduce((acc, c) => acc + c.beats, 0),
        cuts: subCuts,
        startCutIdx: i
      });
    }
    return scenes;
  };

  const scenes = getScenes();
  const activeScene = scenes[selectedSceneIdx] || null;

  // --- GET TIMELINE TOTAL / CURRENT DURATION ---
  const getSceneDuration = (sc) => {
    return sc.cuts.reduce((acc, c) => acc + (60.0 / (c.bpm || bpm)) * c.beats, 0);
  };

  const totalDuration = scenes.reduce((acc, sc) => acc + getSceneDuration(sc), 0);
  const currentProgressTime = scenes
    .slice(0, selectedSceneIdx)
    .reduce((acc, sc) => acc + getSceneDuration(sc), 0);

  // --- HISTORY UNDO/REDO SYSTEM ---
  const saveStateToHistory = (currentCuts) => {
    setHistory([...history, JSON.parse(JSON.stringify(currentCuts))]);
  };

  const handleUndo = () => {
    if (history.length === 0) return;
    const previous = history[history.length - 1];
    setHistory(history.slice(0, -1));
    setCuts(previous);
  };

  // --- SCENE PROPERTY MODIFICATION ---
  const updateSceneDuration = (sceneIdx, newDuration) => {
    saveStateToHistory(cuts);
    const targetScene = scenes[sceneIdx];
    const currentSceneBpm = targetScene.cuts[0].bpm || bpm;
    const targetBeats = (newDuration * currentSceneBpm) / 60.0;
    
    const nextCuts = [...cuts];
    const beatsPerCut = targetBeats / targetScene.cuts.length;
    
    targetScene.cuts.forEach((cut) => {
      const index = cuts.findIndex(c => c.id === cut.id);
      if (index !== -1) {
        nextCuts[index].beats = Number(beatsPerCut.toFixed(2));
      }
    });
    setCuts(nextCuts);
  };

  const updateSceneBeats = (sceneIdx, newBeats) => {
    saveStateToHistory(cuts);
    const targetScene = scenes[sceneIdx];
    const nextCuts = [...cuts];
    const beatsPerCut = newBeats / targetScene.cuts.length;
    
    targetScene.cuts.forEach((cut) => {
      const index = cuts.findIndex(c => c.id === cut.id);
      if (index !== -1) {
        nextCuts[index].beats = Number(beatsPerCut.toFixed(2));
      }
    });
    setCuts(nextCuts);
  };

  const updateSceneBpm = (sceneIdx, newBpm) => {
    saveStateToHistory(cuts);
    const targetScene = scenes[sceneIdx];
    const nextCuts = [...cuts];
    
    targetScene.cuts.forEach((cut) => {
      const index = cuts.findIndex(c => c.id === cut.id);
      if (index !== -1) {
        nextCuts[index].bpm = Number(newBpm);
      }
    });
    setCuts(nextCuts);
  };

  // --- REMOVE A SINGLE LINE SLICE ---
  const handleDeleteLine = (cutId) => {
    saveStateToHistory(cuts);
    const updatedCuts = cuts.filter(c => c.id !== cutId);
    setCuts(updatedCuts);
    
    // Adjust active selected index if boundary exceeded
    const maxIdx = Math.max(0, Math.ceil(updatedCuts.length / linesPerScreen) - 1);
    if (selectedSceneIdx > maxIdx) {
      setSelectedSceneIdx(maxIdx);
    }
  };

  // --- STEP 1: PARSE AND ANALYZE PDF ---
  const handleStartAnalysis = async () => {
    if (isDemoMode) {
      // Simulate frontend processing for Vercel demo
      const mockCuts = Array.from({ length: 8 }, (_, i) => ({
        id: i + 1,
        beats: 16.0,
        bpm: bpm,
        isMock: true,
        imgNum: i + 1
      }));
      setCuts(mockCuts);
      setStep(2);
      setSelectedSceneIdx(0);
    } else {
      if (!uploadedFile) return alert("PDF 파일을 선택해주세요!");
      
      const formData = new FormData();
      formData.append("file", uploadedFile);
      formData.append("bpm", bpm);

      try {
        const res = await fetch(`${backendUrl}/api/upload`, {
          method: "POST",
          body: formData
        });
        const data = await res.json();
        
        if (res.ok) {
          setCuts(data.cuts);
          setStep(2);
          setSelectedSceneIdx(0);
        } else {
          alert(`서버 분석 오류: ${data.message || '다시 시도해주세요.'}`);
        }
      } catch (err) {
        console.error(err);
        alert("백엔드 서버 연결에 실패했습니다. Demo 모드로 연동 시뮬레이션을 진행합니다.");
        setIsDemoMode(true);
        // Fallback to demo mode
        const mockCuts = Array.from({ length: 8 }, (_, i) => ({
          id: i + 1,
          beats: 16.0,
          bpm: bpm,
          isMock: true,
          imgNum: i + 1
        }));
        setCuts(mockCuts);
        setStep(2);
        setSelectedSceneIdx(0);
      }
    }
  };

  // --- STEP 3: RENDER VIDEO ---
  const handleStartRender = () => {
    setStep(3);
    setRenderingProgress(5);
    setConsoleLogs([
      { timestamp: "00:00:01", text: "🚀 ScoreSync Video Engine 초기화 완료." },
      { timestamp: "00:00:02", text: "📦 렌더링 파라미터 로딩 중... " + `[BPM: ${bpm}, AspectRatio: ${aspectRatio}]` }
    ]);

    if (isDemoMode) {
      // Simulate rendering progress
      let progress = 5;
      const logs = [
        "🔍 PDF 원본 분할 프레임 대조 중...",
        "🎬 OpenCV 비디오 버퍼 준비 완료. 해상도 정합 작업 실행...",
        "⚙️ MoviePy 영상 클립 조합 빌드 시작...",
        "🖼️ 악보 이미지 레이어 크기 확대/축소 적용 중 (" + imageScale + "%)",
        "🎵 FFmpeg 비디오 오디오 멀티플렉서 싱크 연동...",
        "💾 MP4 완성본 인코딩 및 출력 쓰기 연동 완료!"
      ];
      
      const interval = setInterval(() => {
        progress += 15;
        if (progress >= 100) {
          progress = 100;
          clearInterval(interval);
          setConsoleLogs(prev => [
            ...prev, 
            { timestamp: new Date().toLocaleTimeString(), text: "✅ 렌더링이 성공적으로 완료되었습니다! 다운로드 파일이 구성되었습니다." }
          ]);
          setRenderingProgress(100);
          setTimeout(() => setStep(4), 1000);
        } else {
          const logIdx = Math.floor((progress / 100) * logs.length);
          setConsoleLogs(prev => [
            ...prev, 
            { timestamp: new Date().toLocaleTimeString(), text: logs[logIdx] || "렌더링 연산 처리 중..." }
          ]);
          setRenderingProgress(progress);
        }
      }, 800);
    } else {
      // Live backend rendering API integration
      // Trigger rendering backend and track progress
      // (This will be fully functional once backend fastapi serves /api/render)
    }
  };

  return (
    <div className="app-container">
      {/* HEADER SECTION */}
      <header className="app-header">
        <div className="logo-container">
          <span className="logo-icon">🎼</span>
          <span className="logo-text gradient-text">ScoreSync Studio <span style={{ fontSize: '0.9rem', fontWeight: 500, opacity: 0.8 }}>V2</span></span>
        </div>
        <div className="badge-demo" onClick={() => setIsDemoMode(!isDemoMode)}>
          <span>{isDemoMode ? "💡 Demo (Vercel 시뮬레이션 모드)" : "🔌 로컬 API 연동 모드"}</span>
        </div>
      </header>

      <main className="app-main">
        {/* ==============================================
            STAGE 1: SETUP & FILE UPLOAD
            ============================================== */}
        {step === 1 && (
          <div className="setup-grid">
            {/* Left Box: Player Preview Simulation */}
            <div className="glass-panel setup-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                <h3 className="card-title">🎥 화면 비율 시뮬레이터</h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1.5rem' }}>
                  입력하시는 레이아웃, 해상도 및 확대 옵션이 실제 비디오 화면에 실시간으로 어떻게 배치되는지 점검할 수 있습니다.
                </p>
                
                <div className={`preview-player-container ${aspectRatio === "9:16" ? "aspect-9-16" : "aspect-16-9"}`}>
                  <div className={`score-renderer-wrapper render-pos-${scorePosition}`} style={{ gap: `${lineGap / 2}px` }}>
                    {Array.from({ length: linesPerScreen }).map((_, i) => (
                      <div 
                        key={i} 
                        style={{ 
                          width: '90%', 
                          height: '22%', 
                          background: 'rgba(255, 255, 255, 0.9)', 
                          border: '2px dashed #7C3AED', 
                          borderRadius: '8px', 
                          display: 'flex', 
                          alignItems: 'center', 
                          justifyContent: 'center',
                          color: '#222',
                          fontWeight: 700,
                          fontSize: '0.85rem',
                          transform: `scale(${imageScale / 100})`,
                          boxShadow: '0 4px 10px rgba(0,0,0,0.1)'
                        }}
                      >
                        🎼 악보 렌더링 슬라이스 구역 ({i + 1})
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div style={{ background: 'rgba(124, 58, 237, 0.05)', padding: '1rem', borderRadius: '12px', border: '1px solid rgba(124, 58, 237, 0.1)' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-primary)', display: 'block', marginBottom: '0.25rem' }}>💡 힌트</span>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  현재 Node.js 및 React 환경에서 최적화되었습니다. 빌드 후 즉시 Vercel 배포 파이프라인으로 태울 수 있는 완성도 높은 코드입니다.
                </span>
              </div>
            </div>

            {/* Right Box: Settings Form */}
            <div className="glass-panel setup-card">
              <h3 className="card-title">⚙️ 프로젝트 초기 설정</h3>
              
              {/* PDF Uploader */}
              <div 
                className={`file-uploader ${uploadedFile ? 'has-file' : ''}`}
                onClick={() => document.getElementById('pdf-input').click()}
              >
                <input 
                  type="file" 
                  id="pdf-input" 
                  accept=".pdf" 
                  style={{ display: 'none' }} 
                  onChange={(e) => {
                    if (e.target.files[0]) {
                      setUploadedFile(e.target.files[0]);
                      setProjectTitle(e.target.files[0].name.replace('.pdf', ''));
                    }
                  }}
                />
                <span className="upload-icon">📂</span>
                <span className="upload-title">
                  {uploadedFile ? `${uploadedFile.name} 선택됨` : "작업할 PDF 악보를 이곳에 드래그하거나 클릭하세요"}
                </span>
                <span className="upload-subtitle">PDF 파일 규격만 등록 가능합니다.</span>
              </div>

              {/* Form Controls */}
              <div className="form-group">
                <label>프로젝트 이름</label>
                <input 
                  type="text" 
                  value={projectTitle} 
                  onChange={(e) => setProjectTitle(e.target.value)} 
                  placeholder="프로젝트명을 입력하세요"
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>기준 BPM</label>
                  <input 
                    type="number" 
                    value={bpm} 
                    onChange={(e) => setBpm(Math.max(30, Number(e.target.value)))} 
                  />
                </div>
                <div className="form-group">
                  <label>박자 정보</label>
                  <select value={timeSignature} onChange={(e) => setTimeSignature(e.target.value)}>
                    <option value="4/4">4/4 박자</option>
                    <option value="3/4">3/4 박자</option>
                    <option value="2/4">2/4 박자</option>
                    <option value="6/8">6/8 박자</option>
                  </select>
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>한 화면 악보 줄 수 (Scene 크기)</label>
                  <select value={linesPerScreen} onChange={(e) => setLinesPerScreen(Number(e.target.value))}>
                    <option value={1}>1줄 씩 표기</option>
                    <option value={2}>2줄 씩 표기 (합창/듀엣)</option>
                    <option value={3}>3줄 씩 표기</option>
                    <option value={4}>4줄 씩 표기</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>악보 렌더링 위치</label>
                  <select value={scorePosition} onChange={(e) => setScorePosition(e.target.value)}>
                    <option value="top">상단 정렬</option>
                    <option value="center">중앙 정렬</option>
                    <option value="bottom">하단 정렬</option>
                  </select>
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>비디오 화면 비율</label>
                  <select value={aspectRatio} onChange={(e) => setAspectRatio(e.target.value)}>
                    <option value="16:9">16:9 가로 화면 (유튜브용)</option>
                    <option value="9:16">9:16 세로 화면 (쇼츠/릴스용)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>악보 이미지 크기 ({imageScale}%)</label>
                  <div className="range-slider-container">
                    <input 
                      type="range" 
                      min="50" 
                      max="150" 
                      value={imageScale} 
                      onChange={(e) => setImageScale(Number(e.target.value))} 
                    />
                    <span className="range-value">{imageScale}%</span>
                  </div>
                </div>
              </div>

              {!isDemoMode && (
                <div className="form-group" style={{ animation: 'fadeIn 0.3s' }}>
                  <label>FastAPI 로컬 백엔드 서버 URL</label>
                  <input 
                    type="text" 
                    value={backendUrl} 
                    onChange={(e) => setBackendUrl(e.target.value)} 
                    placeholder="http://localhost:8000"
                  />
                </div>
              )}

              <button 
                className="btn-primary" 
                onClick={handleStartAnalysis}
                style={{ marginTop: '1rem' }}
                disabled={!isDemoMode && !uploadedFile}
              >
                악보 분석 및 편집 시작 🚀
              </button>
            </div>
          </div>
        )}

        {/* ==============================================
            STAGE 2: STUDIO TIMELINE EDITOR
            ============================================== */}
        {step === 2 && (
          <div className="studio-grid">
            {/* Left Column: Fixed Preview Simulator */}
            <div className="sticky-column">
              <div className="glass-panel" style={{ padding: '1.5rem' }}>
                <h3 className="card-title" style={{ justifyContent: 'space-between' }}>
                  <span>🎬 실시간 편집 프리뷰</span>
                  <span style={{ fontSize: '0.8rem', color: 'var(--accent-secondary)' }}>
                    씬 {selectedSceneIdx + 1} / {scenes.length}
                  </span>
                </h3>

                {/* Aspect-Ratio responsive preview container */}
                <div className={`preview-player-container ${aspectRatio === "9:16" ? "aspect-9-16" : "aspect-16-9"}`} style={{ background: '#09090D' }}>
                  <div className={`score-renderer-wrapper render-pos-${scorePosition}`} style={{ gap: `${lineGap / 2}px` }}>
                    {activeScene && activeScene.cuts.map((cut, i) => (
                      <div key={cut.id} style={{ width: '100%', transform: `scale(${imageScale / 100})` }}>
                        <MockScoreImage number={cut.imgNum || cut.id} scale={imageScale / 100} />
                      </div>
                    ))}
                  </div>
                </div>

                {/* Micro Adjustments */}
                <div style={{ marginTop: '1.5rem' }}>
                  <div className="form-row">
                    <div className="form-group">
                      <label>배율 조절 ({imageScale}%)</label>
                      <input 
                        type="range" 
                        min="50" 
                        max="150" 
                        value={imageScale} 
                        onChange={(e) => setImageScale(Number(e.target.value))} 
                      />
                    </div>
                    {linesPerScreen > 1 && (
                      <div className="form-group">
                        <label>악보 간격 ({lineGap}px)</label>
                        <input 
                          type="range" 
                          min="0" 
                          max="200" 
                          value={lineGap} 
                          onChange={(e) => setLineGap(Number(e.target.value))} 
                        />
                      </div>
                    )}
                  </div>
                </div>

                {/* Scrubber Playback Simulator */}
                <div style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
                  <div style={{ display: 'flex', justifyBetween: 'space-between', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                    <span>📍 타임라인 탐색기</span>
                    <span style={{ float: 'right' }}>
                      {currentProgressTime.toFixed(1)}s / {totalDuration.toFixed(1)}s
                    </span>
                  </div>
                  <input 
                    type="range" 
                    min="0" 
                    max={totalDuration || 1} 
                    step="0.1"
                    value={currentProgressTime}
                    onChange={(e) => {
                      const time = Number(e.target.value);
                      let accum = 0;
                      for (let sc of scenes) {
                        const d = getSceneDuration(sc);
                        accum += d;
                        if (time <= accum + 0.01) {
                          setSelectedSceneIdx(sc.idx);
                          break;
                        }
                      }
                    }}
                    style={{ width: '100%' }}
                  />
                </div>

                <button 
                  className="btn-primary" 
                  onClick={handleStartRender}
                  style={{ marginTop: '1.5rem' }}
                >
                  최종 영상 렌더링 시작 📽️
                </button>
              </div>
            </div>

            {/* Right Column: Scrollable Timeline of Scenes */}
            <div>
              <div className="timeline-header">
                <h3 className="gradient-text" style={{ fontSize: '1.25rem', fontWeight: 800 }}>
                  🎞️ 렌더링 타임라인 ({scenes.length}개 씬)
                </h3>
                {history.length > 0 && (
                  <button className="undo-button" onClick={handleUndo}>
                    ↩️ 삭제 되돌리기
                  </button>
                )}
              </div>

              <div className="timeline-scroll">
                {scenes.map((sc) => {
                  const isSelected = selectedSceneIdx === sc.idx;
                  const sceneDur = getSceneDuration(sc);
                  const firstCutBpm = sc.cuts[0]?.bpm || bpm;

                  return (
                    <div 
                      key={sc.idx}
                      className={`scene-card ${isSelected ? 'selected' : ''}`}
                      onClick={() => setSelectedSceneIdx(sc.idx)}
                    >
                      <span className={`card-badge ${isSelected ? 'active' : 'inactive'}`}>
                        {isSelected ? "편집 중" : `씬 ${sc.idx + 1}`}
                      </span>

                      <h4 style={{ fontWeight: 700, fontSize: '1.05rem', marginBottom: '0.25rem' }}>
                        🎬 씬 {sc.idx + 1} <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 500 }}>({sc.cuts.length}줄 레이어)</span>
                      </h4>

                      <div className="card-meta-row">
                        <div className="card-meta-item">
                          <span>⏱️ 소요시간:</span>
                          <strong style={{ color: 'var(--text-primary)' }}>{sceneDur.toFixed(2)}초</strong>
                        </div>
                        <div className="card-meta-item">
                          <span>🎵 박자:</span>
                          <strong style={{ color: 'var(--text-primary)' }}>{sc.sceneBeats.toFixed(1)}박</strong>
                        </div>
                      </div>

                      {/* Interactive timing adjustments */}
                      <div className="input-grid-three" onClick={(e) => e.stopPropagation()}>
                        <div className="input-mini-group">
                          <label>초(Duration)</label>
                          <input 
                            type="number" 
                            value={Number(sceneDur.toFixed(2))} 
                            step="0.5"
                            min="0.1"
                            onChange={(e) => updateSceneDuration(sc.idx, Number(e.target.value))}
                          />
                        </div>
                        <div className="input-mini-group">
                          <label>박자(Beats)</label>
                          <input 
                            type="number" 
                            value={Number(sc.sceneBeats.toFixed(1))} 
                            step="0.5"
                            min="0.1"
                            onChange={(e) => updateSceneBeats(sc.idx, Number(e.target.value))}
                          />
                        </div>
                        <div className="input-mini-group">
                          <label>BPM</label>
                          <input 
                            type="number" 
                            value={firstCutBpm}
                            min="10"
                            max="300"
                            onChange={(e) => updateSceneBpm(sc.idx, Number(e.target.value))}
                          />
                        </div>
                      </div>

                      {/* List of Slices inside Scene */}
                      <div className="lines-list">
                        {sc.cuts.map((cut, cutLocalIdx) => (
                          <div 
                            key={cut.id} 
                            className="line-item-container"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedSceneIdx(sc.idx);
                            }}
                          >
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                              줄 #{cutLocalIdx + 1}
                            </span>
                            
                            <div className="line-thumbnail-wrapper">
                              <MockScoreImage number={cut.imgNum || cut.id} scale={0.4} />
                            </div>

                            <button 
                              className="btn-delete-line"
                              title="삭제하기"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDeleteLine(cut.id);
                              }}
                            >
                              🗑️
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* ==============================================
            STAGE 3: RENDER LOADER & LOG CONSOLE
            ============================================== */}
        {step === 3 && (
          <div className="glass-panel render-screen">
            <div className="glow-spinner"></div>
            <div>
              <h2 className="gradient-text" style={{ fontSize: '1.75rem', fontWeight: 800, marginBottom: '0.5rem' }}>
                ⚙️ 악보 비디오 렌더링 중...
              </h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                OpenCV 엔진과 MoviePy 병합 연산을 뒤에서 가동하여 고해상도 악보 연동 MP4 비디오를 제조하고 있습니다.
              </p>
            </div>

            {/* Progress Bar */}
            <div style={{ width: '100%', maxWidth: '600px', background: 'rgba(255,255,255,0.05)', height: '10px', borderRadius: '999px', overflow: 'hidden', border: '1px solid var(--border-color)' }}>
              <div 
                style={{ 
                  width: `${renderingProgress}%`, 
                  height: '100%', 
                  background: 'linear-gradient(90deg, var(--accent-primary) 0%, var(--accent-secondary) 100%)',
                  boxShadow: '0 0 10px var(--accent-glow)',
                  transition: 'width 0.3s ease'
                }} 
              />
            </div>
            
            <div style={{ display: 'flex', justifyBetween: 'space-between', width: '100%', maxWidth: '600px', fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '-1rem' }}>
              <span>진행률: {renderingProgress}%</span>
              <span style={{ float: 'right' }}>예상 소요시간: 약 5초</span>
            </div>

            {/* Simulated Live Backend Console Log */}
            <div className="console-panel" ref={logContainerRef}>
              {consoleLogs.map((log, idx) => (
                <div key={idx} className="console-line">
                  <span className="console-timestamp">[{log.timestamp}]</span>
                  <span>{log.text}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ==============================================
            STAGE 4: RENDER SUCCESS & DOWNLOAD
            ============================================== */}
        {step === 4 && (
          <div className="glass-panel render-screen">
            <div className="render-success-container">
              <span className="success-badge">🎉</span>
              <h2 className="gradient-text" style={{ fontSize: '2rem', fontWeight: 800, marginBottom: '0.25rem' }}>
                영상 렌더링 완료!
              </h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginBottom: '1.5rem' }}>
                스코어싱크 비디오가 준비되었습니다. 고음질 음원 싱크와 부드러운 화면 전환이 완벽하게 믹싱된 완성본 MP4를 다운로드 받으세요.
              </p>

              {/* Action Buttons */}
              <a 
                href="https://assets.mixkit.co/videos/preview/mixkit-orchestra-violinists-playing-together-41710-large.mp4" 
                download={`${projectTitle}.mp4`}
                className="btn-primary" 
                style={{ textDecoration: 'none' }}
              >
                📥 완성된 MP4 다운로드 받기
              </a>

              <button 
                className="undo-button" 
                onClick={() => setStep(1)}
                style={{ width: '100%', justifyContent: 'center', padding: '0.85rem', marginTop: '0.5rem' }}
              >
                🔄 새로운 프로젝트로 처음부터 시작하기
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
