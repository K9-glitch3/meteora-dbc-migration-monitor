FROM node:22-bookworm-slim@sha256:c3de60bf2f9dd0ac6370e6117950ff62d6e339527e7472301c9c78a017978392 AS sdk
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
COPY vendor ./vendor
RUN npm ci --ignore-scripts --no-fund && npm cache clean --force

FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NODE_OPTIONS=--max-old-space-size=256
WORKDIR /app
COPY --from=sdk /usr/local/bin/node /usr/local/bin/node
COPY --from=sdk /app/node_modules ./node_modules
COPY pyproject.toml LICENSE README.md ./
COPY dbc_monitor ./dbc_monitor
COPY scripts ./scripts
COPY docs/METEORA_SDK_LICENSE.txt ./docs/METEORA_SDK_LICENSE.txt
COPY package.json package-lock.json ./
COPY vendor ./vendor
RUN pip install --no-cache-dir . && mkdir /data && chown 65532:65532 /data
USER 65532:65532
EXPOSE 8898
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
  CMD python -c "import json,urllib.request; h=json.load(urllib.request.urlopen('http://127.0.0.1:8898/healthz',timeout=3)); assert h['status'] in ('live','degraded')"
CMD ["python", "scripts/serve_live.py", "--data", "/data", "--host", "0.0.0.0"]
