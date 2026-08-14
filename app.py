import os
import tempfile
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from redactor import redact_docx

app = FastAPI()

html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PII Redaction Studio</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --accent: #3b82f6;
            --accent-hover: #2563eb;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
        }
        
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, var(--bg-color) 0%, #020617 100%);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .container {
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 24px;
            padding: 48px;
            max-width: 600px;
            width: 100%;
            text-align: center;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            animation: slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1);
        }

        @keyframes slideUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        h1 {
            font-weight: 700;
            font-size: 2rem;
            margin-bottom: 12px;
            background: linear-gradient(to right, #60a5fa, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        p {
            color: var(--text-secondary);
            margin-bottom: 32px;
            line-height: 1.6;
        }

        .upload-area {
            border: 2px dashed rgba(255, 255, 255, 0.2);
            border-radius: 16px;
            padding: 40px 20px;
            transition: all 0.3s ease;
            cursor: pointer;
            position: relative;
            background: rgba(0,0,0,0.2);
        }

        .upload-area:hover, .upload-area.dragover {
            border-color: var(--accent);
            background: rgba(59, 130, 246, 0.05);
        }

        input[type="file"] {
            position: absolute;
            width: 100%;
            height: 100%;
            top: 0;
            left: 0;
            opacity: 0;
            cursor: pointer;
        }

        .upload-icon {
            width: 48px;
            height: 48px;
            margin-bottom: 16px;
            fill: var(--accent);
        }

        button {
            background: var(--accent);
            color: white;
            border: none;
            padding: 14px 32px;
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 600;
            font-family: inherit;
            cursor: pointer;
            transition: all 0.2s ease;
            margin-top: 24px;
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        button:hover:not(:disabled) {
            background: var(--accent-hover);
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.4);
        }
        
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        #file-name {
            display: block;
            margin-top: 16px;
            font-size: 0.9rem;
            color: #60a5fa;
            font-weight: 500;
        }

        /* Loading State */
        #loadingState {
            display: none;
            flex-direction: column;
            align-items: center;
            padding: 20px 0;
        }

        .spinner {
            width: 40px;
            height: 40px;
            border: 4px solid rgba(255,255,255,0.1);
            border-top-color: var(--accent);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-bottom: 20px;
        }

        @keyframes spin { to { transform: rotate(360deg); } }

        .pulse-text {
            animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
    </style>
</head>
<body>

    <div class="container">
        <h1>Secure PII Redaction</h1>
        <p>Upload a Word Document (.docx) to automatically sanitize all personal and sensitive information.</p>

        <form id="uploadForm">
            <div id="defaultState">
                <div class="upload-area" id="dropZone">
                    <svg class="upload-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"/>
                    </svg>
                    <div style="font-weight: 600;">Drag & Drop your .docx file</div>
                    <div style="font-size: 0.85rem; margin-top: 8px; color: var(--text-secondary);">or click to browse</div>
                    <input type="file" id="fileInput" accept=".docx" required>
                </div>
                <span id="file-name"></span>
                <button type="submit" id="submitBtn" disabled>
                    <svg style="width:20px; height:20px; fill:currentColor" viewBox="0 0 24 24"><path d="M12 2L4 5v6.09c0 5.05 3.41 9.76 8 10.91 4.59-1.15 8-5.86 8-10.91V5l-8-3zm1 14h-2v-2h2v2zm0-4h-2V7h2v5z"/></svg>
                    Redact Document
                </button>
            </div>

            <div id="loadingState">
                <div class="spinner"></div>
                <h3 class="pulse-text" id="loadingText">Analyzing & Redacting PII...</h3>
                <p style="margin-top: 12px; font-size: 0.85rem;">This may take up to 20 seconds for large documents.</p>
            </div>
        </form>
    </div>

    <script>
        const fileInput = document.getElementById('fileInput');
        const fileNameDisplay = document.getElementById('file-name');
        const submitBtn = document.getElementById('submitBtn');
        const dropZone = document.getElementById('dropZone');

        // File selection handling
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                const name = e.target.files[0].name;
                if(name.endsWith('.docx')) {
                    fileNameDisplay.textContent = "Selected: " + name;
                    submitBtn.disabled = false;
                } else {
                    fileNameDisplay.textContent = "Error: Only .docx files allowed";
                    fileNameDisplay.style.color = "#ef4444";
                    submitBtn.disabled = true;
                }
            } else {
                fileNameDisplay.textContent = "";
                submitBtn.disabled = true;
            }
        });

        // Drag and drop visuals
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });
        function preventDefaults (e) { e.preventDefault(); e.stopPropagation(); }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
        });

        // Form Submission
        document.getElementById('uploadForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            if (!fileInput.files.length) return;
            
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            
            // Switch to Loading UI
            document.getElementById('defaultState').style.display = 'none';
            document.getElementById('loadingState').style.display = 'flex';
            
            try {
                const response = await fetch('/redact', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Redaction failed');
                }
                
                // Trigger programmatic download
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'redacted_' + fileInput.files[0].name;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                // Show success
                document.getElementById('loadingText').innerText = 'Complete! File Downloaded.';
                document.getElementById('loadingText').style.color = '#4ade80';
                
                // Reset UI after 3 seconds
                setTimeout(() => {
                    document.getElementById('loadingState').style.display = 'none';
                    document.getElementById('defaultState').style.display = 'block';
                    document.getElementById('loadingText').innerText = 'Analyzing & Redacting PII...';
                    document.getElementById('loadingText').style.color = '';
                    fileInput.value = '';
                    fileNameDisplay.textContent = '';
                    submitBtn.disabled = true;
                }, 3000);
                
            } catch (error) {
                alert('Error: ' + error.message);
                document.getElementById('loadingState').style.display = 'none';
                document.getElementById('defaultState').style.display = 'block';
            }
        });
    </script>
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
