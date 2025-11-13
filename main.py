#!/usr/bin/env python3
"""
Entry point CLI for CTE Registration tool.
"""
import argparse
import sys
from core.logger import get_logger
from core.environment import EnvironmentManager
from core.repository import RepositoryManager
from core.compatibility_checker import CompatibilityChecker
from core.installer import Installer
from core.encrypt_asset import EncryptAssetManager
from core.issue_resolver import IssueResolver

logger = get_logger(__name__)

def build_parser():
    p = argparse.ArgumentParser(prog="cte-registration", description="CTE registration & installer tool")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="Check compatibility only")
    group.add_argument("--install", action="store_true", help="Perform full install (will check compatibility first)")
    group.add_argument("--encrypt", action="store_true", help="Apply automatic asset encryption (requires installed agent)")
    group.add_argument("--resolve", action="store_true", help="Attempt to resolve common issues")
    p.add_argument("--repo-info-url", default=None, help="(optional) override GitHub main_package.info raw URL")
    p.add_argument("--no-venv", action="store_true", help="Do not create/enter virtualenv (use system python)")
    p.add_argument("--verbose", action="store_true")
    return p

def main():
    args = build_parser().parse_args()

    if args.verbose:
        logger.setLevel("DEBUG")

    env = EnvironmentManager(use_venv=not args.no_venv)
    repo = RepositoryManager(override_url=args.repo_info_url)
    checker = CompatibilityChecker()
    installer = Installer(repo_manager=repo)
    encrypt_mgr = EncryptAssetManager()
    resolver = IssueResolver(installer=installer)

    try:
        env.ensure_environment()
        env.install_requirements()
    except Exception as e:
        logger.error("Environment preparation failed: %s", e)
        sys.exit(2)

    if args.check:
        kernel = checker.get_kernel_version()
        logger.info("Detected kernel: %s", kernel)
        compat = checker.check_kernel_support(kernel)
        if compat is None:
            logger.warning("Compatibility check could not be fully determined automatically. See message above.")
        else:
            logger.info("Compatibility table rows: %d", len(compat))
            for row in compat:
                logger.info(" - %s", row)
        return

    if args.install:
        kernel = checker.get_kernel_version()
        logger.info("Detected kernel: %s", kernel)
        compat = checker.check_kernel_support(kernel)
        if compat is None:
            logger.warning("Cannot verify compatibility automatically. Aborting install. You can re-run with --check to inspect.")
            return
        # choose download target based on OS detection inside installer
        installer.perform_install()
        return

    if args.encrypt:
        encrypt_mgr.auto_encrypt()
        return

    if args.resolve:
        resolver.auto_resolve()
        return

if __name__ == "__main__":
    main()
