# ACFM-Net production image.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ACFM_MODEL_PATH=/home/acfm/models/fatigue.joblib \
    ACFM_WEB_DIR=/home/acfm/web

RUN useradd --create-home --shell /usr/sbin/nologin acfm \
    && mkdir -p /home/acfm/models \
    && chown -R acfm:acfm /home/acfm

WORKDIR /home/acfm

COPY requirements.txt pyproject.toml README.md LICENSE ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
RUN pip install --no-cache-dir --no-deps .

COPY app.py ./app.py
COPY web ./web
RUN chown -R acfm:acfm /home/acfm

USER acfm
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/api/health', timeout=3)"

ENTRYPOINT ["gunicorn"]
CMD ["--preload", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--access-logfile", "-", "app:app"]
