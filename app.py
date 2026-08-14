import os
import tempfile
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from redactor import redact_docx

app = FastAPI()

html_content = """
<!DOCTYPE html>
<html>
    <head>
        <title>PII Redaction Tool</title>
        <style>
            body { font-family: sans-serif; margin: 40px; }
            form { margin-top: 20px; }
        </style>
    </head>
    <body>
        <h1>PII Redaction Tool</h1>
        <p>Upload a .docx file to automatically redact PII.</p>
        <form action="/redact" method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".docx" required>
            <button type="submit">Upload and Redact</button>
        </form>
    </body>
</html>
"""

@app.get("/")
def main():
    return HTMLResponse(content=html_content)

@app.get("/health")
def health():
    return {"status": "ok"}

def cleanup_files(*paths):
    for path in paths:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

@app.post("/redact")
async def redact_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Only .docx files are supported.")

    fd_in, temp_in = tempfile.mkstemp(suffix=".docx")
    fd_out, temp_out = tempfile.mkstemp(suffix=".docx")
    
    os.close(fd_in)
    os.close(fd_out)
    
    try:
        with open(temp_in, "wb") as f:
            content = await file.read()
            f.write(content)
            
        try:
            # Call the exact pipeline logic directly
            redact_docx(temp_in, temp_out, audit_path=None)
        except Exception as e:
            cleanup_files(temp_in, temp_out)
            raise HTTPException(status_code=500, detail=f"Redaction failed during processing: {str(e)}")
            
        # Clean up both temp files after the response is fully sent
        background_tasks.add_task(cleanup_files, temp_in, temp_out)
        
        return FileResponse(
            path=temp_out,
            filename=f"redacted_{file.filename}",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    except HTTPException:
        raise
    except Exception as e:
        cleanup_files(temp_in, temp_out)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
