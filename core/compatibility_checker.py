# core/compatibility_checker.py
import requests
import pdfplumber
import re
import json
import warnings
from utils.command import run_shell
from utils import config
from core.logger import get_logger

logger = get_logger(__name__)
warnings.filterwarnings("ignore", message="Could get FontBBox")

import logging
logging.getLogger("pdfminer").setLevel(logging.ERROR)

class CompatibilityChecker:
    def __init__(self,
                 json_url="https://packages.vormetric.com/pub/cte_compatibility_matrix.json",
                 pdf_path="./data/cte_release_status.pdf"):
        self.json_url = json_url
        self.pdf_path = pdf_path

    # === Ambil kernel version ===
    def get_kernel_version(self):
        out = run_shell("uname -r")
        return out.strip()

    # === Ambil matrix JSON dari Thales ===
    def fetch_cte_compatibility(self):
        logger.info(f"Fetching CTE compatibility matrix from {self.json_url}")
        resp = requests.get(self.json_url, timeout=15)
        resp.raise_for_status()
        return resp.json()

    # === Parse PDF support status ===
    def parse_cte_support_status(self):
        logger.info(f"Parsing CTE release support status from {self.pdf_path}")
        results = {}
        pattern = re.compile(r"^(\d+\.\d+\.\d+)\s+[\dA-Za-z-]+\s+([A-Za-z\s]+)$")

        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                for line in text.splitlines():
                    match = pattern.match(line.strip())
                    if match:
                        version, status = match.groups()
                        results[version.strip()] = status.strip()

        return results

    # === Cek kernel di JSON matrix + tambahkan support PDF ===
    def check_kernel_support(self, kernel_version):
        try:
            data = self.fetch_cte_compatibility()
            support_data = self.parse_cte_support_status()
        except Exception as e:
            logger.error(f"Failed to load compatibility data: {e}")
            return None

        results = []
        for os_entry in data["MAPPING"]:
            for k in os_entry["KERNEL"]:
                if kernel_version in k["NUM"]:
                    compat = "Active" if k["END"] == "0" else f"Supported until {k['END']}"
                    cte_version_base = '.'.join(k["START"].split('.')[:3])
                    support_status = support_data.get(cte_version_base, "Unknown")

                    results.append({
                        "OS": os_entry["OS"],
                        "CTE Start": k["START"],
                        "CTE End": k["END"],
                        "Compatibility": compat,
                        "Support Status": support_status
                    })

        if not results:
            logger.warning(f"No entry found for kernel: {kernel_version}")
            return None

        return results

    # === Cetak hasil dalam tabel rapi ===
    def print_table(self, results):
        if not results:
            logger.warning("No results to display.")
            return

        headers = ["OS", "CTE Start", "CTE End", "Compatibility", "Support"]
        col_widths = [max(len(str(row[h])) for row in results + [dict(zip(headers, headers))]) for h in headers]
        sep = "╬".join("═" * (w + 2) for w in col_widths)

        print("╔" + sep.replace("╬", "╦") + "╗")
        print("║ " + " ║ ".join(headers[i].ljust(col_widths[i]) for i in range(len(headers))) + " ║")
        print("╠" + sep.replace("╬", "╬") + "╣")
        for r in results:
            print("║ " + " ║ ".join(str(r[h]).ljust(col_widths[i]) for i, h in enumerate(headers)) + " ║")
        print("╚" + sep.replace("╬", "╩") + "╝")

    # === Kesimpulan (summary) singkat ===
    def summarize_compatibility(self, results):
        if not results:
            return {"compatible": False, "reason": "Kernel not found"}

        # Jika salah satu masih Active → dianggap compatible
        active = any("Active" in r["Compatibility"] or "Active" in r["Support"] for r in results)
        if active:
            return {"compatible": True, "reason": "CTE version still active"}
        return {"compatible": False, "reason": "End of Support"}
