import subprocess
from core.logger import get_logger

logger = get_logger(__name__)

def run_shell(cmd, check=True, capture_output=True, text=True):
    """
    Run shell command and return stdout.
    Compatible with Python 3.6+ (no capture_output/text native support).
    Raises subprocess.CalledProcessError if check=True and exit code != 0.
    """
    logger.debug("Running shell command: %s", cmd)

    # Menentukan argumen stdout/stderr secara manual agar kompatibel
    kwargs = {}
    if capture_output:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE

    # Python 3.6 belum punya argumen text=True, pakai universal_newlines
    kwargs["universal_newlines"] = text

    if isinstance(cmd, str):
        proc = subprocess.run(cmd, shell=True, check=check, **kwargs)
    else:
        proc = subprocess.run(cmd, check=check, **kwargs)

    if capture_output:
        return proc.stdout.strip() if proc.stdout else ""
    return None
