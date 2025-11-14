#!/usr/bin/env python3
# /usr/bin/cte_client.py
"""
CTE Client Integration - Thales CipherTrust Manager
Author: Nera Project
Date: 2025-11-05
"""

import os
import re
import json
import platform
import requests
import subprocess
from pathlib import Path
from typing import Optional

# ======================
# CONFIG
# ======================
GITHUB_INFO_URL = "https://raw.githubusercontent.com/Nera-Project/enrolling_thales_cte/main/main_package.info"
COMPAT_MATRIX_URL = "https://packages.vormetric.com/pub/cte_compatibility_matrix.json"
LOCAL_MATRIX_FILE = Path("data/cte_compatibility_matrix.json")
DEFAULT_DOWNLOAD_PATH = Path("/tmp/cte_downloads")


# ======================
# UTILITY CLASSES
# ======================

class SystemInfo:
    """Collects local system OS and kernel information."""

    def __init__(self):
        self.os_name = self.detect_os_name()
        self.kernel_version = platform.release()

    @staticmethod
    def detect_os_name() -> str:
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME"):
                        name = line.split("=")[1].strip().strip('"')
                        return name
        except FileNotFoundError:
            pass
        return platform.system()

    def __repr__(self):
        return f"<SystemInfo OS={self.os_name}, Kernel={self.kernel_version}>"


class ThalesCompatibilityMatrix:
    """Loads and validates Thales CTE compatibility data."""

    def __init__(self):
        self.data = self._load_matrix()

    def _load_matrix(self) -> dict:
        """Try to load matrix from local cache, else from internet."""
        if LOCAL_MATRIX_FILE.exists():
            with open(LOCAL_MATRIX_FILE) as f:
                print("📄 Using cached compatibility matrix.")
                return json.load(f)
        else:
            print("🌐 Downloading latest Thales compatibility matrix...")
            resp = requests.get(COMPAT_MATRIX_URL, timeout=10)
            resp.raise_for_status()
            LOCAL_MATRIX_FILE.parent.mkdir(parents=True, exist_ok=True)
            LOCAL_MATRIX_FILE.write_text(resp.text)
            return resp.json()

    def get_supported_version(self, kernel: str) -> Optional[str]:
        """Return the highest compatible CTE version for a given kernel."""
        for entry in self.data.get("MAPPING", []):
            for kdata in entry["KERNEL"]:
                if kernel.startswith(kdata["NUM"].split(".x86_64")[0]):
                    return kdata["START"]
        return None


class RepositoryLocator:
    """Finds the current active repository endpoint from GitHub info file."""

    def __init__(self):
        self.repo_url = self._fetch_repo_url()

    def _fetch_repo_url(self) -> str:
        resp = requests.get(GITHUB_INFO_URL, timeout=10)
        resp.raise_for_status()
        match = re.search(r'https://[^\s"]+', resp.text)
        if not match:
            raise ValueError("❌ Failed to parse repo URL from GitHub info.")
        return match.group(0)

    def get_repo_url(self) -> str:
        return self.repo_url


class BinaryDownloader:
    """Downloads the correct binary from repo if compatible."""

    def __init__(self, repo_url: str):
        self.repo_url = repo_url
        DEFAULT_DOWNLOAD_PATH.mkdir(exist_ok=True)

    @staticmethod
    def _guess_os_code(os_name: str) -> Optional[str]:
        """Detect target folder name like rh8, rh9, ubuntu24 based on OS name."""
        os_name = os_name.lower()
        if "rhel 8" in os_name or "centos 8" in os_name:
            return "rh8"
        elif "rhel 9" in os_name:
            return "rh9"
        elif "ubuntu 24" in os_name:
            return "ubuntu24"
        elif "oracle linux 10" in os_name or "oel10" in os_name:
            return "oel10"
        else:
            return None

    def download_binary(self, os_name: str, version: str) -> Optional[Path]:
        os_code = self._guess_os_code(os_name)
        if not os_code:
            print(f"❌ Tidak bisa mendeteksi OS target dari: {os_name}")
            return None

        binary_name = f"vee-fs-{version}-{os_code}-x86_64.bin"
        file_url = f"{self.repo_url}/cte/bin/{os_code}/latest/{binary_name}"
        dest_path = DEFAULT_DOWNLOAD_PATH / binary_name

        print(f"⬇️  Downloading {binary_name} from {file_url}")
        resp = requests.get(file_url, stream=True, timeout=15)

        if resp.status_code != 200:
            print(f"❌ File {binary_name} tidak ditemukan di repo.")
            return None

        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        os.chmod(dest_path, 0o755)
        print(f"✅ Binary disimpan di {dest_path}")
        return dest_path


# ======================
# MAIN CONTROLLER
# ======================

class CTEClient:
    """Main orchestrator for checking compatibility and fetching binary."""

    def __init__(self):
        print("🚀 Initializing CTE Client...")
        self.sys_info = SystemInfo()
        self.matrix = ThalesCompatibilityMatrix()
        self.repo = RepositoryLocator()
        self.downloader = BinaryDownloader(self.repo.get_repo_url())

    def check_compatibility_and_download(self):
        print(f"🧩 System Detected: {self.sys_info}")
        supported_version = self.matrix.get_supported_version(self.sys_info.kernel_version)

        if not supported_version:
            print("⚠️ Tidak ditemukan versi CTE yang kompatibel untuk kernel ini.")
            return

        print(f"✅ Ditemukan versi kompatibel: {supported_version}")
        downloaded = self.downloader.download_binary(self.sys_info.os_name, supported_version)
        if downloaded:
            print(f"🎉 Selesai. Binary siap diinstal: {downloaded}")
        else:
            print("⚠️ Binary tidak tersedia di repo untuk versi tersebut.")


# ======================
# ENTRY POINT
# ======================

if __name__ == "__main__":
    client = CTEClient()
    client.check_compatibility_and_download()
