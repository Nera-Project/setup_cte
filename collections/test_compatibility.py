import requests
import json
import pdfplumber
import re
import pdfplumber
import warnings
warnings.filterwarnings("ignore", message="Could get FontBBox")

import logging
logging.getLogger("pdfminer").setLevel(logging.ERROR)


# =============================
# 1️⃣ Ambil JSON Compatibility Matrix dari URL
# =============================
def fetch_cte_compatibility():
    url = "https://packages.vormetric.com/pub/cte_compatibility_matrix.json"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data

# =============================
# 2️⃣ Parse PDF "CTE Release Support Status"
# =============================
def parse_cte_support_status(pdf_path):
    """
    Membaca file PDF yang berisi tabel 'CTE Release Support Status'
    dan mengembalikan dict: { '7.8.0': 'Active', ... }
    """

    results = {}
    pattern = re.compile(r"^(\d+\.\d+\.\d+)\s+[\dA-Za-z-]+\s+([A-Za-z\s]+)$")

    with pdfplumber.open(pdf_path) as pdf:
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

# =============================
# 3️⃣ Cek kompatibilitas berdasarkan kernel + tambahkan status dari PDF
# =============================
def check_kernel_compatibility_with_support(kernel_version, pdf_path):
    """
    Mengecek kernel di matrix JSON, dan gabungkan hasil dengan support status dari PDF
    """
    data = fetch_cte_compatibility()
    support_data = parse_cte_support_status(pdf_path)

    results = []
    for os_entry in data["MAPPING"]:
        for k in os_entry["KERNEL"]:
            if kernel_version in k["NUM"]:
                status = "Active" if k["END"] == "0" else f"Supported until {k['END']}"
                
                # ambil status support dari PDF berdasarkan versi START (misal 7.8.0)
                cte_version_base = '.'.join(k["START"].split('.')[:3])
                support_status = support_data.get(cte_version_base, "Unknown")

                results.append({
                    "OS": os_entry["OS"],
                    "Kernel": k["NUM"],
                    "CTE Start": k["START"],
                    "CTE End": k["END"],
                    "Compatibility": status,
                    "Support Status": support_status
                })
    return results

# =============================
# 4️⃣ Contoh penggunaan
# =============================
if __name__ == "__main__":
    kernel = "4.18.0-372.41.1.el8_6.x86_64"
    pdf_path = "./data/cte_release_status.pdf"  # ubah path sesuai lokasi PDF kamu

    compatible = check_kernel_compatibility_with_support(kernel, pdf_path)
    if compatible:
        for entry in compatible:
            print(
                f"OS: {entry['OS']} | "
                f"CTE: {entry['CTE Start']} - {entry['CTE End']} | "
                f"Compatibility: {entry['Compatibility']} | "
                f"Support Status: {entry['Support Status']}"
            )
    else:
        print("Kernel tidak ditemukan di matrix.")
