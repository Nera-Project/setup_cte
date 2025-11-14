# core/database_detector.py
import subprocess
import re
from utils.command import run_shell
from core.logger import get_logger

logger = get_logger(__name__)

class DatabaseDetector:

    MYSQL_BINARIES = ["mysqld", "mysql", "mariadbd"]
    POSTGRES_BINARIES = ["postgres", "psql"]

    def __init__(self):
        self.databases = []

    # ===== MySQL / MariaDB Detection =====
    def detect_mysql(self):
        results = []
        try:
            # 1. Cari semua mysqld yang berjalan
            output = run_shell("ps -eo pid,comm,args", capture_output=True)
            for line in output.splitlines():
                for bin_name in self.MYSQL_BINARIES:
                    if bin_name in line:
                        pid = line.strip().split()[0]
                        cmd = line.strip().split()[1]
                        # Cek versi
                        try:
                            version_out = run_shell(f"{cmd} --version")
                        except Exception:
                            version_out = "Unknown"
                        # Cek port dari process
                        port_out = run_shell(f"ss -ltnp | grep {pid}", capture_output=True)
                        ports = re.findall(r":(\d+)\s", port_out)
                        ports = list(set(ports)) if ports else ["Unknown"]
                        for p in ports:
                            results.append({
                                "Engine": "MYSQL",
                                "Version": version_out,
                                "Port": p,
                                "Service": cmd,
                                "Running": "Yes"
                            })
        except Exception as e:
            logger.error(f"MySQL detection failed: {e}")
        return results

    # ===== PostgreSQL Detection =====
    def detect_postgres(self):
        results = []
        try:
            output = run_shell("ps -eo pid,comm,args", capture_output=True)
            for line in output.splitlines():
                for bin_name in self.POSTGRES_BINARIES:
                    if bin_name in line:
                        pid = line.strip().split()[0]
                        cmd = line.strip().split()[1]
                        # Cek versi
                        try:
                            if "postgres" in cmd:
                                version_out = run_shell("psql --version")
                            else:
                                version_out = run_shell(f"{cmd} --version")
                        except Exception:
                            version_out = "Unknown"
                        # Cek port
                        port_out = run_shell(f"ss -ltnp | grep {pid}", capture_output=True)
                        ports = re.findall(r":(\d+)\s", port_out)
                        ports = list(set(ports)) if ports else ["Unknown"]
                        for p in ports:
                            results.append({
                                "Engine": "POSTGRESQL",
                                "Version": version_out,
                                "Port": p,
                                "Service": cmd,
                                "Running": "Yes"
                            })
        except Exception as e:
            logger.error(f"PostgreSQL detection failed: {e}")
        return results

    # ===== Detect All =====
    def detect_all(self):
        self.databases = self.detect_mysql() + self.detect_postgres()
        return self.databases

    # ===== Print Table =====
    @staticmethod
    def print_table(databases):
        if not databases:
            print("No running database instances detected.")
            return

        headers = ["Database Engine", "Version", "Port", "Service", "Running"]
        col_widths = [
            max(len(str(d[h])) for d in databases + [{h:h}]) for h in headers
        ]
        sep = "╬".join("═" * (w + 2) for w in col_widths)

        print("╔" + sep.replace("╬", "╦") + "╗")
        print("║ " + " ║ ".join(headers[i].ljust(col_widths[i]) for i in range(len(headers))) + " ║")
        print("╠" + sep.replace("╬", "╬") + "╣")
        for d in databases:
            print("║ " + " ║ ".join(str(d[h]).ljust(col_widths[i]) for i, h in enumerate(headers)) + " ║")
        print("╚" + sep.replace("╬", "╩") + "╝")
