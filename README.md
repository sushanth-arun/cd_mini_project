# Adaptive Error Recovery Compiler

A web-based C compiler with intelligent error detection and automatic fix suggestions.

## Ports Configuration

- **Backend Server**: Port `8001` (http://127.0.0.1:8001)
- **Frontend Dev Server**: Port `5174` (http://localhost:5174)

## Quick Start

### Option 1: Using Helper Scripts

**Terminal 1 - Backend:**
```bash
chmod +x start_backend.sh
./start_backend.sh
```

**Terminal 2 - Frontend:**
```bash
chmod +x start_frontend.sh
./start_frontend.sh
```

### Option 2: Manual Start

**Terminal 1 - Backend:**
```bash
python3 local_server.py
```
Backend will run on: `http://127.0.0.1:8001`

**Terminal 2 - Frontend:**
```bash
npm run dev
```
Frontend will run on: `http://localhost:5174`

## Features

- ✅ Real-time error detection using clang
- ✅ Heuristic-based fix suggestions
- ✅ AI-powered error detection and fixes (Ollama)
- ✅ One-click fix application
- ✅ Fully local - no external APIs needed

## Requirements

- Python 3
- Node.js and npm
- clang (for compilation)
- Ollama (optional, for AI suggestions)

## Configuration

All ports are configured in:
- Backend: `local_server.py` (default port 8001)
- Frontend: `vite.config.ts` (port 5174)
- Frontend API URL: `src/App.tsx` (connects to http://127.0.0.1:8001)


