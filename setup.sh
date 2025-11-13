#!/usr/bin/env bash
set -e

VENV_DIR=".venv_cte"

# ---- [Utility function for logging] ----
log() { echo -e "[setup_cte] $1"; }

# ---- [Parse CLI argument to forward later] ----
ARGS="$@"

# ---- [1. Basic checks] ----
log "Checking Python3 availability..."
if ! command -v python3 >/dev/null 2>&1; then
  log "❌ Python3 not found. Please install it first."
  exit 1
fi

# ---- [2. Check GCC for psutil build] ----
if ! command -v gcc >/dev/null 2>&1; then
  log "❌ gcc not installed. Please install it first (e.g., sudo yum install gcc python3-devel -y)."
  exit 1
fi

# ---- [3. Create venv if not exists] ----
if [ ! -d "$VENV_DIR" ]; then
  log "Creating virtual environment in $VENV_DIR ..."
  python3 -m venv "$VENV_DIR"
else
  log "Virtual environment already exists."
fi

# ---- [4. Activate venv] ----
source "$VENV_DIR/bin/activate"

# ---- [5. Upgrade pip and ensure dependencies installed] ----
REQ_FILE="requirements.txt"
if [ ! -f "$REQ_FILE" ]; then
  log "❌ Missing requirements.txt!"
  exit 1
fi

if [ ! -f "$VENV_DIR/.deps_installed" ]; then
  log "Installing dependencies..."
  pip install --upgrade pip wheel setuptools >/dev/null
  pip install -r "$REQ_FILE"
  touch "$VENV_DIR/.deps_installed"
  log "Dependencies installed successfully."
else
  log "Dependencies already satisfied (cached)."
fi

# ---- [6. Run main.py inside venv] ----
if [ ! -f "main.py" ]; then
  log "❌ main.py not found in current directory."
  exit 1
fi

log "Running main.py with arguments: $ARGS"
python main.py $ARGS
