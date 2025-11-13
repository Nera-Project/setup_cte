import subprocess
from core.logger import get_logger

logger = get_logger(__name__)

def run_shell(cmd, check=True, capture_output=True, text=True):
    """Run shell command and return stdout. Raises subprocess.CalledProcessError on error when check=True."""
    logger.debug("Running shell command: %s", cmd)
    if isinstance(cmd, str):
        proc = subprocess.run(cmd, shell=True, check=check, capture_output=capture_output, text=text)
    else:
        proc = subprocess.run(cmd, check=check, capture_output=capture_output, text=text)
    if capture_output:
        return proc.stdout
    return None
