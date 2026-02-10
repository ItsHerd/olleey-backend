#!/bin/bash
# Development server startup script with proper file watching

python3 -m uvicorn main:app \
  --reload \
  --reload-dir ./routers \
  --reload-dir ./services \
  --reload-dir ./schemas \
  --reload-dir ./middleware \
  --reload-dir ./utils \
  --reload-dir ./scripts \
  --reload-include "*.py" \
  --reload-include ".env" \
  --host 0.0.0.0 \
  --port 8000
