# ---- 1) 프론트엔드 빌드 ----
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY budget/frontend/package*.json ./
RUN npm install
COPY budget/frontend/ ./
RUN npm run build

# ---- 2) 백엔드 런타임 ----
FROM python:3.12-slim
WORKDIR /app

COPY budget/backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY budget/backend/ ./backend/
COPY --from=frontend /app/frontend/dist ./frontend/dist

WORKDIR /app/backend
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
