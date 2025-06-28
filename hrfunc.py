from flask import Flask, request, redirect, url_for, flash, render_template
import os
import json

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/developer")
def developer():
    return render_template("developer.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/events")
def events():
    return render_template("events.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/hrfunc_guide")
def hrfunc_guide():
    return render_template("hrfunc_guide.html")

@app.route("/hrtree_guide")
def hrtree_guide():
    return render_template("hrtree_guide.html")

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
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    try:
        # Validate the JSON before saving
        data = json.load(file.stream)
    except json.JSONDecodeError:
        flash('Invalid JSON content.', 'error')
        return redirect(url_for('index'))

    # Save safely
    with open(filepath, 'w') as f:
        json.dump(data, f)

    flash('JSON uploaded successfully.', 'success')
    return redirect(url_for('index'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)