"""
Suporte a internacionalização (i18n) da GUI.

Como gerar traduções:
1. Instale as ferramentas Qt: pip install pyside6-tools
2. Crie um arquivo .ts: pylupdate6 src/gui -ts src/gui/i18n/pt_BR.ts
3. Edite o arquivo .ts com Qt Linguist
4. Compile para .qm: lrelease src/gui/i18n/pt_BR.ts
5. Coloque o .qm em ~/.alakoro/i18n/alakoro_pt_BR.qm
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtWidgets import QApplication


LOCALE_DIR = Path.home() / ".alakoro" / "i18n"


def install_translators(app: QApplication) -> list[QTranslator]:
    """
    Instala tradutores Qt baseados no locale do sistema.

    Retorna a lista de tradutores instalados para referência.
    """
    translators: list[QTranslator] = []
    locale = QLocale.system().name()  # ex: "pt_BR", "en_US"

    # Traduções do próprio Alakoro
    qm_path = LOCALE_DIR / f"alakoro_{locale}.qm"
    if qm_path.exists():
        translator = QTranslator()
        if translator.load(str(qm_path)):
            app.installTranslator(translator)
            translators.append(translator)

    # Traduções padrão do Qt
    qt_translations = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    qt_translator = QTranslator()
    if qt_translator.load(f"qt_{locale}", qt_translations):
        app.installTranslator(qt_translator)
        translators.append(qt_translator)
    elif qt_translator.load(f"qtbase_{locale}", qt_translations):
        app.installTranslator(qt_translator)
        translators.append(qt_translator)

    return translators
