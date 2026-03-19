"""
NuoYi - Flask Web Interface for PDF/DOCX to Markdown conversion.

Features:
- File upload (single or batch)
- Engine selection (marker, mineru, docling, pymupdf, pdfplumber, llamaparse, mathpix)
- Device selection (cuda, mps, mlx, cpu, etc.)
- Progress tracking via SSE
- Download converted files
"""

from __future__ import annotations

import io
import tempfile
import threading
import uuid
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

from flask import (
    Flask,
    jsonify,
    render_template_string,
    request,
    send_file,
    send_from_directory,
)

from .converter import DocxConverter, get_converter, list_available_engines
from .utils import (
    DEFAULT_LANGS,
    SUPPORTED_LANGUAGES,
    list_available_devices,
    save_images_and_update_markdown,
)

if TYPE_CHECKING:
    pass

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

jobs: dict[str, dict] = {}


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NuoYi - PDF/DOCX to Markdown</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; min-height: 100vh; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #333; margin-bottom: 20px; text-align: center; }
        .card { background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 20px; margin-bottom: 20px; }
        .card h2 { color: #555; margin-bottom: 15px; font-size: 1.1em; border-bottom: 1px solid #eee; padding-bottom: 10px; }
        .row { display: flex; gap: 20px; flex-wrap: wrap; }
        .col { flex: 1; min-width: 250px; }
        label { display: block; font-weight: 500; margin-bottom: 5px; color: #555; }
        select, input[type="text"] { width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }
        select:focus, input:focus { outline: none; border-color: #4CAF50; }
        .checkbox-group { display: flex; gap: 15px; flex-wrap: wrap; }
        .checkbox-group label { display: flex; align-items: center; gap: 5px; font-weight: normal; cursor: pointer; }
        .checkbox-group input { width: 16px; height: 16px; }
        .lang-group { display: flex; gap: 8px; flex-wrap: wrap; }
        .lang-group label { display: flex; align-items: center; gap: 3px; font-weight: normal; font-size: 13px; cursor: pointer; }
        .lang-group input { width: 14px; height: 14px; }
        .upload-area { border: 2px dashed #ccc; border-radius: 8px; padding: 40px; text-align: center; cursor: pointer; transition: all 0.3s; }
        .upload-area:hover { border-color: #4CAF50; background: #f9fff9; }
        .upload-area.dragover { border-color: #4CAF50; background: #e8f5e9; }
        .upload-area input { display: none; }
        .file-list { margin-top: 15px; }
        .file-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: #f9f9f9; border-radius: 4px; margin-bottom: 5px; }
        .file-item .name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .file-item .remove { color: #f44336; cursor: pointer; padding: 0 10px; }
        .btn { padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; font-weight: 500; transition: all 0.3s; }
        .btn-primary { background: #4CAF50; color: white; }
        .btn-primary:hover { background: #43A047; }
        .btn-primary:disabled { background: #ccc; cursor: not-allowed; }
        .btn-secondary { background: #2196F3; color: white; }
        .btn-secondary:hover { background: #1E88E5; }
        .btn-group { display: flex; gap: 10px; margin-top: 15px; }
        .progress { margin-top: 20px; }
        .progress-bar { height: 8px; background: #e0e0e0; border-radius: 4px; overflow: hidden; }
        .progress-fill { height: 100%; background: #4CAF50; transition: width 0.3s; width: 0%; }
        .status { margin-top: 10px; color: #666; }
        .log-area { background: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 4px; font-family: 'Consolas', monospace; font-size: 13px; height: 200px; overflow-y: auto; margin-top: 15px; }
        .log-line { margin: 2px 0; }
        .log-info { color: #4CAF50; }
        .log-warn { color: #FF9800; }
        .log-error { color: #f44336; }
        .results { margin-top: 20px; }
        .result-item { display: flex; justify-content: space-between; align-items: center; padding: 10px; background: #f5f5f5; border-radius: 4px; margin-bottom: 8px; }
        .result-item .name { font-weight: 500; }
        .result-item .download { color: #2196F3; text-decoration: none; }
        .result-item .download:hover { text-decoration: underline; }
        .engine-info { font-size: 12px; color: #888; margin-top: 5px; }
        .status-ok { color: #4CAF50; }
        .status-error { color: #f44336; }
        .status-pending { color: #FF9800; }
        @media (max-width: 768px) { .row { flex-direction: column; } }
    </style>
</head>
<body>
    <div class="container">
        <h1>NuoYi - PDF/DOCX to Markdown</h1>

        <div class="card">
            <h2>Upload Files</h2>
            <div class="upload-area" id="uploadArea">
                <input type="file" id="fileInput" multiple accept=".pdf,.docx">
                <p>Click or drag files here (PDF, DOCX)</p>
                <p style="color: #888; font-size: 13px; margin-top: 10px;">Max 100MB per file</p>
            </div>
            <div class="file-list" id="fileList"></div>
        </div>

        <div class="card">
            <h2>Options</h2>
            <div class="row">
                <div class="col">
                    <label>Engine</label>
                    <select id="engine">
                        <option value="auto">Auto (recommended)</option>
                    </select>
                    <div class="engine-info" id="engineInfo"></div>
                </div>
                <div class="col">
                    <label>Device</label>
                    <select id="device">
                        <option value="auto">Auto (recommended)</option>
                    </select>
                </div>
            </div>
            <div class="row" style="margin-top: 15px;">
                <div class="col">
                    <label>Page Range</label>
                    <input type="text" id="pageRange" placeholder="e.g. 0-5,10,15-20">
                </div>
                <div class="col">
                    <div class="checkbox-group" style="margin-top: 22px;">
                        <label><input type="checkbox" id="forceOcr"> Force OCR</label>
                        <label><input type="checkbox" id="lowVram"> Low VRAM</label>
                    </div>
                </div>
            </div>
            <div style="margin-top: 15px;">
                <label>Languages</label>
                <div class="lang-group" id="langGroup"></div>
            </div>
        </div>

        <div class="card">
            <div class="btn-group">
                <button class="btn btn-primary" id="convertBtn" disabled>Convert</button>
                <button class="btn btn-secondary" id="downloadAllBtn" style="display:none;">Download All (ZIP)</button>
            </div>
            <div class="progress" id="progressArea" style="display:none;">
                <div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
                <div class="status" id="statusText">Ready</div>
            </div>
            <div class="log-area" id="logArea" style="display:none;"></div>
        </div>

        <div class="card results" id="resultsArea" style="display:none;">
            <h2>Results</h2>
            <div id="resultsList"></div>
        </div>
    </div>

    <script>
        const fileInput = document.getElementById('fileInput');
        const uploadArea = document.getElementById('uploadArea');
        const fileList = document.getElementById('fileList');
        const convertBtn = document.getElementById('convertBtn');
        const engineSelect = document.getElementById('engine');
        const deviceSelect = document.getElementById('device');
        const engineInfo = document.getElementById('engineInfo');
        const progressArea = document.getElementById('progressArea');
        const progressFill = document.getElementById('progressFill');
        const statusText = document.getElementById('statusText');
        const logArea = document.getElementById('logArea');
        const resultsArea = document.getElementById('resultsArea');
        const resultsList = document.getElementById('resultsList');
        const downloadAllBtn = document.getElementById('downloadAllBtn');

        let files = [];
        let jobId = null;

        uploadArea.addEventListener('click', () => fileInput.click());
        uploadArea.addEventListener('dragover', e => { e.preventDefault(); uploadArea.classList.add('dragover'); });
        uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));
        uploadArea.addEventListener('drop', e => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            addFiles(e.dataTransfer.files);
        });
        fileInput.addEventListener('change', e => addFiles(e.target.files));

        function addFiles(newFiles) {
            for (const f of newFiles) {
                if (f.name.endsWith('.pdf') || f.name.endsWith('.docx')) {
                    if (!files.some(x => x.name === f.name)) files.push(f);
                }
            }
            updateFileList();
        }

        function updateFileList() {
            fileList.innerHTML = files.map((f, i) => `
                <div class="file-item">
                    <span class="name">${f.name}</span>
                    <span class="remove" onclick="removeFile(${i})">✕</span>
                </div>
            `).join('');
            convertBtn.disabled = files.length === 0;
        }

        window.removeFile = i => { files.splice(i, 1); updateFileList(); };

        fetch('/api/hardware').then(r => r.json()).then(data => {
            data.engines.forEach(e => {
                const opt = document.createElement('option');
                opt.value = e.name;
                opt.textContent = e.name + (e.available ? '' : ' (unavailable)');
                opt.disabled = !e.available;
                engineSelect.appendChild(opt);
            });
            data.devices.forEach(d => {
                const opt = document.createElement('option');
                opt.value = d;
                opt.textContent = d;
                deviceSelect.appendChild(opt);
            });
            engineInfo.innerHTML = data.engines.map(e =>
                `<span class="${e.available ? 'status-ok' : 'status-error'}">${e.available ? '✓' : '✗'} ${e.name}</span>`
            ).join(' | ');
        });

        const defaultLangs = '{{ default_langs }}'.split(',');
        const langGroup = document.getElementById('langGroup');
        const langNames = {{ lang_names | tojson }};
        Object.entries(langNames).forEach(([code, name]) => {
            const label = document.createElement('label');
            label.innerHTML = `<input type="checkbox" value="${code}" ${defaultLangs.includes(code) ? 'checked' : ''}> ${code}`;
            label.title = name;
            langGroup.appendChild(label);
        });

        convertBtn.addEventListener('click', async () => {
            if (files.length === 0) return;

            const formData = new FormData();
            files.forEach(f => formData.append('files', f));
            formData.append('engine', engineSelect.value);
            formData.append('device', deviceSelect.value);
            formData.append('page_range', document.getElementById('pageRange').value);
            formData.append('force_ocr', document.getElementById('forceOcr').checked);
            formData.append('low_vram', document.getElementById('lowVram').checked);
            const langs = [...document.querySelectorAll('#langGroup input:checked')].map(c => c.value).join(',');
            formData.append('langs', langs || '{{ default_langs }}');

            convertBtn.disabled = true;
            progressArea.style.display = 'block';
            logArea.style.display = 'block';
            logArea.innerHTML = '';
            resultsArea.style.display = 'none';
            resultsList.innerHTML = '';

            try {
                const resp = await fetch('/api/convert', { method: 'POST', body: formData });
                const data = await resp.json();
                if (!data.job_id) throw new Error(data.error || 'Failed to start job');
                jobId = data.job_id;
                pollStatus(jobId);
            } catch (err) {
                addLog('error', 'Error: ' + err.message);
                convertBtn.disabled = false;
            }
        });

        async function pollStatus(jid) {
            try {
                const resp = await fetch(`/api/status/${jid}`);
                const data = await resp.json();

                progressFill.style.width = data.progress + '%';
                statusText.textContent = data.status;

                if (data.logs) data.logs.forEach(l => addLog(l.level, l.msg));

                if (data.status === 'completed') {
                    showResults(data.results);
                    convertBtn.disabled = false;
                    downloadAllBtn.style.display = 'inline-block';
                } else if (data.status === 'error') {
                    addLog('error', data.error || 'Unknown error');
                    convertBtn.disabled = false;
                } else {
                    setTimeout(() => pollStatus(jid), 1000);
                }
            } catch (err) {
                addLog('error', 'Status check failed: ' + err.message);
                convertBtn.disabled = false;
            }
        }

        function addLog(level, msg) {
            const line = document.createElement('div');
            line.className = 'log-line log-' + level;
            line.textContent = '[' + new Date().toLocaleTimeString() + '] ' + msg;
            logArea.appendChild(line);
            logArea.scrollTop = logArea.scrollHeight;
        }

        function showResults(results) {
            resultsArea.style.display = 'block';
            resultsList.innerHTML = results.map(r => `
                <div class="result-item">
                    <span class="name">${r.original}</span>
                    <a class="download" href="/api/download/${jobId}/${r.filename}" target="_blank">Download</a>
                </div>
            `).join('');
        }

        downloadAllBtn.addEventListener('click', () => {
            if (jobId) window.location.href = `/api/download/${jobId}/zip`;
        });
    </script>
</body>
</html>
"""


def run_conversion(
    job_id: str,
    file_paths: list[tuple[str, str]],
    options: dict,
):
    """Background conversion task."""
    job = jobs[job_id]
    job["status"] = "processing"
    job["logs"] = []

    try:
        engine = options.get("engine", "auto")
        device = options.get("device", "auto")
        force_ocr = options.get("force_ocr", False)
        page_range = options.get("page_range") or None
        langs = options.get("langs", DEFAULT_LANGS)
        low_vram = options.get("low_vram", False)

        pdf_converter = None
        docx_converter = DocxConverter()

        pdf_files = [(n, p) for n, p in file_paths if p.lower().endswith(".pdf")]
        if pdf_files:
            job["logs"].append({"level": "info", "msg": f"Initializing {engine} converter..."})
            try:
                pdf_converter = get_converter(
                    engine=engine,
                    force_ocr=force_ocr,
                    page_range=page_range,
                    langs=langs,
                    device=device,
                    low_vram=low_vram,
                )
                job["logs"].append({"level": "info", "msg": "Converter ready"})
            except Exception as e:
                job["logs"].append({"level": "error", "msg": f"Failed to init converter: {e}"})

        results = []
        total = len(file_paths)

        for i, (orig_name, filepath) in enumerate(file_paths):
            job["logs"].append({"level": "info", "msg": f"Processing: {orig_name}"})
            job["progress"] = int((i / total) * 90)

            try:
                images = {}
                if filepath.lower().endswith(".pdf") and pdf_converter:
                    content, images = pdf_converter.convert_file(filepath)
                elif filepath.lower().endswith(".docx"):
                    content = docx_converter.convert_file(filepath)
                else:
                    job["logs"].append({"level": "warn", "msg": f"Skipped: {orig_name}"})
                    continue

                out_name = Path(orig_name).stem + ".md"
                out_path = job["output_dir"] / out_name

                if images:
                    images_subdir = Path(orig_name).stem + "_images"
                    content = save_images_and_update_markdown(
                        content, images, job["output_dir"], images_subdir
                    )
                    for img_name, img_data in images.items():
                        img_path = job["output_dir"] / images_subdir / img_name
                        img_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(img_path, "wb") as f:
                            f.write(img_data)

                out_path.write_text(content, encoding="utf-8")
                results.append({"original": orig_name, "filename": out_name})
                job["logs"].append({"level": "info", "msg": f"Done: {orig_name}"})

            except Exception as e:
                job["logs"].append({"level": "error", "msg": f"Error {orig_name}: {e}"})

        job["results"] = results
        job["status"] = "completed"
        job["progress"] = 100

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
        job["logs"].append({"level": "error", "msg": str(e)})


@app.route("/")
def index():
    return render_template_string(
        HTML_TEMPLATE,
        default_langs=DEFAULT_LANGS,
        lang_names=SUPPORTED_LANGUAGES,
    )


@app.route("/api/hardware")
def api_hardware():
    engines = list_available_engines()
    devices = list_available_devices()
    return jsonify(
        {
            "engines": [{"name": k, **v} for k, v in engines.items()],
            "devices": devices,
        }
    )


@app.route("/api/convert", methods=["POST"])
def api_convert():
    uploaded = request.files.getlist("files")
    if not uploaded:
        return jsonify({"error": "No files uploaded"}), 400

    job_id = str(uuid.uuid4())[:8]
    output_dir = Path(tempfile.mkdtemp(prefix=f"nuoyi_{job_id}_"))

    file_paths = []
    for f in uploaded:
        if f.filename:
            path = output_dir / f.filename
            f.save(path)
            file_paths.append((f.filename, str(path)))

    options = {
        "engine": request.form.get("engine", "auto"),
        "device": request.form.get("device", "auto"),
        "page_range": request.form.get("page_range"),
        "force_ocr": request.form.get("force_ocr") == "true",
        "low_vram": request.form.get("low_vram") == "true",
        "langs": request.form.get("langs", DEFAULT_LANGS),
    }

    jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "output_dir": output_dir,
        "results": [],
        "logs": [],
    }

    thread = threading.Thread(target=run_conversion, args=(job_id, file_paths, options))
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def api_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify(
        {
            "status": job["status"],
            "progress": job["progress"],
            "results": job.get("results", []),
            "logs": job.get("logs", [])[-10:],
            "error": job.get("error"),
        }
    )


@app.route("/api/download/<job_id>/<filename>")
def api_download(job_id: str, filename: str):
    job = jobs.get(job_id)
    if not job:
        return "Job not found", 404

    return send_from_directory(job["output_dir"], filename, as_attachment=True)


@app.route("/api/download/<job_id>/zip")
def api_download_zip(job_id: str):
    job = jobs.get(job_id)
    if not job:
        return "Job not found", 404

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in job["output_dir"].iterdir():
            if item.is_file():
                zf.write(item, item.name)
            elif item.is_dir():
                for sub in item.rglob("*"):
                    if sub.is_file():
                        rel = sub.relative_to(job["output_dir"])
                        zf.write(sub, str(rel))

    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"nuoyi_{job_id}.zip",
    )


def run_web(host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
    """Launch the NuoYi web interface."""
    print("NuoYi Web Interface")
    print(f"http://{host}:{port}" if host != "0.0.0.0" else f"http://localhost:{port}")
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == "__main__":
    run_web(debug=True)
