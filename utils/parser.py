# utils/parser.py
from bs4 import BeautifulSoup
from core.logger import get_logger

logger = get_logger(__name__)

def parse_portal_table(html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    table = soup.find("table", class_="portal-table")
    if not table:
        logger.debug("No portal-table found in HTML.")
        return None
    rows = []
    for tr in table.find_all("tr"):
        cols = [td.get_text(strip=True) for td in tr.find_all(["th", "td"])]
        if cols:
            rows.append(cols)
    return rows
