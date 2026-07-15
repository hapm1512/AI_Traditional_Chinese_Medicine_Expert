import logging
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from tcm_expert.core.config import AppSettings
from tcm_expert.core.logging_config import configure_logging
from tcm_expert.core.paths import AppPaths
from tcm_expert.database.manager import DatabaseManager
from tcm_expert.ui.main_window import MainWindow
from tcm_expert.ui.theme import DARK_THEME


def main() -> int:
    paths = AppPaths.discover()
    paths.ensure()
    configure_logging(paths.logs)
    app = QApplication(sys.argv)
    app.setApplicationName("AI Traditional Chinese Medicine Expert")
    app.setOrganizationName("Hai Pham")
    try:
        settings = AppSettings.load(paths.settings)
        database = DatabaseManager(paths.database)
        database.initialize()
        if not database.health_check():
            raise RuntimeError("Không thể kết nối cơ sở dữ liệu")
        app.setStyleSheet(DARK_THEME)
        window = MainWindow(settings.clinic_name, database, database.reference_counts())
        window.show()
        return app.exec()
    except Exception as error:  # GUI boundary logs unexpected failures.
        logging.exception("Application startup failed")
        QMessageBox.critical(None, "Lỗi khởi động", str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
