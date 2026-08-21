from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from nightscout_widget.constants import APP_DISPLAY_NAME
from nightscout_widget.logging_setup import configure_logging
from nightscout_widget.os_integration.factory import create_desktop_integration
from nightscout_widget.paths import AppPaths


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_DISPLAY_NAME)
    parser.add_argument(
        "--config-dir",
        type=Path,
        help="Nadpisuje katalog config/state/logs (przydatne do testów i trybu portable).",
    )
    parser.add_argument(
        "--print-config-dir",
        action="store_true",
        help="Wypisuje katalog konfiguracji i kończy działanie.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.config_dir:
        os.environ["NIGHTSCOUT_WIDGET_HOME"] = str(args.config_dir.expanduser().resolve())

    paths = AppPaths.discover()
    paths.ensure()

    if args.print_config_dir:
        print(paths.config_dir)
        return 0

    configure_logging(paths.log_dir)
    logger = logging.getLogger(__name__)
    logger.info("Uruchamianie %s", APP_DISPLAY_NAME)

    integration = create_desktop_integration()
    integration.prepare_process()

    from PySide6.QtCore import QLockFile
    from PySide6.QtWidgets import QApplication, QMessageBox

    from nightscout_widget.app import NightscoutWidgetController
    from nightscout_widget.ui.icons import tray_icon

    application = QApplication(sys.argv[:1])
    application.setApplicationName(APP_DISPLAY_NAME)
    application.setOrganizationName("NightscoutWidget")
    application.setQuitOnLastWindowClosed(False)
    application.setWindowIcon(tray_icon())

    instance_lock = QLockFile(str(paths.config_dir / "instance.lock"))
    if not instance_lock.tryLock(250):
        QMessageBox.information(
            None,
            APP_DISPLAY_NAME,
            "Nightscout Widget jest już uruchomiony.",
        )
        return 0

    controller = NightscoutWidgetController(application, paths, integration)
    # Keep both objects alive for the entire event loop.
    application._nightscout_controller = controller  # type: ignore[attr-defined]
    application._nightscout_instance_lock = instance_lock  # type: ignore[attr-defined]
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
