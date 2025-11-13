import os
import shutil
import stat
from pathlib import Path
import requests
from core.logger import get_logger
from utils.command import run_shell
from utils.config import DEFAULT_CLOUDFLARE_DOMAIN_PATTERN
from utils.exceptions import InstallerError
import re

logger = get_logger(__name__)

class Installer:
    def __init__(self, repo_manager, download_dir="/tmp/cte_download"):
        self.repo_manager = repo_manager
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def determine_target(self):
        # determine distro family (rh8/rh9/ubuntu22/ubuntu24)
        out = run_shell("cat /etc/os-release || true")
        if "rhel" in out.lower() or "centos" in out.lower() or "rocky" in out.lower():
            # map kernel to rh8 vs rh9 maybe by checking /etc/redhat-release or kernel
            release = run_shell("cat /etc/redhat-release || true").lower()
            if "9." in release:
                return "rh9"
            return "rh8"
        if "ubuntu" in out.lower():
            # check version id
            m = re.search(r'VERSION_ID="?([0-9\.]+)"?', out)
            if m:
                v = m.group(1)
                if v.startswith("24"):
                    return "ubuntu24"
                return "ubuntu22"
            return "ubuntu22"
        # fallback
        logger.warning("Unable to auto-detect distro; defaulting to 'ubuntu22'")
        return "ubuntu22"

    def perform_install(self):
        repo_url = self.repo_manager.fetch_active_repo_url()
        target = self.determine_target()
        logger.info("Selected distro target: %s", target)
        # craft download URL - expecting structure /cte/bin/<target>/latest/<binary>
        index_url = f"{repo_url}/cte/bin/{target}/latest/"
        logger.info("Fetching index URL: %s", index_url)
        resp = requests.get(index_url, timeout=10)
        resp.raise_for_status()
        # try to find .bin file in listing by simple regex
        m = re.search(r'href="([^"]+\.bin)"', resp.text)
        if not m:
            raise InstallerError("No .bin file found in repository 'latest' index.")
        filename = m.group(1)
        download_url = f"{index_url}{filename}"
        logger.info("Downloading binary: %s", download_url)
        local_path = self.download_dir / filename
        with requests.get(download_url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(local_path, "wb") as fh:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        fh.write(chunk)
        # make executable
        local_path.chmod(local_path.stat().st_mode | stat.S_IXUSR)
        logger.info("Downloaded to %s", local_path)
        # now run installer silently if the binary supports --silent or --install
        self._run_binary_installer(local_path)

    def _run_binary_installer(self, path: Path):
        # WARNING: adjust flags according to binary docs
        cmd = f"{str(path)} --install --quiet"
        logger.info("Running installer command: %s", cmd)
        try:
            out = run_shell(cmd)
            logger.info("Installer output: %s", out[:400])
        except Exception as e:
            logger.error("Installer failed: %s", e)
            raise InstallerError("CTE binary installer failed") from e
