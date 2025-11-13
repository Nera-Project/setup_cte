import argparse
import logging
from core.environment import EnvironmentManager
from core.repository import RepositoryManager
from core.compatibility_checker import CompatibilityChecker  # ✅ NEW import

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Thales CTE Setup & Integration Tool")
    parser.add_argument("--check", action="store_true", help="Check environment and compatibility")
    parser.add_argument("--install", action="store_true", help="Install Thales CTE Agent")
    parser.add_argument("--encrypt", action="store_true", help="Encrypt asset folder")
    parser.add_argument("--fix", action="store_true", help="Resolve common issues automatically")

    args = parser.parse_args()

    # Validate we are inside venv (setup.sh handles env creation)
    EnvironmentManager.validate_virtualenv()

    # ========================
    # MAIN EXECUTION LOGIC
    # ========================
    if args.check:
        logger.info("Performing environment and repository compatibility check...")
        try:
            # ✅ 1. Check environment
            EnvironmentManager.check_system_info()

            # ✅ 2. Fetch repository info
            repo = RepositoryManager()
            url = repo.fetch_active_repo_url()
            logger.info(f"Active repository URL detected: {url}")

            # ✅ 3. Compatibility check (new feature)
            compat = CompatibilityChecker()
            kernel_version = compat.get_kernel_version()
            logger.info(f"Detected kernel version: {kernel_version}")

            table = compat.check_kernel_support(kernel_version)
            if table:
                compat.print_table(table)
                summary = compat.summarize_compatibility(table)
                if summary["compatible"]:
                    logger.info(f"✅ This system is compatible with Thales CTE: {summary['reason']}")
                else:
                    logger.warning(f"⚠️  This system might NOT be fully compatible: {summary['reason']}")
            else:
                logger.warning("Could not determine Thales CTE compatibility automatically.")

            logger.info("Environment check completed successfully.")

        except Exception as e:
            logger.error(f"Error during environment check: {e}")
            exit(1)

    elif args.install:
        logger.info("CTE Agent installation process started...")
        # TODO: add integration logic
        logger.info("Installation feature not implemented yet.")

    elif args.encrypt:
        logger.info("Starting folder encryption process...")
        # TODO: encryption automation
        logger.info("Encryption feature not implemented yet.")

    elif args.fix:
        logger.info("Auto fixing common issues...")
        # TODO: add automatic repair logic
        logger.info("Fixing feature not implemented yet.")

    else:
        parser.print_help()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        exit(1)
