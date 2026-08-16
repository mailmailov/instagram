# Instagram Video Downloader

Python 3 + Flask + yt-dlp layihəsidir.

## Lokal test
python -m venv venv
Windows:
venv\Scripts\activate
pip install -r requirements.txt
python app.py

Brauzerdə:
http://127.0.0.1:5000

## Render
Build Command:
pip install -r requirements.txt

Start Command:
gunicorn app:app

`render.yaml` bunu avtomatik təsvir edir.

## İstifadə
Instagram Reel/video linkini yapışdır və "VİDEONU YÜKLƏ" düyməsinə bas.

Qeyd: yalnız açıq/public və istifadə etməyə icazən olan məzmunu endirmək üçün istifadə et. Private hesablar üçün login/cookie bypass daxil edilməyib.

Qeyd: Render-in adi web-service fayl sistemi daimi media saxlama üçün nəzərdə tutulmayıb. Yüklənən faylları uzunmüddətli saxlamaq lazımdırsa persistent disk və ya object storage əlavə edilməlidir.
