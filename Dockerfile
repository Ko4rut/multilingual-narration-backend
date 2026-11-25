FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app \
    && mkdir -p /var/lib/mnr/offline-manifests \
    && chown -R app:app /var/lib/mnr

COPY requirements.txt ./
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

COPY --chown=app:app alembic ./alembic
COPY --chown=app:app app ./app
COPY --chown=app:app assets ./assets
# Giữ một bản chỉ đọc bên ngoài mount point. Named volume có sẵn không tự nhận
# file mới từ image sau khi rebuild, nên API dùng bản này để bổ sung seed assets.
COPY --chown=app:app assets/images/pois ./seed-assets/poi-images
COPY --chown=app:app scripts ./scripts
COPY --chown=app:app alembic.ini ./

# Thư mục runtime nằm trong source tree theo cấu hình hiện tại. Quyền sở hữu này
# cũng được dùng để khởi tạo named volume trong lần chạy Docker đầu tiên.
RUN mkdir -p /app/assets/audio/tts /app/assets/images/pois \
    && chown -R app:app /app/assets

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
