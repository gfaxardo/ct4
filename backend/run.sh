#!/usr/bin/env bash
# Ejecutar el backend (FastAPI + Uvicorn)
cd "$(dirname "$0")"
.venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
