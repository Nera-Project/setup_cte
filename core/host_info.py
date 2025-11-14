# core/host_info.py

import socket
import platform
import os
import re
from utils import config
from utils.command import run_shell
from core.logger import get_logger

logger = get_logger(__name__)


class HostInfoCollector:

    # ================================================================
    # HOSTNAME
    # ================================================================
    def get_hostname(self):
        """
        Hostname harus dari /etc/hosts sesuai kebutuhan CTE.
        Ambil entri pertama bukan 127.0.0.1
        """
        try:
            with open("/etc/hosts") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    parts = line.split()
                    if len(parts) >= 2:
                        ip, name = parts[0], parts[1]
                        if ip != "127.0.0.1":
                            return name
        except Exception:
            pass

        return socket.gethostname()

    # ================================================================
    # IP ADDRESS
    # ================================================================
    def get_ip_addresses(self):
        """
        Ambil semua IP yang UP (kecuali 127.x.x.x)
        """
        try:
            output = run_shell("ip -4 addr show", capture_output=True)
            ips = re.findall(r"inet (\d+\.\d+\.\d+\.\d+)", output)
            return [ip for ip in ips if not ip.startswith("127.")]
        except Exception as e:
            logger.error(f"Failed to get IP addresses: {e}")
            return []

    def get_primary_ip(self):
        """
        Primary IP = IP pertama yang UP
        """
        ips = self.get_ip_addresses()
        return ips[0] if ips else "Unknown"

    # ================================================================
    # OS
    # ================================================================
    def get_os_details(self):
        """
        Ambil OS detail dari /etc/os-release
        """
        try:
            if os.path.exists("/etc/os-release"):
                data = {}
                with open("/etc/os-release") as f:
                    for line in f:
                        if "=" in line:
                            k, _, v = line.partition("=")
                            data[k.strip()] = v.strip().strip('"')
                return f"{data.get('NAME')} {data.get('VERSION')}"
        except Exception:
            pass

        return platform.platform()

    def get_architecture(self):
        return platform.machine()

    # ================================================================
    # LDT
    # ================================================================
    def is_ldt_applicable(self):
        """
        Kernel >= 4.x dianggap compatible.
        """
        try:
            kernel = platform.release()
            major = int(kernel.split('.')[0])
            return "Yes" if major >= 4 else "No"
        except Exception:
            return "Unknown"

    # ================================================================
    # ROOT PRIVILEGE
    # ================================================================
    def is_root(self):
        try:
            return "Yes" if os.geteuid() == 0 else "No"
        except Exception:
            return "Unknown"

    # ================================================================
    # PORT 443 CHECK (socket)
    # ================================================================
    def is_port_443_open_to_cm(self, cm_host):
        """
        Cek port 443 via socket.connect_ex
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((cm_host, 443))
            sock.close()
            return "Yes" if result == 0 else "No"
        except Exception as e:
            logger.error(f"Port check error for {cm_host}: {e}")
            return "No"

    # ================================================================
    # USER LIST
    # ================================================================
    def get_users(self):
        users = []
        try:
            with open("/etc/passwd") as f:
                for line in f:
                    users.append(line.split(":")[0])
        except Exception:
            pass
        return users

    # ================================================================
    # DATABASE DETECTION
    # ================================================================
    def detect_database(self):
        try:
            services = run_shell(
                "systemctl list-units --type=service --state=running",
                capture_output=True
            )

            # MySQL / MariaDB
            if ("mysqld.service" in services or 
                "mariadb.service" in services or 
                "mysqld" in services):
                return "MYSQL"

            # PostgreSQL
            if "postgresql" in services or "postgres.service" in services:
                return "POSTGRESQL"

            # Process check fallback
            ps = run_shell("ps aux", capture_output=True)
            if "mysqld" in ps:
                return "MYSQL"
            if "postgres" in ps:
                return "POSTGRESQL"

            return "Unknown"
        except:
            return "Unknown"

    # ================================================================
    # DATABASE VERSION
    # ================================================================
    def get_database_version(self, db_type):
        try:
            if db_type == "MYSQL":
                out = run_shell("mysql -V", capture_output=True)
                match = re.search(r"(\d+\.\d+\.\d+)", out)
                return match.group(1) if match else "Unknown"

            if db_type == "POSTGRESQL":
                out = run_shell("psql --version", capture_output=True)
                match = re.search(r"PostgreSQL\)\s+(\d+\.\d+)", out)
                if match:
                    return match.group(1)

                # fallback regex
                match = re.search(r"(\d+\.\d+)", out)
                return match.group(1) if match else "Unknown"

            return "Unknown"
        except:
            return "Unknown"

    # ================================================================
    # MASTER COLLECT FUNCTION
    # ================================================================
    def collect(self, cm_domain=config.CTVL_IP, directory_for_encryption="/data"):
        logger.info("Collecting host information...")

        db_type = self.detect_database()
        db_version = self.get_database_version(db_type)

        info = {
            "Hostname": self.get_hostname(),
            "Host IP address": self.get_primary_ip(),
            "Operating System Details": self.get_os_details(),
            "Architecture": self.get_architecture(),
            "Admin/Root access available": self.is_root(),
            "Is Port 443 Enabled between Host and CM?": self.is_port_443_open_to_cm(cm_domain),
            "User on OS": ", ".join(self.get_users()),
            "Directory path for Encryption": directory_for_encryption,
            "is LDT applicable": self.is_ldt_applicable(),
            "Database Type": db_type,
            "Database Version": db_version,
        }

        return info

    # ================================================================
    # PRINT TABLE
    # ================================================================
    @staticmethod
    def print_table(info):
        headers = ["Key", "Value"]
        rows = [{"Key": k, "Value": v} for k, v in info.items()]

        col_widths = [
            max(len(str(row[h])) for row in rows + [{h: h}]) for h in headers
        ]

        sep = "╬".join("═" * (w + 2) for w in col_widths)

        print("╔" + sep.replace("╬", "╦") + "╗")
        print("║ " + " ║ ".join(headers[i].ljust(col_widths[i]) 
                                for i in range(2)) + " ║")
        print("╠" + sep.replace("╬", "╬") + "╣")

        for r in rows:
            print("║ " + r["Key"].ljust(col_widths[0]) +
                  " ║ " + str(r["Value"]).ljust(col_widths[1]) + " ║")

        print("╚" + sep.replace("╬", "╩") + "╝")
