"""Internationalization setup."""
import gettext
import locale
import os

def setup_i18n():
    """Initialize translations for the app. Call this once at startup.

    Automatically detects system locale.
    """
    localedir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        '..',
        'translations'
    )

    # Get system locale (e.g., 'es_ES', 'en_US')
    try:
        # Initialize locale from environment
        locale.setlocale(locale.LC_ALL, '')
        lang, _ = locale.getlocale()
        if lang:
            # Extract language code (e.g., 'es' from 'es_ES')
            lang = lang.split('_')[0]
    except:
        lang = None

    # Try to load translation for detected language
    if lang:
        try:
            trans = gettext.translation('messages', localedir=localedir, languages=[lang])
            trans.install()
            return
        except FileNotFoundError:
            pass

    # Fallback: install with English
    gettext.install('messages', localedir=localedir, names=['_'])
