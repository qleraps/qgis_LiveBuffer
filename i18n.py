# -*- coding: utf-8 -*-
"""User-interface texts in English and Danish.

The language follows QGIS' own language setting (Settings > Options >
General): Danish if QGIS runs in Danish, otherwise English. QGIS only changes
language on restart, so it is decided once, the first time a text is needed.
Texts are looked up by key; a key missing in Danish falls back to English.
"""

_language = None


def _detect_language():
    try:
        from qgis.core import QgsSettings
        from qgis.PyQt.QtCore import QLocale

        settings = QgsSettings()
        if settings.value("locale/overrideFlag", False, type=bool):
            locale = str(settings.value("locale/userLocale", "") or "")
        else:
            locale = QLocale.system().name()
    except Exception:
        locale = ""
    return "da" if locale.lower().startswith("da") else "en"


def language():
    global _language
    if _language is None:
        _language = _detect_language()
    return _language


def set_language(lang):
    global _language
    _language = lang


def tr(key, *args):
    text = STRINGS.get(language(), {}).get(key)
    if text is None:
        text = STRINGS["en"].get(key, key)
    return text % args if args else text


STRINGS = {
    "en": {
        "action_text": "Draw live buffer",
        "action_status_tip": "Draw a line and create a buffer polygon around it",
        "buffer_label": " Buffer (m): ",
        "buffer_tip": "Buffer distance in metres",
        "autoselect": "Auto-select when finished",
        "autoselect_tip": "Automatically select the newly created polygon in the layer when the line is finished",
        "status_draw": "Draw a line. Enter the buffer distance.",
        "status_too_few": "Too few points for a line. Draw a line. Enter the buffer distance.",
        "edit_failed": "Could not edit the layer '%s'.",
    },
    "da": {
        "action_text": "Tegn live buffer",
        "action_status_tip": "Tegn en linje og opret en buffer-polygon omkring den",
        "buffer_label": " Buffer (m): ",
        "buffer_tip": "Bufferstørrelse i meter",
        "autoselect": "Autoselect ved afslutning",
        "autoselect_tip": "Vælg automatisk den nyoprettede polygon i laget, når linjen afsluttes",
        "status_draw": "Tegn linje. Indtast bufferstørrelse.",
        "status_too_few": "For få punkter til en linje. Tegn linje. Indtast bufferstørrelse.",
        "edit_failed": "Kunne ikke redigere laget '%s'.",
    },
}
