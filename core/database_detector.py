# core/database_detector.py
import re
from utils.command import run_shell
from core.logger import get_logger

logger = get_logger(__name__)

class DatabaseDetector:

    MYSQL_BINARIES = ["mysqld", "mariadbd"]
    POSTGRES_BINARIES = ["postgres"]

    def __init__(self):
        self.databases = []


    # ==========================
    # SAFE run (no exception)
    # ==========================
    def safe_run(self, cmd):
        try:
            return run_shell(cmd, capture_output=True)
        except:
            return ""


    # ==========================
    # GET ALL LISTENING PORTS
    # ==========================
    def get_listening_ports(self):
        output = self.safe_run("ss -ltnp 2>/dev/null")
        results = []

        for line in output.splitlines():
            m = re.search(
                r"LISTEN\s+\d+\s+\d+\s+.*:(\d+)\s+.*pid=(\d+),fd=\d+\)",
                line
            )
            if m:
                port, pid = m.groups()
                results.append({"port": port, "pid": pid, "raw": line})

        return results


    # ==========================
    # Detect MySQL / MariaDB
    # ==========================
    def detect_mysql(self, processes, ports):
        db_list = []

        for p in processes:
            pid = p["pid"]
            name = p["cmd"]

            if name not in self.MYSQL_BINARIES:
                continue

            # Find ports for this PID
            matching_ports = [x["port"] for x in ports if x["pid"] == pid]
            if not matching_ports:
                matching_ports = ["Unknown"]

            version = self.safe_run(f"{name} --version").strip() or "Unknown"

            db_list.append({
                "Database Engine": "MYSQL",
                "Version": version,
                "Port": ", ".join(matching_ports),
                "Service": name,
                "Running": "Yes"
            })

        return db_list


    # ==========================
    # Detect PostgreSQL (FIXED)
    # ==========================
    def detect_postgres(self, processes, ports):
        db_list = []

        # all postgres pids
        postgres_pids = {p["pid"] for p in processes if p["cmd"] == "postgres"}

        if not postgres_pids:
            return []

        # only postgres with ports
        postgres_with_ports = [p for p in ports if p["pid"] in postgres_pids]

        if not postgres_with_ports:
            # no port, still show postgres but with Unknown port
            main_pid = list(postgres_pids)[0]
            ports_list = ["Unknown"]
        else:
            # choose the main PID (usually master)
            main_pid = postgres_with_ports[0]["pid"]
            ports_list = [p["port"] for p in postgres_with_ports if p["pid"] == main_pid]

        version = self.safe_run("psql --version").strip() or "Unknown"

        db_list.append({
            "Database Engine": "POSTGRESQL",
            "Version": version,
            "Port": ", ".join(ports_list),
            "Service": "postgres",
            "Running": "Yes"
        })

        return db_list


    # ==========================
    # Detect All DB
    # ==========================
    def detect_all(self):
        # Get running processes
        ps_out = self.safe_run("ps -eo pid,comm")
        processes = []

        for line in ps_out.splitlines()[1:]:
            parts = line.strip().split()
            if len(parts) < 2:
                continue
            processes.append({
                "pid": parts[0],
                "cmd": parts[1]
            })

        # Get ports
        ports = self.get_listening_ports()

        # Detect DBs
        result = []
        result.extend(self.detect_mysql(processes, ports))
        result.extend(self.detect_postgres(processes, ports))

        self.databases = result
        return result


    # ==========================
    # Print Table
    # ==========================
    @staticmethod
    def print_table(databases):
        if not databases:
            print("\nNo running database instances detected.\n")
            return

        headers = ["Database Engine", "Version", "Port", "Service", "Running"]

        col_widths = [
            max(len(str(row[h])) for row in databases + [{h: h}])
            for h in headers
        ]

        sep = "╬".join("═" * (w + 2) for w in col_widths)

        print("╔" + sep.replace("╬", "╦") + "╗")
        print("║ " + " ║ ".join(headers[i].ljust(col_widths[i]) for i in range(len(headers))) + " ║")
        print("╠" + sep.replace("╬", "╬") + "╣")

        for row in databases:
            print("║ " + " ║ ".join(
                str(row[h]).ljust(col_widths[i])
                for i, h in enumerate(headers)
            ) + " ║")

        print("╚" + sep.replace("╬", "╩") + "╝")
