FROM node:22-alpine@sha256:2c752226d477b4a886378baa95b9af252be59301b725fdb0b7e15208131505a8 AS panel
WORKDIR /build/apps/panel
COPY apps/panel/package.json apps/panel/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY apps/panel/ ./
COPY licenses/ /build/licenses/
COPY THIRD_PARTY_NOTICES.md /build/THIRD_PARTY_NOTICES.md
ARG VITE_BASE_URL=/
ENV VITE_BASE_URL=${VITE_BASE_URL}
RUN npm run build

FROM python:3.12-slim-bookworm@sha256:2ed6491b93cd49272ee6de2b5a38440c3448360322c089fc23e370722d74179d AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ARCHIVE_DATA_DIR=/data \
    ARCHIVE_STATIC_DIR=/app/apps/panel/dist
WORKDIR /app
COPY archive_service/requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir --require-hashes -r /tmp/requirements.lock \
    && groupadd --gid 10001 archive \
    && useradd --uid 10001 --gid archive --no-create-home --home-dir /data archive \
    && install -d -o archive -g archive -m 0700 /data
COPY archive_service/ /app/archive_service/
COPY licenses/ /app/licenses/
COPY THIRD_PARTY_NOTICES.md LICENSE.md /app/
COPY --from=panel /build/apps/panel/dist/ /app/apps/panel/dist/
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "archive_service.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
