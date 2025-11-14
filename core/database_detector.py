# core/database_detector.py
import re
import os
from utils.command import run_shell
from core.logger import get_logger

logger = get_logger(__name__)


class DatabaseDetector:

    MYSQL_BINARIES = ["mysqld", "mariadbd"]
    POSTGRES_BINARIES = ["postgres"]

    def __init__(self):
        self.databases = []

    def safe_run(self, cmd):
        try:
            return run_shell(cmd, capture_output=True)
        except:
            return ""

    # ==========================
    # PORT LISTENING
    # ==========================
    def get_listening_ports(self):
        output = self.safe_run("ss -ltnp 2>/dev/null")
        results = []

        for line in output.splitlines():
            m = re.search(r"LISTEN\s+\d+\s+\d+\s+.*:(\d+)\s+.*pid=(\d+)", line)
            if m:
                port, pid = m.groups()
                results.append({"port": port, "pid": pid})

        return results

    # ==========================
    # SERVICE / STARTUP DETECTOR
    # ==========================
    def detect_startup_method(self, service_name, pid):
        # Check systemd
        svc = self.safe_run(f"systemctl is-active {service_name}")
        if "active" in svc:
            return "systemd"

        # Postgres sometimes uses postgresql-XX
        if "postgres" in service_name:
            pg_services = self.safe_run("systemctl list-units --type=service --no-pager | grep postgres")
            if pg_services:
                return "systemd"

        # Check init.d
        if os.path.exists(f"/etc/init.d/{service_name}"):
            return "init-script"

        # Check docker
        cgroup = self.safe_run(f"cat /proc/{pid}/cgroup")
        if "docker" in cgroup or "containerd" in cgroup:
            return "docker"

        # Default fallback = manual startup
        return "manual"

    # ==========================
    # MySQL Detection
    # ==========================
    def detect_mysql(self, processes, ports):
        db_list = []

        for p in processes:
            pid = p["pid"]
            name = p["cmd"]

            if name not in self.MYSQL_BINARIES:
                continue

            matching_ports = [x["port"] for x in ports if x["pid"] == pid] or ["Unknown"]
            version = self.safe_run(f"{name} --version") or "Unknown"

            startup = self.detect_startup_method("mysqld", pid)

            db_list.append({
                "Database Engine": "MYSQL",
                "Version": version.strip(),
                "Port": ", ".join(matching_ports),
                "Service": name,
                "Running": "Yes",
                "Startup Method": startup
            })

        return db_list

    # ==========================
    # PostgreSQL Detection
    # ==========================
    def detect_postgres(self, processes, ports):
        db_list = []

        for p in processes:
            pid = p["pid"]
            name = p["cmd"]

            if name not in self.POSTGRES_BINARIES:
                continue

            matching_ports = [x["port"] for x in ports if x["pid"] == pid] or ["Unknown"]
            version = self.safe_run("psql --version") or "Unknown"

            startup = self.detect_startup_method("postgresql", pid)

            db_list.append({
                "Database Engine": "POSTGRESQL",
                "Version": version.strip(),
                "Port": ", ".join(matching_ports),
                "Service": name,
                "Running": "Yes",
                "Startup Method": startup
            })

        return db_list

    # ==========================
    # DETECT ALL
    # ==========================
    def detect_all(self):
        ps_out = self.safe_run("ps -eo pid,comm")
        processes = []

        for line in ps_out.splitlines()[1:]:
            parts = line.strip().split()
            if len(parts) >= 2:
                processes.append({"pid": parts[0], "cmd": parts[1]})

        ports = self.get_listening_ports()
        result = []

        result.extend(self.detect_mysql(processes, ports))
        result.extend(self.detect_postgres(processes, ports))

        self.databases = result
        return result

    # ==========================
    # TABLE OUTPUT
    # ==========================
    @staticmethod
    def print_table(databases):
        if not databases:
            print("\nNo running database instances detected.\n")
            return

        headers = ["Database Engine", "Version", "Port", "Service", "Running", "Startup Method"]

        col_widths = [
            max(len(str(row.get(h, ""))) for row in databases + [{h: h}])
            for h in headers
        ]

        sep = "╬".join("═" * (w + 2) for w in col_widths)

        print("╔" + sep.replace("╬", "╦") + "╗")
        print("║ " + " ║ ".join(headers[i].ljust(col_widths[i]) for i in range(len(headers))) + " ║")
        print("╠" + sep.replace("╬", "╬") + "╣")

        for row in databases:
            print("║ " + " ║ ".join(str(row.get(h, "")).ljust(col_widths[i])
                for i, h in enumerate(headers)) + " ║")

        print("╚" + sep.replace("╬", "╩") + "╝")
