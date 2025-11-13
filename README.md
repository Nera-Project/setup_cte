CTE Registration Tool - README

Usage:
    python3 main.py --check
    python3 main.py --install
    python3 main.py --encrypt
    python3 main.py --resolve

Steps to prepare:
1. Ensure python3 installed (>=3.8 recommended).
2. Place repo info file URL into utils/config.py or pass --repo-info-url.
3. Run: python3 main.py --check

Notes:
- Some actions require root.
- Installer expects repository to expose binary under /cte/bin/<distro>/latest/
- Adjust installer flags to match actual .bin installer options.
