import re
import requests
from core.logger import get_logger
from utils import config
from utils.exceptions import RepositoryError

logger = get_logger(__name__)

class RepositoryManager:
    def __init__(self, override_url=None):
        self.info_url = override_url or config.GITHUB_RAW_MAIN

    def fetch_active_repo_url(self):
        logger.info("Fetching repository info from %s", self.info_url)
        resp = requests.get(self.info_url, timeout=10)
        resp.raise_for_status()
        text = resp.text
        # try to find trycloudflare domain (common in your setup)
        m = re.search(config.DEFAULT_CLOUDFLARE_DOMAIN_PATTERN, text)
        if m:
            url = m.group(0)
            logger.info("Found active repo URL: %s", url)
            return url.rstrip("/")
        # fallback: try first http(s) link
        m2 = re.search(r"https?:\/\/[^\s'\"<>]+", text)
        if m2:
            url = m2.group(0)
            logger.info("Found fallback URL: %s", url)
            return url.rstrip("/")
        raise RepositoryError("Active repository URL not found in info file.")
