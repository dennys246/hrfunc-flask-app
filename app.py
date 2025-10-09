from flask import Flask, request, redirect, url_for, flash, render_template
from werkzeug.utils import secure_filename
import os, json

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
app.secret_key = os.environ.get("FLASK_SECRET_KEY") # You’ll want to set this as an environment variable in production

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

@app.route('/upload', methods=['POST'])
def upload_json():
    file = request.files.get('jsonFile')
    if not file or not file.filename.endswith('.json'):
        flash('Invalid file. Must be a .json.', 'error')
        return redirect(url_for('index'))

    filename = secure_filename(file.filename)
    UPLOAD_FOLDER = "/mnt/public/hrfunc/uploads"
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    try:
        data = json.load(file.stream)
    except json.JSONDecodeError:
        flash('Invalid JSON content.', 'error')
        return redirect(url_for('index'))

    # Combine HRF data with metadata
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

    # Save combined JSON
    with open(filepath, 'w') as f:
        json.dump(submission, f, indent=2)

    flash(f"File '{filename}' uploaded successfully!", "success")
    return redirect(url_for('index'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)