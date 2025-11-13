import logging
import os
import sys
import platform
import subprocess
import shutil

logger = logging.getLogger(__name__)

class EnvironmentManager:
    @staticmethod
    def validate_virtualenv():
        """
        Pastikan script dijalankan di dalam virtual environment.
        """
        if sys.prefix == sys.base_prefix:
            logger.error("❌ Not running inside a virtual environment. Use ./setup.sh instead.")
            sys.exit(1)
        venv_path = os.environ.get("VIRTUAL_ENV", "(unknown)")
        logger.info(f"✓ Running inside virtual environment: {venv_path}")

    @staticmethod
    def check_system_info():
        """
        Menampilkan informasi dasar OS, kernel, dan package penting.
        """
        logger.info("Collecting system information...")
        uname = platform.uname()
        logger.info(f"System: {uname.system}")
        logger.info(f"Node Name: {uname.node}")
        logger.info(f"Release: {uname.release}")
        logger.info(f"Version: {uname.version}")
        logger.info(f"Machine: {uname.machine}")
        logger.info(f"Processor: {uname.processor}")

        # Kernel version (for compatibility check)
        try:
            kernel_version = subprocess.check_output(["uname", "-r"], text=True).strip()
            logger.info(f"Kernel Version: {kernel_version}")
        except Exception as e:
            logger.warning(f"Could not fetch kernel version: {e}")
            kernel_version = None

        # Check Python version inside venv
        logger.info(f"Python Executable: {sys.executable}")
        logger.info(f"Python Version: {platform.python_version()}")

        # Check if gcc is available
        gcc_path = shutil.which("gcc")
        if gcc_path:
            logger.info(f"✓ GCC found at {gcc_path}")
        else:
            logger.warning("⚠️ GCC not found. Some modules (e.g. psutil) may fail to build.")

        # Detect package manager
        pkg_mgr = EnvironmentManager.detect_package_manager()
        logger.info(f"Detected Package Manager: {pkg_mgr}")

        # Return structured data for possible future logic
        return {
            "os": uname.system,
            "kernel": kernel_version,
            "python": platform.python_version(),
            "gcc": gcc_path,
            "pkg_mgr": pkg_mgr
        }

    @staticmethod
    def detect_package_manager():
        """
        Mendeteksi package manager yang digunakan (apt, yum, dnf, zypper, dll.)
        """
        if shutil.which("apt"):
            return "apt"
        elif shutil.which("dnf"):
            return "dnf"
        elif shutil.which("yum"):
            return "yum"
        elif shutil.which("zypper"):
            return "zypper"
        else:
            return "unknown"

    @staticmethod
    def run_command(cmd, cwd=None):
        """
        Helper untuk menjalankan command shell dengan logging.
        """
        logger.debug(f"Running command: {cmd}")
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                shell=isinstance(cmd, str),
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.stdout:
                logger.debug(result.stdout.strip())
            if result.stderr:
                logger.debug(result.stderr.strip())
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e.cmd}\n{e.stderr}")
            raise

