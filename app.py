import os
import time
import uuid
import threading
from pathlib import Path

from flask import (
    Flask,
    render_template,
    request,
    send_from_directory,
    jsonify,
    abort
)

import yt_dlp


app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "change-this-secret"
)


DOWNLOAD_DIR = Path(app.root_path) / "downloads"

DOWNLOAD_DIR.mkdir(
    exist_ok=True
)


MAX_AGE = int(
    os.environ.get(
        "FILE_MAX_AGE_SECONDS",
        "1800"
    )
)


jobs = {}

lock = threading.Lock()


# =========================================
# KÖHNƏ FAYLLARI SİL
# =========================================

def cleanup():

    now = time.time()

    for file in DOWNLOAD_DIR.iterdir():

        if not file.is_file():
            continue

        if file.name == ".gitkeep":
            continue

        try:

            age = now - file.stat().st_mtime

            if age > MAX_AGE:
                file.unlink()

        except OSError:
            pass


# =========================================
# INSTAGRAM LINK YOXLAMA
# =========================================

def valid_url(url):

    url = url.lower().strip()

    return (
        "instagram.com/" in url
        and
        url.startswith(
            (
                "http://",
                "https://"
            )
        )
    )


# =========================================
# JOB MƏLUMATLARINI YENİLƏ
# =========================================

def set_job(job_id, **values):

    with lock:

        if job_id not in jobs:
            jobs[job_id] = {}

        jobs[job_id].update(values)


# =========================================
# VIDEO YÜKLƏ
# =========================================

def download_worker(
    job_id,
    url,
    quality
):

    formats = {

        "best":
            "bestvideo+bestaudio/best",

        "1080":
            "bestvideo[height<=1080]+bestaudio/"
            "best[height<=1080]/best",

        "720":
            "bestvideo[height<=720]+bestaudio/"
            "best[height<=720]/best",

        "480":
            "bestvideo[height<=480]+bestaudio/"
            "best[height<=480]/best",

        "360":
            "bestvideo[height<=360]+bestaudio/"
            "best[height<=360]/best"

    }


    output = str(
        DOWNLOAD_DIR /
        f"{job_id}.%(ext)s"
    )


    # =====================================
    # PROGRESS
    # =====================================

    def progress_hook(data):

        status = data.get(
            "status"
        )


        if status == "downloading":

            total = (
                data.get("total_bytes")
                or
                data.get("total_bytes_estimate")
                or
                0
            )


            downloaded = (
                data.get("downloaded_bytes")
                or
                0
            )


            if total:

                percent = round(
                    downloaded * 100 / total,
                    1
                )

            else:

                percent = 0


            set_job(

                job_id,

                status="downloading",

                progress=percent,

                speed=data.get(
                    "_speed_str",
                    ""
                )

            )


        elif status == "finished":

            set_job(

                job_id,

                status="processing",

                progress=100

            )


    # =====================================
    # YT-DLP
    # =====================================

    options = {

        "outtmpl": output,

        "format":
            formats.get(
                quality,
                formats["best"]
            ),

        "merge_output_format":
            "mp4",

        "noplaylist":
            True,

        "quiet":
            True,

        "no_warnings":
            True,

        "progress_hooks":
            [progress_hook]

    }


    try:

        cleanup()


        with yt_dlp.YoutubeDL(
            options
        ) as ydl:

            info = ydl.extract_info(
                url,
                download=True
            )


            prepared = ydl.prepare_filename(
                info
            )


        # =================================
        # YARANMIŞ FAYLI TAP
        # =================================

        candidates = [

            Path(prepared),

            Path(
                os.path.splitext(
                    prepared
                )[0]
                + ".mp4"
            ),

            Path(
                os.path.splitext(
                    prepared
                )[0]
                + ".mkv"
            ),

            Path(
                os.path.splitext(
                    prepared
                )[0]
                + ".webm"
            )

        ]


        video_file = next(

            (
                file
                for file in candidates
                if file.exists()
            ),

            None

        )


        if not video_file:

            raise RuntimeError(
                "Downloaded file not found"
            )


        # =================================
        # NƏTİCƏ
        # =================================

        file_size = (
            video_file.stat().st_size
        )


        duration = (
            info.get("duration")
            or
            0
        )


        title = (
            info.get("title")
            or
            "Instagram Video"
        )


        set_job(

            job_id,

            status="done",

            progress=100,

            filename=
                video_file.name,

            size=
                file_size,

            duration=
                duration,

            title=
                title

        )


    except Exception as error:

        print(
            "Download error:",
            repr(error)
        )


        set_job(

            job_id,

            status="error",

            error=
                "Video yüklənmədi. "
                "Link açıq/public və "
                "düzgün Instagram linki olmalıdır."

        )


# =========================================
# ANA SƏHİFƏ
# =========================================

@app.get("/")
def index():

    cleanup()

    return render_template(
        "index.html"
    )


# =========================================
# DOWNLOAD BAŞLAT
# =========================================

@app.post("/download")
def start_download():

    url = request.form.get(
        "url",
        ""
    ).strip()


    quality = request.form.get(
        "quality",
        "best"
    )


    if not valid_url(url):

        return jsonify({

            "error":
                "invalid"

        }), 400


    job_id = uuid.uuid4().hex


    set_job(

        job_id,

        status="starting",

        progress=0

    )


    thread = threading.Thread(

        target=download_worker,

        args=(
            job_id,
            url,
            quality
        ),

        daemon=True

    )


    thread.start()


    return jsonify({

        "job_id":
            job_id

    })


# =========================================
# STATUS
# =========================================

@app.get("/status/<job_id>")
def status(job_id):

    with lock:

        data = dict(
            jobs.get(
                job_id,
                {}
            )
        )


    if not data:

        return jsonify({

            "status":
                "error",

            "error":
                "Job tapılmadı"

        }), 404


    return jsonify(
        data
    )


# =========================================
# RESULT SƏHİFƏSİ
# =========================================

@app.get("/result")
def result():

    return render_template(
        "result.html"
    )


# =========================================
# VIDEO PREVIEW
# =========================================

@app.get("/preview/<path:filename>")
def preview(filename):

    file = (
        DOWNLOAD_DIR /
        filename
    )


    if not file.is_file():

        abort(404)


    return send_from_directory(

        DOWNLOAD_DIR,

        filename,

        as_attachment=False

    )


# =========================================
# VIDEO DOWNLOAD
# =========================================

@app.get("/files/<path:filename>")
def files(filename):

    file = (
        DOWNLOAD_DIR /
        filename
    )


    if not file.is_file():

        abort(404)


    return send_from_directory(

        DOWNLOAD_DIR,

        filename,

        as_attachment=True

    )


# =========================================
# SERVER
# =========================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            "5000"
        )
    )


    app.run(

        host="0.0.0.0",

        port=port

    )
