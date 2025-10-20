from flask import Flask, request, redirect, url_for, flash, render_template, jsonify
from werkzeug.utils import secure_filename
import os, json, requests, random, smtplib
from email.message import EmailMessage
from datetime import datetime, timezone

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
API_KEY = os.environ.get("HRFUNC_API_KEY")
app.secret_key = os.environ.get("SECRET_KEY")
UPLOAD_FOLDER = "/mnt/public/hrfunc/uploads"
TIMESTAMP_SUFFIX_FORMAT = "%Y-%m-%d_%H-%M-%S"


def send_confirmation_email(recipient, submission_metadata):
    """Send a confirmation email acknowledging receipt of the HRF submission."""
    if not recipient:
        return

    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    from_email = os.environ.get("SMTP_FROM_EMAIL")

    if not smtp_host or not from_email:
        app.logger.warning("Skipping confirmation email, SMTP configuration incomplete.")
        return

    msg = EmailMessage()
    msg["Subject"] = "HRF Submission Received"
    msg["From"] = from_email
    msg["To"] = recipient

    subset_value = (submission_metadata.get("dataset_subset") or "").strip().lower()
    if subset_value == "no":
        extra_note = (
            "We noticed this upload represents your full dataset. "
            "If you have the time, we encourage estimating HRFs from meaningful subsets "
            "(e.g., by demographic or condition) and sharing those as well — they help "
            "broaden representation and improve downstream analyses."
        )
    elif subset_value == "yes":
        extra_note = (
            "Thank you for going the extra mile to estimate HRFs from a subset of your data. "
            "These nuanced contributions deepen our shared understanding of variability."
        )
    else:
        extra_note = ""

    extra_note_block = f"{extra_note}\n\n" if extra_note else ""

    body = (
        f"Hello {submission_metadata.get('name', 'researcher')},\n\n"
        "Thank you for submitting your HRF estimates to HRfunc. We truly appreciate your "
        "contributions to the HRtree! Each HRF you share helps us understand hemodynamic "
        "response variability and supports more accurate neural activity estimation.\n\n"
        f"We successfully received your file '{submission_metadata.get('stored_filename')}'. "
        "At your earliest convenience, please review the details below and let us know at "
        "help@hrfunc.org if anything needs correction.\n\n"
        "Submission details:\n"
        f"  Study: {submission_metadata.get('study', 'N/A')}\n"
        f"  Area Codes: {submission_metadata.get('area_codes', 'N/A')}\n"
        f"  DOI: {submission_metadata.get('doi', 'N/A')}\n"
        f"  Email: {submission_metadata.get('email', 'N/A')}\n"
        f"  Phone Number: {submission_metadata.get('phone', 'N/A')}\n"
        f"  Dataset Ownership: {submission_metadata.get('dataset_ownership', 'N/A')}\n"
        f"  Dataset Permission: {submission_metadata.get('dataset_permission', 'N/A')}\n"
        f"  Dataset Owner: {submission_metadata.get('dataset_owner', 'N/A')}\n"
        f"  Dataset Owner Email: {submission_metadata.get('dataset_contact', 'N/A')}\n"
        f"  Used Unaltered HRfunc: {submission_metadata.get('hrfunc_standard', 'N/A')}\n"
        f"  Dataset Subset: {submission_metadata.get('dataset_subset', 'N/A')}\n"
        f"  Uploaded at (UTC): {submission_metadata.get('uploaded_at', 'N/A')}\n\n"
        "HRF experimental context:\n"
        f"  Task: {submission_metadata.get('task', 'N/A')}\n"
        f"  Condition(s): {submission_metadata.get('conditions', 'N/A')}\n"
        f"  Stimuli: {submission_metadata.get('stimuli', 'N/A')}\n"
        f"  Stimuli Medium: {submission_metadata.get('medium', 'N/A')}\n"
        f"  Stimuli Intensity: {submission_metadata.get('intensity', 'N/A')}\n"
        f"  Protocol: {submission_metadata.get('protocol', 'N/A')}\n"
        f"  Age: {submission_metadata.get('age', 'N/A')}\n"
        f"  Demographics: {submission_metadata.get('demographics', 'N/A')}\n"
        f"  Additional Comment: {submission_metadata.get('comment', 'N/A') or 'N/A'}\n\n"
        f"{extra_note_block}"
        "We greatly appreciate your contribution to the HRfunc community and "
        "cannot wait to hear about the insights you uncover!\n\n"
        "Best,\n"
        "The HRfunc Team"
    )
    msg.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            if smtp_user and smtp_password:
                server.starttls()
                server.login(smtp_user, smtp_password)
            server.send_message(msg)
    except OSError:
        app.logger.exception("Unable to send confirmation email.")

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
    # ---- Extract file ----
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
    filename = f"{name_root}_{timestamp_suffix}_{random.randint(1, 10000)}{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    # ---- Read bytes and validate JSON ----
    original_bytes = file.read()
    try:
        data = json.loads(original_bytes.decode("utf-8"))
    except json.JSONDecodeError:
        flash("Invalid JSON content.", "error")
        return redirect(url_for("hrf_upload"))

    # ---- Merge submission metadata into payload ----
    submission = request.form.to_dict(flat=True)
    submission.setdefault("area_codes", request.form.get("area-codes", ""))
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

    # ---- Forward to API ----
    try:
        resp = requests.post(
            "https://flask.jib-jab.org/upload_json",
            files={"jsonFile": (filename, augmented_bytes)},
            headers={"x-api-key": API_KEY},
            timeout=10,
        )
    except Exception as e:
        flash(f"Error contacting API: {e}", "error")
        return redirect(url_for("hrf_upload"))

    # ---- Handle response ----
    if resp.status_code == 200:
        send_confirmation_email(submission_metadata.get("email"), submission_metadata)
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
