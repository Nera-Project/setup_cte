# core/host_info.py

import socket
import platform
import os
import re
import subprocess
from utils.command import run_shell
from core.logger import get_logger

logger = get_logger(__name__)

class HostInfoCollector:

    def get_hostname(self):
        try:
            return socket.gethostname()
        except:
            return "Unknown"

    def get_ip_addresses(self):
        """
        Ambil semua IP yang UP.
        Tidak termasuk 127.x.x.x
        """
        try:
            output = run_shell("ip -4 addr show", capture_output=True)
            ips = re.findall(r"inet (\d+\.\d+\.\d+\.\d+)", output)
            return [ip for ip in ips if not ip.startswith("127.")]
        except Exception as e:
            logger.error(f"Failed to get IP addresses: {e}")
            return []

    def get_os_details(self):
        """
        Ambil distro + version dari /etc/os-release
        """
        try:
            if os.path.exists("/etc/os-release"):
                data = {}
                with open("/etc/os-release") as f:
                    for line in f:
                        k, _, v = line.partition("=")
                        data[k.strip()] = v.strip().strip('"')
                pretty = f"{data.get('NAME')} {data.get('VERSION')}"
                return pretty
        except:
            pass
        return platform.platform()

    def get_architecture(self):
        return platform.machine()

    def is_ldt_applicable(self):
        """
        Sementara simple rule:
        - Kernel >= 4.x biasanya support LDT secara default.
        """
        kernel = platform.release()
        major = int(kernel.split('.')[0])
        return "Yes" if major >= 4 else "Maybe"

    def is_root(self):
        return "Yes" if os.geteuid() == 0 else "No"

    def is_port_443_open_to_cm(self, cm_domain):
        """
        Test TCP ke CM domain:443 menggunakan bash.
        """
        cmd = f"timeout 3 bash -c '</dev/tcp/{cm_domain}/443' 2>/dev/null && echo OK || echo FAIL'"
        result = run_shell(cmd, capture_output=True)
        return "Yes" if result == "OK" else "No"

    def get_users(self):
        """
        Ambil user dari /etc/passwd (system + normal).
        """
        users = []
        try:
            with open("/etc/passwd") as f:
                for line in f:
                    name = line.split(":")[0]
                    users.append(name)
        except:
            pass
        return users

    def collect(self, cm_domain="example.com"):
        """
        Collect seluruh informasi host.
        """
        logger.info("Collecting host information...")

        info = {
            "Hostname": self.get_hostname(),
            "IP Addresses": ", ".join(self.get_ip_addresses()),
            "Operating System": self.get_os_details(),
            "Architecture": self.get_architecture(),
            "LDT Applicable": self.is_ldt_applicable(),
            "Is Root": self.is_root(),
            "Port 443 to CM": self.is_port_443_open_to_cm(cm_domain),
            "OS Users": ", ".join(self.get_users()),
        }

        return info

    @staticmethod
    def print_table(info):
        """
        Print tabel seperti compatibility checker.
        """
        headers = ["Key", "Value"]
        rows = [{"Key": k, "Value": v} for k, v in info.items()]

        col_widths = [
            max(len(row[h]) for row in rows + [{h: h}]) for h in headers
        ]

        sep = "╬".join("═" * (w + 2) for w in col_widths)

        print("╔" + sep.replace("╬", "╦") + "╗")
        print("║ " + " ║ ".join(headers[i].ljust(col_widths[i]) for i in range(2)) + " ║")
        print("╠" + sep.replace("╬", "╬") + "╣")
        for r in rows:
            print("║ " + r["Key"].ljust(col_widths[0]) + " ║ " + r["Value"].ljust(col_widths[1]) + " ║")
        print("╚" + sep.replace("╬", "╩") + "╝")
