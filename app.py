from flask import Flask, request, redirect, url_for, flash, render_template, jsonify
from werkzeug.utils import secure_filename
import os, json, requests
from datetime import datetime, timezone

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
API_KEY = os.environ.get("HRFUNC_API_KEY")
app.secret_key = os.environ.get("SECRET_KEY")
UPLOAD_FOLDER = "/mnt/public/hrfunc/uploads"
TIMESTAMP_SUFFIX_FORMAT = "%Y-%m-%dT_%H-%M-%SZ"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/developers")
def developers():
    return render_template("developers.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/hrfunc_guide")
def hrfunc_guide():
    return render_template("hrfunc_guide.html")

@app.route("/hrtree_guide")
def hrtree_guide():
    return render_template("hrtree_guide.html")

@app.route("/QA")
def QA():
    return render_template("QA.html")

@app.route("/experimental_contexts")
def experimental_contexts():
    return render_template("experimental_contexts.html")

@app.route("/hrf_upload")
def hrf_upload():
    return render_template("hrf_upload.html")


@app.route("/upload_json", methods=["POST"])
def upload_json():
    # ---- 1. Extract file ----
    file = request.files.get("jsonFile")
    if not file or not file.filename.lower().endswith(".json"):
        flash("Invalid file. Must be a .json.", "error")
        return redirect(url_for("hrf_upload"))  # redirect to your upload page

    original_filename = secure_filename(file.filename)
    name_root, ext = os.path.splitext(original_filename or "hrf_upload.json")
    ext = ext or ".json"
    if not name_root:  # in case secure_filename strips everything
        name_root = "hrf_upload"
        ext = ".json"
    uploaded_at = datetime.now(timezone.utc)
    timestamp_suffix = uploaded_at.strftime(TIMESTAMP_SUFFIX_FORMAT)
    filename = f"{name_root}_{timestamp_suffix}{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    # ---- 2. Read bytes and validate JSON ----
    original_bytes = file.read()
    try:
        data = json.loads(original_bytes.decode("utf-8"))
    except json.JSONDecodeError:
        flash("Invalid JSON content.", "error")
        return redirect(url_for("hrf_upload"))

    # ---- 3. Merge submission metadata into payload ----
    submission = request.form.to_dict(flat=True)
    uploaded_at_iso = uploaded_at.isoformat()
    submission_metadata = {
        **submission,
        "uploaded_at": uploaded_at_iso,
        "original_filename": original_filename,
        "stored_filename": filename,
    }

    if isinstance(data, dict):
        data["_hrf_submission"] = submission_metadata
    else:
        data = {
            "hrf_payload": data,
            "_hrf_submission": submission_metadata,
        }

    augmented_bytes = json.dumps(data, separators=(",", ":")).encode("utf-8")

    # ---- 4. Forward to API ----
    try:
        resp = requests.post(
            "https://flask.jib-jab.org/api/upload",
            files={"jsonFile": (filename, augmented_bytes)},
            headers={"x-api-key": API_KEY},
            timeout=10,
        )
    except Exception as e:
        flash(f"Error contacting API: {e}", "error")
        return redirect(url_for("hrf_upload"))

    # ---- 5. Handle response ----
    if resp.status_code == 200:
        flash(
            f"HRFs '{filename}' from the {submission.get('study', 'unknown')} study "
            f"uploaded successfully — thank you {submission.get('name', 'researcher')}!",
            "success",
        )
    else:
        flash(f"Upload failed: {resp.text}", "error")

    return redirect(url_for("hrf_upload"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
