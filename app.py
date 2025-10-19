from flask import Flask, request, redirect, url_for, flash, render_template, jsonify
from werkzeug.utils import secure_filename
import os, json, requests

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 
API_KEY = os.environ.get("HRFUNC_API_KEY")
app.secret_key = os.environ.get("SECRET_KEY")
UPLOAD_FOLDER = "/mnt/public/hrfunc/uploads"

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
    if not file or not file.filename.endswith(".json"):
        flash("Invalid file. Must be a .json.", "error")
        return redirect(url_for("hrf_upload"))  # redirect to your upload page

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    # ---- 2. Read bytes and validate JSON ----
    file_bytes = file.read()
    try:
        data = json.loads(file_bytes.decode("utf-8"))
    except json.JSONDecodeError:
        flash("Invalid JSON content.", "error")
        return redirect(url_for("hrf_upload"))

    # ---- 3. Save locally ----
    with open(filepath, "wb") as f:
        f.write(file_bytes)

    # ---- 4. Forward to API ----
    try:
        resp = requests.post(
            "https://flask.jib-jab.org/api/upload",
            files={"jsonFile": (filename, file_bytes)},
            headers={"x-api-key": API_KEY},
            timeout=10,
        )
    except Exception as e:
        flash(f"Error contacting API: {e}", "error")
        return redirect(url_for("hrf_upload"))

    # ---- 5. Gather metadata from form ----
    submission = {k: request.form.get(k) for k in request.form.keys()}

    # ---- 6. Handle response ----
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