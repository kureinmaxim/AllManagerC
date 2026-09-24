"""Request-local UI translations. Catalogs contain UI text, never vault data."""
import json
from pathlib import Path
from urllib.parse import urlsplit

from flask import abort, current_app, has_request_context, redirect, request, url_for

LANGUAGES = {'ru': 'Русский', 'en': 'English', 'zh': '简体中文'}
COOKIE = 'allmanagerc_language'


def get_locale():
    language = request.cookies.get(COOKIE, 'ru') if has_request_context() else 'ru'
    return language if language in LANGUAGES else 'ru'


def gettext(message, **values):
    translated = message
    if has_request_context():
        translated = current_app.extensions['translations'].get(get_locale(), {}).get(message, message)
    return translated % values if values else translated


def init_localization(app):
    directory = Path(app.root_path) / 'translations'
    if not directory.is_dir() and getattr(__import__('sys'), 'frozen', False):
        directory = Path(getattr(__import__('sys'), '_MEIPASS', app.root_path)) / 'translations'
    app.extensions['translations'] = {
        language: (json.loads((directory / f'{language}.json').read_text(encoding='utf-8'))
                   if (directory / f'{language}.json').is_file() else {})
        for language in ('en', 'zh')
    }
    app.jinja_env.globals['_'] = gettext

    @app.context_processor
    def language_context():
        return {'current_locale': get_locale(), 'ui_languages': LANGUAGES}

    @app.get('/language/<language>')
    def change_language(language):
        if language not in LANGUAGES:
            abort(404)
        target = request.args.get('next', '/')
        parsed = urlsplit(target)
        # Only relative paths on this app; no Referer-based external redirects.
        if (parsed.scheme or parsed.netloc or not target.startswith('/')
                or target.startswith('//') or '\\' in target
                or any(ord(char) < 32 for char in target)):
            target = url_for('index')
        response = redirect(target)
        response.set_cookie(COOKIE, language, max_age=365 * 24 * 60 * 60,
                            httponly=True, samesite='Lax', secure=request.is_secure)
        return response
