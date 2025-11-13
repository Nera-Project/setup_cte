from utils.command import run_shell
import requests
from utils.parser import parse_portal_table
from utils import config
from core.logger import get_logger

logger = get_logger(__name__)

class CompatibilityChecker:
    def __init__(self, base_url=config.THALES_CM_URL):
        self.base_url = base_url

    def get_kernel_version(self):
        out = run_shell("uname -r")
        return out.strip()

    def check_kernel_support(self, kernel_version):
        qurl = f"{self.base_url}?sideBarIndex=0&radioOption=KERNEL&search={kernel_version}"
        logger.info("Querying Thales compatibility matrix: %s", qurl)
        try:
            resp = requests.get(qurl, timeout=15)
        except Exception as e:
            logger.error("Failed to request Thales portal: %s", e)
            return None

        text = resp.text
        # Detect Angular single-page app
        if "<app-root" in text or "runtime.js" in text or "main.js" in text:
            logger.warning("Thales portal appears to be a dynamic SPA (Angular). Cannot scrape table reliably.")
            logger.info("Please open the following URL in a browser for manual verification: %s", qurl)
            return None

        table = parse_portal_table(text)
        if not table:
            logger.warning("No compatibility table parsed from Thales portal response.")
            return None

        return table

    def print_table(self, table):
        """Pretty-print the compatibility table."""
        if not table or len(table) < 2:
            logger.warning("No valid table data to print.")
            return

        headers = table[0]
        rows = table[1:]
        col_widths = [max(len(str(row[i])) for row in rows + [headers]) for i in range(len(headers))]

        sep = "╬".join("═" * (w + 2) for w in col_widths)
        print("╔" + sep.replace("╬", "╦") + "╗")
        print("║ " + " ║ ".join(headers[i].ljust(col_widths[i]) for i in range(len(headers))) + " ║")
        print("╠" + sep.replace("╬", "╬") + "╣")
        for row in rows:
            print("║ " + " ║ ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(headers))) + " ║")
        print("╚" + sep.replace("╬", "╩") + "╝")

    def summarize_compatibility(self, table):
        """Try to infer whether the kernel appears supported based on table content."""
        if not table or len(table) < 2:
            return {"compatible": False, "reason": "No compatibility data found"}

        headers = [h.lower() for h in table[0]]
        rows = table[1:]
        # Simple heuristic: check if "status" column mentions active / extended / supported
        status_idx = None
        for i, h in enumerate(headers):
            if "status" in h:
                status_idx = i
                break

        compatible = False
        reason = "Unknown"

        if status_idx is not None:
            statuses = [r[status_idx].lower() for r in rows]
            if any("active" in s or "support" in s for s in statuses):
                compatible = True
                reason = "Active support found"
            elif any("end" in s or "deprecated" in s for s in statuses):
                compatible = False
                reason = "End of support"
        else:
            reason = "No status column detected"

        return {"compatible": compatible, "reason": reason}
