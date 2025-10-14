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

@app.route("/api/upload", methods=["POST"])
def upload_json():
    # ---- API key authentication (for Render POSTs) ----
    key = request.headers.get("x-api-key")
    if key and key != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    # ---- File check ----
    file = request.files.get("jsonFile")
    if not file or not file.filename.endswith(".json"):
        flash("Invalid file. Must be a .json.", "error")
        return redirect(url_for("index"))

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    # ---- Read JSON content ----
    try:
        data = json.load(file.stream)
    except json.JSONDecodeError:
        flash("Invalid JSON content.", "error")
        return redirect(url_for("index"))

    # ---- Combine with metadata (if form data exists) ----
    submission = {
        "name": request.form.get("name"),
        "email": request.form.get("email"),
        "phone": request.form.get("phone"),
        "doi": request.form.get("doi"),
        "study": request.form.get("study"),
        "comment": request.form.get("comment"),
        "hrfunc_standard": request.form.get("hrfunc_standard"),
        "dataset_subset": request.form.get("dataset_subset"),
        "hrf_data": data
    }

    # ---- Save the JSON locally ----
    file = request.files['jsonFile']
    resp = requests.post(
        "https://flask.jib-jab.org/api/upload",
        files={"jsonFile": (file.filename, file.stream)},
        headers={"x-api-key": "your_secret_key"},
    )
    # ---- Return / flash response ----
    if key:  # API POST → return JSON
        return jsonify({"message": "Upload successful", "filename": filename}), 200
    else:    # Browser form → flash + redirect
        flash(f"File '{filename}' uploaded successfully!", "success")
        return redirect(url_for("index"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)