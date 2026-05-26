import os
import shutil
import uuid
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from engine import ScoreSyncEngine

app = FastAPI(title="ScoreSync Studio API")

# --- ENABLE CORS (Allow React Vercel / Local Host to connect) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DIRECTORIES SETUP ---
UPLOAD_DIR = "temp_uploads"
SLICES_DIR = "temp_slices"
OUTPUT_DIR = "temp_outputs"

for d in [UPLOAD_DIR, SLICES_DIR, OUTPUT_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

# Mount sliced images folder so the React client can load them via URL
app.mount("/static/slices", StaticFiles(directory=SLICES_DIR), name="slices")
# Mount output videos folder for download access
app.mount("/static/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")


class CutInfo(BaseModel):
    id: int
    beats: float
    bpm: int
    img: str  # Image path or URL


class RenderRequest(BaseModel):
    title: str
    bpm: int
    scorePosition: str
    imageScale: int
    lineGap: int
    cuts: List[CutInfo]


@app.post("/api/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    bpm: int = Form(120)
):
    """
    Receives sheet music PDF, slices it into line-by-line images using OpenCV,
    and returns initial scene cut configurations for the React timeline editor.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    # Save uploaded PDF to temporary file
    temp_pdf_path = f"{UPLOAD_DIR}/{uuid.uuid4()}_{file.filename}"
    with open(temp_pdf_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        # Initialize OpenCV sheet music engine
        engine = ScoreSyncEngine(bpm)
        
        # Read the file again for the PDF engine
        with open(temp_pdf_path, "rb") as f:
            sliced_paths = engine.slice_pdf_to_lines(f)
            
        # Formulate cuts for React with absolute backend static URLs
        cuts = []
        for i, path in enumerate(sliced_paths):
            filename = os.path.basename(path)
            # URL to access the sliced image statically
            img_url = f"/static/slices/{filename}"
            cuts.append({
                "id": i + 1,
                "beats": 16.0,
                "bpm": bpm,
                "img": img_url,
                "localPath": path  # Keep track of local file path for rendering
            })
            
        return {"cuts": cuts}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"PDF Slicing failed: {str(e)}")
    finally:
        # Clean up temporary uploaded PDF
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)


@app.post("/api/render")
async def render_video(request: RenderRequest):
    """
    Renders the final MP4 video using MoviePy and OpenCV, mapping the customized
    beats, BPM, and layouts from the React editor into a single media file.
    """
    try:
        engine = ScoreSyncEngine(request.bpm)
        
        # Map URL/client image paths back to local server file paths for MoviePy
        cuts_info = []
        for cut in request.cuts:
            # Slices are in temp_slices/
            filename = os.path.basename(cut.img)
            local_path = f"{SLICES_DIR}/{filename}"
            
            cuts_info.append({
                "id": cut.id,
                "beats": cut.beats,
                "bpm": cut.bpm,
                "img": local_path
            })
            
        # Trigger video rendering
        output_name = f"{OUTPUT_DIR}/{uuid.uuid4()}_{request.title}"
        output_path = engine.assemble_and_render(
            line_paths=[c["img"] for c in cuts_info],
            cuts_info=cuts_info,
            lines_per_screen=1,  # V2 merges scenes client-side, engine works with flat cuts
            output_name=output_name
        )
        
        if not output_path or not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail="Video rendering yielded empty file.")
            
        # Return static download URL for the React frontend
        filename = os.path.basename(output_path)
        download_url = f"/static/outputs/{filename}"
        
        return {"videoUrl": download_url}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Rendering failed: {str(e)}")
