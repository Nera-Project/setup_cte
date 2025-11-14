import re
import os
from utils.command import run_shell
from core.logger import get_logger

logger = get_logger(__name__)


class DatabaseDetector:

    MYSQL_BINARIES = ["mysqld"]
    MARIADB_BINARIES = ["mariadbd"]
    POSTGRES_BINARIES = ["postgres"]
    ORACLE_BINARIES = ["tnslsnr"]
    MONGODB_BINARIES = ["mongod"]
    REDIS_BINARIES = ["redis-server"]
    MSSQL_BINARIES = ["sqlservr"]

    def __init__(self):
        self.databases = []

    # =====================================================
    # Safe shell runner
    # =====================================================
    def safe_run(self, cmd):
        try:
            return run_shell(cmd, capture_output=True).strip()
        except:
            return ""

    # =====================================================
    # PORT LISTENING
    # =====================================================
    def get_listening_ports(self):
        output = self.safe_run("ss -ltnp 2>/dev/null")
        results = []

        for line in output.splitlines():
            m = re.search(r"LISTEN\s+\d+\s+\d+\s+.*:(\d+)\s+.*pid=(\d+)", line)
            if m:
                port, pid = m.groups()
                results.append({"port": port, "pid": pid})

        return results

    # =====================================================
    # DETECT STARTUP METHOD
    # =====================================================
    def detect_startup_method(self, service_hint, pid):
        # Try systemd service names
        if service_hint:
            svc = self.safe_run(f"systemctl is-active {service_hint}")
            if "active" in svc:
                return "systemd"

        # Try generic
        svc_list = self.safe_run("systemctl list-units --type=service --no-pager")
        if "postgres" in svc_list:
            return "systemd"

        # init.d
        if os.path.exists(f"/etc/init.d/{service_hint}"):
            return "init-script"

        # container?
        cg = self.safe_run(f"cat /proc/{pid}/cgroup")
        if any(x in cg for x in ["docker", "containerd", "kubepods"]):
            return "docker"

        # fallback
        return "manual"

    # =====================================================
    # HELPER FOR ADDING RESULT WITHOUT DUPLICATE
    # =====================================================
    def add_db_unique(self, db_list, new_item):
        signature = f"{new_item['Database Engine']}|{new_item['Port']}"

        for item in db_list:
            sig2 = f"{item['Database Engine']}|{item['Port']}"
            if sig2 == signature:
                return  # skip duplicate

        db_list.append(new_item)

    # =====================================================
    # MYSQL
    # =====================================================
    def detect_mysql(self, processes, ports):
        db_list = []

        for p in processes:
            pid, cmd = p["pid"], p["cmd"]

            if cmd not in self.MYSQL_BINARIES:
                continue

            matched_ports = [x["port"] for x in ports if x["pid"] == pid] or ["Unknown"]
            version = self.safe_run("mysqld --version") or "Unknown"

            startup = self.detect_startup_method("mysqld", pid)

            self.add_db_unique(db_list, {
                "Database Engine": "MYSQL",
                "Version": version,
                "Port": ", ".join(matched_ports),
                "Service": cmd,
                "Running": "Yes",
                "Startup Method": startup
            })

        return db_list

    # =====================================================
    # MARIADB
    # =====================================================
    def detect_mariadb(self, processes, ports):
        db_list = []

        for p in processes:
            pid, cmd = p["pid"], p["cmd"]

            if cmd not in self.MARIADB_BINARIES:
                continue

            matched_ports = [x["port"] for x in ports if x["pid"] == pid] or ["Unknown"]
            version = self.safe_run("mariadbd --version") or "Unknown"

            startup = self.detect_startup_method("mariadb", pid)

            self.add_db_unique(db_list, {
                "Database Engine": "MARIADB",
                "Version": version,
                "Port": ", ".join(matched_ports),
                "Service": cmd,
                "Running": "Yes",
                "Startup Method": startup
            })

        return db_list

    # =====================================================
    # POSTGRESQL
    # =====================================================
    def detect_postgres(self, processes, ports):
        db_list = []

        # avoid multiple postmaster forks showing as instances
        seen_pids = set()

        for p in processes:
            pid, cmd = p["pid"], p["cmd"]

            if cmd not in self.POSTGRES_BINARIES:
                continue
            if pid in seen_pids:
                continue

            seen_pids.add(pid)

            matched_ports = [x["port"] for x in ports if x["pid"] == pid] or ["5432"]
            version = self.safe_run("psql --version") or "Unknown"

            startup = self.detect_startup_method("postgresql", pid)

            self.add_db_unique(db_list, {
                "Database Engine": "POSTGRESQL",
                "Version": version,
                "Port": ", ".join(matched_ports),
                "Service": cmd,
                "Running": "Yes",
                "Startup Method": startup
            })

        return db_list

    # =====================================================
    # ORACLE DB
    # =====================================================
    def detect_oracle(self, processes, ports):
        db_list = []

        for p in processes:
            pid, cmd = p["pid"], p["cmd"]

            if cmd not in self.ORACLE_BINARIES:
                continue

            matched_ports = [x["port"] for x in ports if x["pid"] == pid] or ["1521"]

            version = self.safe_run("sqlplus -v") or "Unknown"

            startup = self.detect_startup_method("oracle", pid)

            self.add_db_unique(db_list, {
                "Database Engine": "ORACLE",
                "Version": version,
                "Port": ", ".join(matched_ports),
                "Service": cmd,
                "Running": "Yes",
                "Startup Method": startup
            })

        return db_list

    # =====================================================
    # MONGODB
    # =====================================================
    def detect_mongodb(self, processes, ports):
        db_list = []

        for p in processes:
            pid, cmd = p["pid"], p["cmd"]

            if cmd not in self.MONGODB_BINARIES:
                continue

            matched_ports = [x["port"] for x in ports if x["pid"] == pid] or ["27017"]
            version = self.safe_run("mongod --version | head -n 1") or "Unknown"

            startup = self.detect_startup_method("mongod", pid)

            self.add_db_unique(db_list, {
                "Database Engine": "MONGODB",
                "Version": version,
                "Port": ", ".join(matched_ports),
                "Service": cmd,
                "Running": "Yes",
                "Startup Method": startup
            })

        return db_list

    # =====================================================
    # REDIS
    # =====================================================
    def detect_redis(self, processes, ports):
        db_list = []

        for p in processes:
            pid, cmd = p["pid"], p["cmd"]

            if cmd not in self.REDIS_BINARIES:
                continue

            matched_ports = [x["port"] for x in ports if x["pid"] == pid] or ["6379"]
            version = self.safe_run("redis-server --version") or "Unknown"

            startup = self.detect_startup_method("redis", pid)

            self.add_db_unique(db_list, {
                "Database Engine": "REDIS",
                "Version": version,
                "Port": ", ".join(matched_ports),
                "Service": cmd,
                "Running": "Yes",
                "Startup Method": startup
            })

        return db_list

    # =====================================================
    # MSSQL
    # =====================================================
    def detect_mssql(self, processes, ports):
        db_list = []

        for p in processes:
            pid, cmd = p["pid"], p["cmd"]

            if cmd not in self.MSSQL_BINARIES:
                continue

            matched_ports = [x["port"] for x in ports if x["pid"] == pid] or ["1433"]
            version = self.safe_run("/opt/mssql/bin/sqlservr --version 2>/dev/null") or "Unknown"

            startup = self.detect_startup_method("mssql-server", pid)

            self.add_db_unique(db_list, {
                "Database Engine": "MSSQL",
                "Version": version,
                "Port": ", ".join(matched_ports),
                "Service": cmd,
                "Running": "Yes",
                "Startup Method": startup
            })

        return db_list

    # =====================================================
    # DETECT ALL DATABASES
    # =====================================================
    def detect_all(self):
        ps_out = self.safe_run("ps -eo pid,comm")
        processes = []

        for line in ps_out.splitlines()[1:]:
            parts = line.strip().split()
            if len(parts) >= 2:
                processes.append({"pid": parts[0], "cmd": parts[1]})

        ports = self.get_listening_ports()
        result = []

        result += self.detect_mysql(processes, ports)
        result += self.detect_mariadb(processes, ports)
        result += self.detect_postgres(processes, ports)
        result += self.detect_oracle(processes, ports)
        result += self.detect_mongodb(processes, ports)
        result += self.detect_redis(processes, ports)
        result += self.detect_mssql(processes, ports)

        self.databases = result
        return result

    # =====================================================
    # PRINT TABLE
    # =====================================================
    @staticmethod
    def print_table(databases):
        if not databases:
            print("\nNo running database instances detected.\n")
            return

        headers = ["Database Engine", "Version", "Port", "Service", "Running", "Startup Method"]

        # calc column widths
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
