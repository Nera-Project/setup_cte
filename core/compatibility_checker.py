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
        # Build query URL (same format you provided)
        qurl = f"{self.base_url}?sideBarIndex=0&radioOption=KERNEL&search={kernel_version}"
        logger.info("Querying Thales compatibility matrix: %s", qurl)
        try:
            resp = requests.get(qurl, timeout=15)
        except Exception as e:
            logger.error("Failed to request Thales portal: %s", e)
            return None

        text = resp.text
        # Quick detect for SPA angular placeholder
        if "<app-root" in text or "runtime.js" in text or "main.js" in text:
            logger.warning("Thales portal appears to be a dynamic SPA (Angular). Cannot scrape table reliably.")
            logger.info("Please open the following URL in a browser for manual verification: %s", qurl)
            return None

        table = parse_portal_table(text)
        if not table:
            logger.warning("No compatibility table parsed from Thales portal response.")
            return None

        # return parsed table rows (list of lists)
        return table
