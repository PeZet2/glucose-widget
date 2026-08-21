from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from glucose_widget.constants import APP_DISPLAY_NAME
from glucose_widget.logging_setup import configure_logging
from glucose_widget.os_integration.factory import create_desktop_integration
from glucose_widget.paths import AppPaths


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_DISPLAY_NAME)
    parser.add_argument(
        "--config-dir",
        type=Path,
        help="Overrides the config/state/logs directory (useful for tests and portable mode).",
    )
    parser.add_argument(
        "--print-config-dir",
        action="store_true",
        help="Prints the configuration directory and exits.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.config_dir:
        os.environ["GLUCOSE_WIDGET_HOME"] = str(args.config_dir.expanduser().resolve())

    paths = AppPaths.discover()
    paths.ensure()

    if args.print_config_dir:
        print(paths.config_dir)
        return 0

    configure_logging(paths.log_dir)
    logger = logging.getLogger(__name__)
    logger.info("Starting %s", APP_DISPLAY_NAME)

    integration = create_desktop_integration()
    integration.prepare_process()

    from PySide6.QtCore import QLockFile
    from PySide6.QtWidgets import QApplication, QMessageBox

    from glucose_widget.app import GlucoseWidgetController
    from glucose_widget.ui.icons import tray_icon

    application = QApplication(sys.argv[:1])
    application.setApplicationName(APP_DISPLAY_NAME)
    application.setOrganizationName("GlucoseWidget")
    application.setQuitOnLastWindowClosed(False)
    application.setWindowIcon(tray_icon())

    instance_lock = QLockFile(str(paths.config_dir / "instance.lock"))
    if not instance_lock.tryLock(250):
        QMessageBox.information(
            None,
            APP_DISPLAY_NAME,
            "Glucose Widget is already running.",
        )
        return 0

    controller = GlucoseWidgetController(application, paths, integration)
    # Keep both objects alive for the entire event loop.
    application._nightscout_controller = controller  # type: ignore[attr-defined]
    application._nightscout_instance_lock = instance_lock  # type: ignore[attr-defined]
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
