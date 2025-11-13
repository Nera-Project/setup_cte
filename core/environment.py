import os
import subprocess
import sys
from pathlib import Path
from core.logger import get_logger

logger = get_logger(__name__)

class EnvironmentManager:
    def __init__(self, venv_path=".venv", use_venv=True):
        self.venv_path = Path(venv_path)
        self.use_venv = use_venv

    def ensure_environment(self):
        if not self.use_venv:
            logger.info("Skipping virtualenv creation (use_venv=False).")
            return
        if not self.venv_path.exists():
            logger.info("Creating virtual environment at %s", self.venv_path)
            subprocess.run([sys.executable, "-m", "venv", str(self.venv_path)], check=True)
        else:
            logger.info("Virtual environment exists at %s", self.venv_path)

    def pip_path(self):
        if self.use_venv:
            # Unix-style path
            return str(self.venv_path / "bin" / "pip")
        return sys.executable.replace("python", "pip") if "python" in sys.executable else "pip"

    def install_requirements(self, req_file="requirements.txt"):
        if not Path(req_file).exists():
            logger.warning("No requirements.txt found at %s. Skipping pip install.", req_file)
            return
        pip = self.pip_path()
        logger.info("Installing requirements from %s using %s", req_file, pip)
        subprocess.run([pip, "install", "-r", req_file], check=True)
