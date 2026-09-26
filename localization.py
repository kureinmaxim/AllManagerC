"""Request-local UI translations. Catalogs contain UI text, never vault data."""
import json
from pathlib import Path
from urllib.parse import urlsplit

from flask import abort, current_app, has_request_context, jsonify, redirect, request, url_for

from ui_preferences import (
    ALLOWED_LANGUAGES,
    ALLOWED_ZOOMS,
    DEFAULT_LANGUAGE,
    load_ui_preferences,
    normalize_language,
    save_ui_preferences,
)

LANGUAGES = {'ru': 'Русский', 'en': 'English', 'zh': '简体中文'}
COOKIE = 'allmanagerc_language'


def _app_data_dir() -> str:
    if has_request_context():
        configured = current_app.config.get('APP_DATA_DIR')
        if configured:
            return configured
    return '.'


def get_locale():
    if not has_request_context():
        return DEFAULT_LANGUAGE

    cookie_language = request.cookies.get(COOKIE)
    if cookie_language in LANGUAGES:
        return cookie_language

    prefs = load_ui_preferences(_app_data_dir())
    return normalize_language(prefs.get('language'), DEFAULT_LANGUAGE)


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
        prefs = load_ui_preferences(_app_data_dir())
        return {
            'current_locale': get_locale(),
            'ui_languages': LANGUAGES,
            'ui_zoom': prefs.get('zoom', '80'),
        }

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
        save_ui_preferences(_app_data_dir(), language=language)
        response = redirect(target)
        response.set_cookie(COOKIE, language, max_age=365 * 24 * 60 * 60,
                            httponly=True, samesite='Lax', secure=request.is_secure)
        return response

    @app.post('/ui_preferences')
    def save_ui_preferences_route():
        payload = request.get_json(silent=True) or {}
        language = payload.get('language')
        zoom = payload.get('zoom')
        kwargs = {}
        if language is not None:
            if language not in ALLOWED_LANGUAGES:
                return jsonify({'success': False, 'error': 'unsupported_language'}), 400
            kwargs['language'] = language
        if zoom is not None:
            zoom = str(zoom).rstrip('%')
            if zoom not in ALLOWED_ZOOMS:
                return jsonify({'success': False, 'error': 'unsupported_zoom'}), 400
            kwargs['zoom'] = zoom
        if not kwargs:
            return jsonify({'success': False, 'error': 'nothing_to_save'}), 400

        prefs = save_ui_preferences(_app_data_dir(), **kwargs)
        response = jsonify({'success': True, 'ui': prefs})
        if 'language' in kwargs:
            response.set_cookie(
                COOKIE,
                kwargs['language'],
                max_age=365 * 24 * 60 * 60,
                httponly=True,
                samesite='Lax',
                secure=request.is_secure,
            )
        return response
