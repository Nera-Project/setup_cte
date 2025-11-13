import argparse
import logging
from core.environment import EnvironmentManager
from core.repository import RepositoryManager

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

    # Execute logic
    if args.check:
        logger.info("Performing environment and repository compatibility check...")
        try:
            EnvironmentManager.check_system_info()
            repo = RepositoryManager()
            url = repo.fetch_active_repo_url()
            logger.info(f"Active repository URL detected: {url}")
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
