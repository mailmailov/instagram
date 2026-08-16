import os
import uuid
from flask import Flask, render_template, request, send_from_directory, flash, redirect, url_for
import yt_dlp

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me")

DOWNLOAD_DIR = os.path.join(app.root_path, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/download", methods=["POST"])
def download_video():
    url = request.form.get("url", "").strip()

    if not url:
        flash("Instagram video linkini daxil et.")
        return redirect(url_for("index"))

    if "instagram.com" not in url.lower():
        flash("Zəhmət olmasa Instagram linki daxil et.")
        return redirect(url_for("index"))

    job_id = uuid.uuid4().hex
    output_template = os.path.join(DOWNLOAD_DIR, f"{job_id}.%(ext)s")

    options = {
        "outtmpl": output_template,
        "format": "best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded = ydl.prepare_filename(info)

        # yt-dlp may change the extension after merging.
        candidates = [
            downloaded,
            os.path.splitext(downloaded)[0] + ".mp4",
            os.path.splitext(downloaded)[0] + ".webm",
            os.path.splitext(downloaded)[0] + ".mkv",
        ]

        file_path = next((p for p in candidates if os.path.exists(p)), None)

        if not file_path:
            flash("Video faylı yaradılmadı.")
            return redirect(url_for("index"))

        filename = os.path.basename(file_path)
        return render_template(
    "result.html",
    filename=filename,
    video_url=url_for("files", filename=filename)
)

    except Exception as exc:
        # Do not expose server internals to the visitor.
        print("Download error:", repr(exc))
        flash("Video yüklənmədi. Linkin açıq/public olduğuna və düzgün Instagram video linki olduğuna əmin ol.")
        return redirect(url_for("index"))

@app.route("/files/<path:filename>")
def files(filename):
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
