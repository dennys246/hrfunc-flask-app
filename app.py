from flask import Flask, request, redirect, url_for, flash, render_template, jsonify
from werkzeug.utils import secure_filename
import os, json, requests, csv
from datetime import datetime, timezone

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
API_KEY = os.environ.get("HRFUNC_API_KEY")
app.secret_key = os.environ.get("SECRET_KEY")
UPLOAD_FOLDER = "/mnt/public/hrfunc/uploads"
FORM_RESPONSES_CSV = os.path.join(UPLOAD_FOLDER, "hrf_form_responses.csv")
FORM_FIELD_ORDER = [
    "name",
    "email",
    "phone",
    "doi",
    "study",
    "hrfunc_standard",
    "dataset_subset",
    "task",
    "conditions",
    "stimuli",
    "intensity",
    "protocol",
    "age",
    "demographics",
    "comment",
]
TIMESTAMP_SUFFIX_FORMAT = "%Y-%m-%dT_%H-%M-%SZ"


def append_submission_to_csv(submission, stored_filename, uploaded_at_iso, original_filename):
    """Append a sanitized form submission to the shared CSV log."""
    csv_exists = os.path.isfile(FORM_RESPONSES_CSV)
    row = {field: submission.get(field, "") for field in FORM_FIELD_ORDER}
    row["original_filename"] = original_filename
    row["json_filename"] = stored_filename
    row["uploaded_at"] = uploaded_at_iso

    try:
        with open(FORM_RESPONSES_CSV, "a", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=FORM_FIELD_ORDER
                + ["original_filename", "json_filename", "uploaded_at"],
            )
            if not csv_exists:
                writer.writeheader()
            writer.writerow(row)
    except OSError:
        app.logger.exception("Unable to record HRF form submission to CSV.")

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
    file_bytes = file.read()
    try:
        data = json.loads(file_bytes.decode("utf-8"))
    except json.JSONDecodeError:
        flash("Invalid JSON content.", "error")
        return redirect(url_for("hrf_upload"))

    # ---- 3. Forward to API ----
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

    # ---- 4. Gather metadata from form ----
    submission = request.form.to_dict(flat=True)
    uploaded_at_iso = uploaded_at.isoformat()
    submission["uploaded_at"] = uploaded_at_iso

    # ---- 5. Persist form submission metadata ----
    append_submission_to_csv(submission, filename, uploaded_at_iso, original_filename)

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
