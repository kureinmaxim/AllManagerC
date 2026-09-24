import json
import os
import sys
from pathlib import Path
from runtime_paths import packaged_data_dir
from localization import gettext as _, init_localization
from datetime import date, datetime
import uuid
from flask import Flask, render_template, request, redirect, url_for, make_response, send_from_directory, jsonify, flash, abort, session, send_file
from dotenv import load_dotenv
from cryptography.fernet import Fernet, InvalidToken
from werkzeug.utils import secure_filename
from werkzeug.serving import make_server
import requests
from urllib.parse import urlparse
import copy
import threading
import subprocess
import shutil
import webview
import signal
import logging
import re
from jinja2 import Environment, FileSystemLoader, select_autoescape
from jinja2.ext import do as DoExtension
try:
    from yubikey_auth import check_internet_connection
except Exception:
    def check_internet_connection(timeout: float = 0.5):
        return False
import sys
import socket
import time

# Handle Windows console encoding for non-encodable characters (e.g., emojis)
try:
    if os.name == 'nt':
        for _name in ('stdout', 'stderr'):
            _stream = getattr(sys, _name, None)
            if _stream is not None and hasattr(_stream, 'reconfigure'):
                _stream.reconfigure(errors='replace')
except Exception:
    pass

# Улучшенная загрузка .env файла для работы в дистрибутиве
def load_env_file():
    """Загружает .env файл из различных возможных мест."""
    from pathlib import Path
    import os
    
    if getattr(sys, 'frozen', False):
        env_path = packaged_data_dir() / '.env'
        if env_path.is_file():
            load_dotenv(env_path)
            return True
        return False

    # Список возможных путей к .env файлу
    possible_paths = []
    
    # 1. Текущая директория (для разработки)
    possible_paths.append(Path.cwd() / ".env")
    
    # 2. Директория приложения (для дистрибутива)
    if getattr(sys, 'frozen', False):
        # Если приложение запаковано
        if sys.platform == 'darwin':  # macOS
            # В .app бандле
            app_bundle = Path(sys.executable).parent.parent.parent
            possible_paths.append(app_bundle / "Contents" / "Resources" / ".env")
            # В пользовательской директории
            user_env = Path.home() / "Library" / "Application Support" / "AllManagerC" / ".env"
            possible_paths.append(user_env)
            # В директории приложения
            app_dir = Path(sys.executable).parent
            possible_paths.append(app_dir / ".env")
        elif sys.platform == 'win32':  # Windows
            # Основной путь для .exe — директория данных пользователя
            from pathlib import Path as _P
            possible_paths.append(_P(os.environ.get('APPDATA', str(Path.home()))) / 'AllManagerC' / '.env')
            # Рядом с исполняемым файлом
            possible_paths.append(Path(sys.executable).parent / '.env')
        else:
            # Linux и др.: ~/.local/share/AllManagerC/.env и рядом с exe
            possible_paths.append(Path.home() / '.local' / 'share' / 'AllManagerC' / '.env')
            possible_paths.append(Path(sys.executable).parent / '.env')
    
    # 3. Директория скрипта
    script_dir = Path(__file__).parent
    possible_paths.append(script_dir / ".env")
    
    # 4. Родительская директория
    parent_dir = Path(__file__).parent.parent
    possible_paths.append(parent_dir / ".env")
    
    # Пытаемся загрузить .env из каждого возможного места
    for env_path in possible_paths:
                print(f"🔍 Проверяем путь: {env_path} {'✅' if env_path.exists() else '❌'}")
                if env_path.exists():
                    print(f"📁 Найден .env файл: {env_path}")
                    load_dotenv(env_path)
                    return True
    
    print(f"❌ .env файл не найден в следующих местах:")
    for path in possible_paths:
        print(f"   - {path} {'✅' if path.exists() else '❌'}")
    
    return False

# Загружаем .env файл
load_env_file()

app = Flask(__name__)
init_localization(app)
# Уникальное имя cookie для сессии, чтобы не пересекаться с другими приложениями на 127.0.0.1
app.config['SESSION_COOKIE_NAME'] = 'allmanagerc_session'

# Включаем расширение 'do' для использования в шаблонах Jinja2
app.jinja_env.add_extension(DoExtension)

# Функция для определения директории для хранения данных
def get_app_data_dir():
    """
    Возвращает директорию для хранения пользовательских данных приложения.
    Учитывает различие между режимом разработки и запакованным приложением.
    """
    if getattr(sys, 'frozen', False):
        directory = packaged_data_dir()
        (directory / 'data').mkdir(parents=True, exist_ok=True)
        (directory / 'uploads').mkdir(exist_ok=True)
        return str(directory)

    # Определяем, запущено ли приложение как пакет
    is_frozen = getattr(sys, 'frozen', False)
    
    # Имя директории приложения
    app_name = "AllManagerC"
    
    if is_frozen:  # Приложение запущено как .app или .exe
        if sys.platform == 'darwin':  # macOS
            # ~/Library/Application Support/AllManager
            app_data_dir = os.path.join(
                os.path.expanduser("~"), 
                "Library", "Application Support", 
                app_name
            )
        elif sys.platform == 'win32':  # Windows
            # %APPDATA%\AllManager
            app_data_dir = os.path.join(
                os.environ.get('APPDATA', os.path.expanduser("~")),
                app_name
            )
        else:  # Linux и другие системы
            # ~/.local/share/AllManager
            app_data_dir = os.path.join(
                os.path.expanduser("~"),
                ".local", "share",
                app_name
            )
    else:
        # В режиме разработки используем локальные пути,
        # а для инсталлятора на Windows — Roaming (если установлен признак сборки)
        app_data_dir = os.path.join(os.getcwd())
        try:
            if os.name == 'nt' and (os.getenv('ALLMANAGERC_INSTALLED') == '1' or getattr(sys, 'frozen', False)):
                app_name = "AllManagerC"
                app_data_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser("~")), app_name)
        except Exception:
            pass
    
    # Создаем директории для данных и загрузок
    os.makedirs(os.path.join(app_data_dir, "data"), exist_ok=True)
    os.makedirs(os.path.join(app_data_dir, "uploads"), exist_ok=True)
    
    return app_data_dir

# --- НОВАЯ ЛОГИКА ИНИЦИАЛИЗАЦИИ КОНФИГА ---
APP_DATA_DIR = get_app_data_dir()
is_frozen = getattr(sys, 'frozen', False)

# --- ИНИЦИАЛИЗАЦИЯ YubiKey ---
try:
    from yubikey_auth import init_yubikey_auth
    # Убеждаемся, что директория существует
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    print(f"📁 APP_DATA_DIR: {APP_DATA_DIR}")
    
    yubikey_auth = init_yubikey_auth(APP_DATA_DIR)
    if yubikey_auth:
        print("✅ YubiKey аутентификация инициализирована")
        print(f"   - Enabled: {yubikey_auth.enabled}")
        print(f"   - Keys count: {len(yubikey_auth.keys)}")
    else:
        print("⚠️ YubiKey аутентификация не инициализирована")
        yubikey_auth = None
except ImportError as e:
    print(f"⚠️ Модуль yubikey_auth не найден: {e}")
    print("⚠️ YubiKey аутентификация отключена.")
    yubikey_auth = None
except Exception as e:
    print(f"❌ Ошибка инициализации YubiKey: {e}")
    print("⚠️ YubiKey аутентификация отключена.")
    yubikey_auth = None

# Путь к конфигу в директории данных пользователя
user_config_path = Path(APP_DATA_DIR) / 'config.json'

def load_config_from_path(path):
    """Загружает JSON конфиг из указанного пути."""
    if not path.exists():
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None

# Шаг 1: Загрузить "эталонный" конфиг из бандла (если применимо)
bundle_config = None
if is_frozen:
    try:
        # sys._MEIPASS - это специальный путь, который PyInstaller создает в собранном приложении
        bundle_config_path = Path(sys._MEIPASS) / 'config.json'
        bundle_config = load_config_from_path(bundle_config_path)
    except Exception as e:
        print(f"Не удалось найти или загрузить эталонный конфиг: {e}")

# Шаг 2: Загрузить пользовательский конфиг
user_config = load_config_from_path(user_config_path)

# Шаг 3: Определить, какой конфиг использовать и нужно ли обновление
final_config = {}
if user_config is None and bundle_config is not None:
    # Случай 1: У пользователя нет конфига, копируем из бандла
    print(f"Пользовательский конфиг не найден. Копирование из {bundle_config_path}")
    try:
        shutil.copy(bundle_config_path, user_config_path)
        final_config = bundle_config
    except Exception as e:
        print(f"Ошибка копирования конфига: {e}")
        final_config = {} # Используем пустой, чтобы избежать сбоя
elif bundle_config is not None and user_config is not None:
    # Случай 2: Оба конфига есть. Сравниваем и обновляем.
    bundle_version = bundle_config.get('app_info', {}).get('version', '0.0.0')
    user_version = user_config.get('app_info', {}).get('version', '0.0.0')

    # Простое сравнение версий (можно заменить на более сложное, если нужно)
    if bundle_version > user_version:
        print(f"Найдена новая версия ({bundle_version} > {user_version}). Обновление конфига.")
        # Обновляем информацию о приложении, сохраняя остальные настройки пользователя
        user_config['app_info'] = bundle_config['app_info']
        final_config = user_config
        # Сохраняем обновленный конфиг
        try:
            with open(user_config_path, 'w', encoding='utf-8') as f:
                json.dump(user_config, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Ошибка сохранения обновленного конфига: {e}")
    else:
        # Версия не новее, используем конфиг пользователя как есть
        final_config = user_config
else:
    # Случай 3: Используем конфиг пользователя (или пустой, если его нет и нет бандла)
    final_config = user_config if user_config is not None else {}
    if not is_frozen and not user_config_path.exists():
        print(f"ВНИМАНИЕ: {user_config_path} не найден в режиме разработки. Будет создан пустой.")
        # Создаем пустой файл, чтобы избежать ошибок при последующих сохранениях
        with open(user_config_path, 'w', encoding='utf-8') as f:
            json.dump({}, f)

# Загрузка основной конфигурации в Flask
app.config.update(final_config)


# Если `app_info` все еще отсутствует (например, при самом первом запуске в dev), добавляем заглушку
if 'app_info' not in app.config:
    # Пытаемся загрузить версию из config.json
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            version = config.get('app_info', {}).get('version', '5.6.0')
            developer = config.get('app_info', {}).get('developer', 'AI Manager Team')
    except:
        version = '5.6.0'
        developer = 'AI Manager Team'
    app.config['app_info'] = {
        "version": "N/A",
        "last_updated": "N/A",
        "developer": "N/A"
    }

# Добавим фильтр для Jinja2
def format_datetime_filter(iso_str):
    """Jinja фильтр для форматирования ISO-строки с датой и временем."""
    if not iso_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime('%Y-%m-%d %H:%M')
    except (ValueError, TypeError):
        return iso_str

app.jinja_env.filters['format_datetime'] = format_datetime_filter

@app.context_processor
def inject_app_info():
    """Инжектирует информацию о приложении во все шаблоны."""
    return {'app_info': app.config.get('app_info', {})}

# Ключ для flash-сообщений
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", "a-default-secret-key-for-flash")

# Устанавливаем пути относительно директории данных приложения
app.config['UPLOAD_FOLDER'] = os.path.join(APP_DATA_DIR, 'uploads')
# Расширяем разрешенные расширения для зашифрованных данных
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'rtf', 'md', 'pdf', 'png', 'jpg', 'jpeg', 'enc'}

# Убедимся, что папки для загрузок и данных существуют

# --- НАСТРОЙКИ БЕЗОПАСНОСТИ ---
# Ограничение доступа по IP (только локальный доступ)
ALLOWED_IPS = ["127.0.0.1", "::1"]  # localhost и IPv6 localhost

# Настройка логирования безопасности
try:
    from security_logger import setup_security_logger, log_security_event
    security_logger = setup_security_logger()
    print("✅ Логгер безопасности инициализирован")
except ImportError:
    print("⚠️ Модуль security_logger не найден. Логирование безопасности отключено.")
    def log_security_event(event_type, details, ip_address=None):
        print(f"🔒 SECURITY: {event_type} - {details} - IP: {ip_address}")
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(APP_DATA_DIR, 'data'), exist_ok=True)

@app.context_processor
def inject_request():
    return {'request': request}

@app.context_processor
def inject_service_urls():
    # Инжектируем URL-адреса сервисов и путь к активному файлу данных
    return {
        'service_urls': app.config.get('service_urls', {}),
        'active_data_file': get_active_data_path()  # Используем полный абсолютный путь
    }

@app.context_processor
def inject_yubikey_status():
    """Инжектирует статус YubiKey во все шаблоны с улучшенной обработкой ошибок."""
    try:
        # Проверяем, есть ли активный контекст запроса
        from flask import has_request_context
        if not has_request_context():
            print("⚠️ inject_yubikey_status вызван вне контекста запроса")
            return {
                'yubikey_status': {
                    'available': yubikey_auth is not None,
                    'enabled': yubikey_auth.enabled if yubikey_auth else False,
                    'authenticated': False,  # Безопасное значение вне контекста
                    'keys_count': len(yubikey_auth.get_keys()) if yubikey_auth else 0
                }
            }
        
        yubikey_status = {
            'available': yubikey_auth is not None,
            'enabled': yubikey_auth.enabled if yubikey_auth else False,
            'authenticated': yubikey_auth.is_authenticated() if yubikey_auth else False,
            'keys_count': len(yubikey_auth.get_keys()) if yubikey_auth else 0
        }
        return {'yubikey_status': yubikey_status}
    except Exception as e:
        print(f"⚠️ Ошибка в inject_yubikey_status: {e}")
        # Возвращаем безопасные значения по умолчанию
        return {
            'yubikey_status': {
                'available': False,
                'enabled': False,
                'authenticated': False,
                'keys_count': 0
            }
        }

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def check_ip_access():
    """Проверяет, разрешен ли доступ с текущего IP."""
    client_ip = request.remote_addr
    if client_ip not in ALLOWED_IPS:
        log_security_event("ACCESS_DENIED", f"IP: {client_ip}", client_ip)
        abort(403, description="Доступ запрещен с вашего IP-адреса")

@app.before_request
def before_request_security():
    """Выполняется перед каждым запросом для проверки безопасности."""
    check_ip_access()

# Динамическое требование аутентификации (независимо от декораторов маршрутов)
@app.before_request
def enforce_authentication_dynamic():
    try:
        # Разрешённые эндпоинты без входа (включая скрытый PIN-вход)
        allowed_endpoints = {
            'yubikey_login', 'yubikey_instructions', 'change_language',
            'secret_login', 'change_secret_pin',
            'static', 'help_page', 'about_page', 'set_clipboard', 'shutdown'
        }
        ep = request.endpoint or ''

        # Если модуль не инициализирован — выходим (UI покажет «Не защищено»)
        if yubikey_auth is None:
            return None

        # Если защита выключена — пропускаем
        if not getattr(yubikey_auth, 'enabled', False):
            return None

        # Если ключей нет — разрешаем только настройки/мастер и статику
        try:
            if len(yubikey_auth.get_keys()) == 0 and not yubikey_auth.static_passwords:
                if ep in {'yubikey_setup', 'static', 'secret_login', 'yubikey_login', 'change_language'}:
                    return None
                session.pop('yubikey_authenticated', None)
                return redirect('/yubikey/setup')
        except Exception:
            pass

        # Для всех остальных: если не аутентифицирован — отправляем на вход
        if ep not in allowed_endpoints and not yubikey_auth.is_authenticated():
            return redirect('/yubikey/login')
    except Exception:
        return None

# --- NEW, ROBUST LOGIC FOR SECRET_KEY ---
SECRET_KEY = None
is_frozen = getattr(sys, 'frozen', False)

if is_frozen:
    # Если приложение собрано, ищем .env в платформа-зависимых местах
    try:
        dotenv_candidates = [Path(APP_DATA_DIR) / ".env"]
        if sys.platform == 'win32':
            # Основное место для Windows: директория данных пользователя
            dotenv_candidates.append(Path(APP_DATA_DIR) / '.env')
            # Также пробуем рядом с исполняемым файлом
            dotenv_candidates.append(Path(sys.executable).parent / '.env')
        elif sys.platform == 'darwin':
            base_path = Path(sys.executable).parent.parent / 'Resources'
            dotenv_candidates.append(base_path / '.env')
        else:
            # Linux и другие системы
            dotenv_candidates.append(Path(APP_DATA_DIR) / '.env')
            dotenv_candidates.append(Path(sys.executable).parent / '.env')
        for _p in dotenv_candidates:
            if _p.exists():
                load_dotenv(dotenv_path=_p)
                SECRET_KEY = os.getenv("SECRET_KEY")
                if SECRET_KEY:
                    break
    except Exception:
        SECRET_KEY = None
else:
    # Для разработки, ищем .env в корне проекта
    load_dotenv()
    SECRET_KEY = os.getenv("SECRET_KEY")

# Если ключ не найден, создаем новый
if not SECRET_KEY:
    try:
        # Генерируем новый ключ
        new_key = Fernet.generate_key().decode()
        SECRET_KEY = new_key
        
        # Сохраняем ключ в .env файл
        if is_frozen:
            # Для дистрибутива сохраняем в пользовательской директории
            env_file = os.path.join(APP_DATA_DIR, '.env')
        else:
            # Для разработки сохраняем в корне проекта
            env_file = '.env'
        
        with open(env_file, 'a') as f:
            f.write(f'\nSECRET_KEY={new_key}\n')
        os.environ["SECRET_KEY"] = new_key
        
        print(f"✅ Создан новый ключ шифрования: {env_file}")
    except Exception as e:
        print(f"❌ Ошибка создания ключа: {e}")
        # Создаем временный ключ для работы
        SECRET_KEY = Fernet.generate_key().decode()

fernet = Fernet(SECRET_KEY.encode())

def collect_extra_credentials(form, existing=()):
    """Encrypt submitted accounts, retaining an unchanged password by original index."""
    usernames = form.getlist('extra_username[]')
    passwords = form.getlist('extra_password[]')
    indices = form.getlist('extra_index[]')
    result = []
    for i, username in enumerate(usernames):
        password = passwords[i] if i < len(passwords) else ''
        index = indices[i] if i < len(indices) else ''
        previous = existing[int(index)] if index.isdigit() and int(index) < len(existing) else {}
        if not username and not password and not previous:
            continue
        credential = {key: value for key, value in previous.items() if not key.endswith('_decrypted')}
        credential['username'] = encrypt_data(username)
        credential['password'] = encrypt_data(password) if password else previous.get('password', '')
        result.append(credential)
    return result


def encrypt_data(data):
    if not data:
        return ""
    return fernet.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data):
    """
    Расшифровывает данные, зашифрованные с помощью Fernet.
    Автоматически определяет формат данных и обрабатывает их соответственно.
    """
    # Проверяем на пустые данные в начале
    if not encrypted_data or encrypted_data == "" or encrypted_data is None:
        return ""
    
    # Конвертируем в строку если нужно
    if not isinstance(encrypted_data, str):
        encrypted_data = str(encrypted_data)
    
    # Дополнительная проверка на пустую строку после конвертации
    if encrypted_data.strip() == "":
        return ""
    
    # Если данные начинаются с gAAAAA или выглядят как зашифрованные Fernet данные
    if encrypted_data.startswith('gAAAAA') or (len(encrypted_data) > 50 and not ' ' in encrypted_data):
        try:
            return fernet.decrypt(encrypted_data.encode()).decode()
        except Exception:
            # Если расшифровка не удалась, возвращаем предупреждение
            return "⚠️ Данные зашифрованы старым ключом"
    
    # Если данные выглядят как обычный читаемый текст
    if all(ord(c) < 128 and (c.isprintable() or c.isspace()) for c in encrypted_data) and len(encrypted_data) < 100:
        return encrypted_data
    
    # Для всех остальных случаев (длинные строки без пробелов, подозрительные данные)
    try:
        import base64
        # Пытаемся декодировать как base64
        decoded = base64.b64decode(encrypted_data)
        
        # Если успешно декодировалось и выглядит как Fernet данные, пытаемся расшифровать
        if len(decoded) >= 57:
            try:
                return fernet.decrypt(encrypted_data.encode()).decode()
            except Exception:
                return "⚠️ Данные зашифрованы старым ключом"
        else:
            return encrypted_data
    except Exception:
        # Если это явно не текст и не удалось обработать - скорее всего зашифрованные данные
        return "⚠️ Данные зашифрованы старым ключом"
def save_app_config():
    """Сохраняет текущую JSON-совместимую конфигурацию в файл."""
    # Сначала читаем текущий файл, чтобы не потерять ключи, которых нет в app.config
    config_path = os.path.join(APP_DATA_DIR, 'config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_to_save = json.load(f)
            if not isinstance(config_to_save, dict):
                config_to_save = {}
    except (FileNotFoundError, json.JSONDecodeError):
        config_to_save = {}

    # Обновляем ключи из app.config, которые должны быть в JSON
    for key in ['version', 'developer', 'service_urls', 'app_info']:
        if key in app.config:
            config_to_save[key] = app.config[key]
            
    # Особо обрабатываем active_data_file
    if app.config.get('active_data_file'):
        config_to_save['active_data_file'] = app.config['active_data_file']
    else:
        # Удаляем ключ, если он None или пустая строка
        config_to_save.pop('active_data_file', None)
        
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config_to_save, f, ensure_ascii=False, indent=2)

def get_active_data_path():
    """Возвращает полный путь к активному файлу данных из конфигурации."""
    path = app.config.get('active_data_file')
    if path:
        local_candidate = os.path.join(APP_DATA_DIR, 'data', str(path).replace('\\', '/').rsplit('/', 1)[-1])
        if not os.path.exists(path) and os.path.isfile(local_candidate):
            return local_candidate
        # Если путь относительный, сделать его абсолютным относительно APP_DATA_DIR
        if not os.path.isabs(path):
            return os.path.join(APP_DATA_DIR, path)
        return path
    return None

def get_export_dir():
    """Возвращает безопасную директорию для экспорта файлов."""
    # Используем папку Downloads пользователя - стандартное место для загрузок
    downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    if os.path.exists(downloads_dir) and os.access(downloads_dir, os.W_OK):
        return downloads_dir
    
    # Если Downloads недоступна, используем APP_DATA_DIR
    return APP_DATA_DIR


def get_day_with_suffix(d):
    return str(d) + ("th" if 4 <= d <= 20 or 24 <= d <= 30 else {1: "st", 2: "nd", 3: "rd"}.get(d % 10, "th"))

def analyze_hosting(ip_info):
    if not ip_info:
        return {"text": "Неизвестно", "quality": "secondary"}
    
    # Расширенный черный список ключевых слов для хостингов, VPN и дата-центров
    bad_keywords = [
        # Общие термины
        'hosting', 'vpn', 'proxy', 'datacenter', 'vps', 'server', 'cloud', 'cdn', 'dedicated',
        
        # Крупные хостинг-провайдеры и облака
        'hetzner', 'ovh', 'digitalocean', 'linode', 'vultr', 'contabo', 'leaseweb', 'scaleway',
        'amazon', 'aws', 'google', 'gcp', 'microsoft', 'azure', 'oracle', 'ionos', 'upcloud',
        'godaddy', 'bluehost', 'hostgator', 'dreamhost', 'liquidweb', 'choopa', 'frantech',
        'datacamp', # Добавлено для вашего случая
        
        # Названия известных VPN-сервисов
        'nord', 'expressvpn', 'cyberghost', 'private internet access', 'pia', 'surfshark',
        'vyprvpn', 'tunnelbear', 'proton'
    ]
    
    org = ip_info.get('org', '').lower()
    for keyword in bad_keywords:
        if keyword in org:
            return {"text": "Хостинг", "quality": "danger"}

    # Исправлена проверка с .get('hosting') на .get('host')
    if ip_info.get('hosting', {}).get('host'):
         return {"text": "Хостинг", "quality": "danger"}

    return {"text": "ISP/Residential", "quality": "success"}

def load_ai_services():
    """Загружает и расшифровывает серверы из активного зашифрованного файла."""
    active_file = get_active_data_path()
    if not active_file or not os.path.exists(active_file):
        return []

    try:
        with open(active_file, 'rb') as f:
            encrypted_data = f.read()

        if not encrypted_data:
            return []

        decrypted_data = fernet.decrypt(encrypted_data)
        servers = json.loads(decrypted_data.decode('utf-8'))
        
        today = date.today()
        # Расшифровываем конфиденциальные данные для отображения
        for server in servers:
            # Для обратной совместимости добавляем недостающие ключи
            if 'status' not in server:
                server['status'] = 'Active' # Статус по умолчанию
            if 'payment_info' not in server:
                server['payment_info'] = {}
            if 'payment_period' not in server['payment_info']:
                server['payment_info']['payment_period'] = ''
            if 'panel_credentials' not in server:
                server['panel_credentials'] = {}
            if 'hoster_credentials' not in server:
                server['hoster_credentials'] = {}
            if 'login_method' not in server.get('hoster_credentials', {}):
                server['hoster_credentials']['login_method'] = 'password'
            if 'geolocation' not in server:
                server['geolocation'] = {}
            if 'checks' not in server:
                server['checks'] = {"dns_ok": False, "streaming_ok": False}

            if "ssh_credentials" in server:
                if 'root_password' not in server['ssh_credentials']:
                    server['ssh_credentials']['root_password'] = ''
                if 'root_login_allowed' not in server['ssh_credentials']:
                    server['ssh_credentials']['root_login_allowed'] = False
                server["ssh_credentials"]["password_decrypted"] = decrypt_data(server["ssh_credentials"].get("password", ""))
                server["ssh_credentials"]["root_password_decrypted"] = decrypt_data(server["ssh_credentials"].get("root_password", ""))
            
            # Автоматическое обновление статуса на основе даты платежа
            due_date_str = server.get('payment_info', {}).get('next_due_date')
            if server.get('status') == 'Active' and due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                    if due_date < today:
                        delta = today - due_date
                        if delta.days > 5:
                            server['status'] = 'Удален'
                        else:
                            server['status'] = 'Приостановлен'
                except (ValueError, TypeError):
                    pass  # Игнорируем неверный формат даты

            # Анализ хостинга
            server['hosting_analysis'] = analyze_hosting(server.get('geolocation'))

            # Форматируем дату
            due_date_str = server.get('payment_info', {}).get('next_due_date')
            if due_date_str:
                try:
                    date_obj = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                    day_with_suffix = get_day_with_suffix(date_obj.day)
                    server['payment_info']['formatted_date'] = date_obj.strftime(f'%B {day_with_suffix}, %Y')
                except (ValueError, TypeError):
                    server['payment_info']['formatted_date'] = due_date_str
            else:
                server['payment_info']['formatted_date'] = 'N/A'


            if "ssh_credentials" in server and "password" in server["ssh_credentials"]:
                pass # Логика перенесена выше для согласованности
            
            # Расшифровываем данные панели управления
            if "panel_credentials" in server:
                server["panel_credentials"]["user_decrypted"] = decrypt_data(server["panel_credentials"].get("user", ""))
                server["panel_credentials"]["password_decrypted"] = decrypt_data(server["panel_credentials"].get("password", ""))

            # Расшифровываем данные кабинета хостера
            if "hoster_credentials" in server:
                server["hoster_credentials"]["user_decrypted"] = decrypt_data(server["hoster_credentials"].get("user", ""))
                server["hoster_credentials"]["password_decrypted"] = decrypt_data(server["hoster_credentials"].get("password", ""))

            # Расшифровываем основные учетные данные (credentials)
            if "credentials" in server:
                server["credentials"]["username_decrypted"] = decrypt_data(server["credentials"].get("username", ""))
                server["credentials"]["password_decrypted"] = decrypt_data(server["credentials"].get("password", ""))
                server["credentials"]["additional_info_decrypted"] = decrypt_data(server["credentials"].get("additional_info", ""))

            # Расшифровываем дополнительные учетные данные (credentials_list)
            if "credentials_list" in server and isinstance(server["credentials_list"], list):
                for cred in server["credentials_list"]:
                    try:
                        if isinstance(cred, dict):
                            cred["username_decrypted"] = decrypt_data(cred.get("username", ""))
                            cred["password_decrypted"] = decrypt_data(cred.get("password", ""))
                            cred["additional_info_decrypted"] = decrypt_data(cred.get("additional_info", ""))
                    except Exception:
                        continue

            if 'receipts' in server.get('payment_info', {}):
                # Сортировка чеков по дате загрузки (от новых к старым)
                server['payment_info']['receipts'].sort(key=lambda r: r.get('upload_date', ''), reverse=True)

        return servers
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    except (InvalidToken, Exception):
        # Если ключ неверный или файл поврежден
        flash('Не удалось расшифровать файл данных. Проверьте ваш SECRET_KEY или целостность файла.', 'danger')
        return []

def save_ai_services(servers):
    """Шифрует и сохраняет полный список серверов в активный файл."""
    active_file = get_active_data_path()
    if not active_file:
        flash('Ошибка: не указан активный файл данных. Сохранение невозможно.', 'danger')
        return

    # Создаем копию для безопасного сохранения, удаляя временные поля
    servers_to_save = copy.deepcopy(servers)
    for server in servers_to_save:
        # Удаляем все временные расшифрованные ключи
        if 'ssh_credentials' in server:
            server['ssh_credentials'].pop('password_decrypted', None)
            server['ssh_credentials'].pop('root_password_decrypted', None)
        if 'panel_credentials' in server:
            server['panel_credentials'].pop('user_decrypted', None)
            server['panel_credentials'].pop('password_decrypted', None)
        if 'hoster_credentials' in server:
            server['hoster_credentials'].pop('user_decrypted', None)
            server['hoster_credentials'].pop('password_decrypted', None)
        if 'credentials' in server:
            server['credentials'].pop('username_decrypted', None)
            server['credentials'].pop('password_decrypted', None)
            server['credentials'].pop('additional_info_decrypted', None)
        # Удаляем расшифрованные поля из дополнительных учетных данных
        if 'credentials_list' in server and isinstance(server['credentials_list'], list):
            for cred in server['credentials_list']:
                if isinstance(cred, dict):
                    cred.pop('username_decrypted', None)
                    cred.pop('password_decrypted', None)
                    cred.pop('additional_info_decrypted', None)
        
        # Удаляем другие временные поля, созданные для UI
        server.pop('hosting_analysis', None)
        server.pop('os_icon', None)
        server.pop('masked_panel_url', None)
        if 'payment_info' in server:
            server['payment_info'].pop('formatted_date', None)

    try:
        json_string = json.dumps(servers_to_save, ensure_ascii=False, indent=2)
        encrypted_data = fernet.encrypt(json_string.encode('utf-8'))
        
        with open(active_file, 'wb') as f:
            f.write(encrypted_data)
    except Exception as e:
        flash(f'Произошла ошибка при сохранении файла: {e}', 'danger')


def re_encrypt_service_data(service, external_fernet, current_fernet):
    """
    Перешифровывает зашифрованные поля сервиса с внешнего ключа на текущий ключ.
    Принимает сервис, внешний fernet объект и текущий fernet объект.
    Возвращает сервис с перешифрованными данными.
    """
    service_copy = copy.deepcopy(service)
    
    # Список полей для перешифровки
    fields_to_reencrypt = [
        ('credentials', 'username'),
        ('credentials', 'password'),
        ('credentials', 'additional_info'),
        ('personal_cabinet', 'account_email'),
        ('ssh_credentials', 'password'),
        ('ssh_credentials', 'root_password'),
        ('panel_credentials', 'user'),
        ('panel_credentials', 'password'),
        ('hoster_credentials', 'user'),
        ('hoster_credentials', 'password')
    ]
    
    for section, field in fields_to_reencrypt:
        try:
            # Проверяем, существует ли секция и поле
            if section in service_copy and field in service_copy[section]:
                encrypted_value = service_copy[section][field]
                
                # Пропускаем пустые значения
                if not encrypted_value or encrypted_value == "":
                    continue
                
                # Расшифровываем внешним ключом
                try:
                    decrypted_value = external_fernet.decrypt(encrypted_value.encode()).decode()
                    # Зашифровываем текущим ключом
                    reencrypted_value = current_fernet.encrypt(decrypted_value.encode()).decode()
                    service_copy[section][field] = reencrypted_value
                except Exception as e:
                    # Если не удалось расшифровать внешним ключом, возможно это уже текущий ключ
                    # или пустые данные - оставляем как есть
                    continue
                    
        except Exception as e:
            # В случае ошибки с секцией, продолжаем обработку других полей
            continue
    
    # Обрабатываем список дополнительных учетных данных
    try:
        if 'credentials_list' in service_copy and isinstance(service_copy['credentials_list'], list):
            new_list = []
            for cred in service_copy['credentials_list']:
                if not isinstance(cred, dict):
                    continue
                new_cred = dict(cred)
                for key in ['username', 'password', 'additional_info']:
                    try:
                        value = cred.get(key)
                        if value:
                            # Пытаемся расшифровать внешним ключом и зашифровать текущим
                            decrypted = external_fernet.decrypt(value.encode()).decode()
                            new_cred[key] = current_fernet.encrypt(decrypted.encode()).decode()
                    except Exception:
                        # Если не удалось — оставляем как есть (возможно уже текущий ключ)
                        pass
                # Убираем временные расшифрованные ключи, если были
                new_cred.pop('username_decrypted', None)
                new_cred.pop('password_decrypted', None)
                new_cred.pop('additional_info_decrypted', None)
                new_list.append(new_cred)
            service_copy['credentials_list'] = new_list
    except Exception:
        pass

    return service_copy


def generate_search_hints():
    """Генерирует подсказки для поиска на основе активных данных."""
    try:
        services = load_ai_services()
        hints = []
        
        for service in services:
            if service.get('name'):
                hints.append(service['name'])
            if service.get('provider'):
                hints.append(service['provider'])
            if service.get('service_type'):
                hints.append(service['service_type'])
                
        hints = list(set(hints))  # Удаляем дубликаты
        hints.sort()
        
        # Сохраняем подсказки в JSON файл
        with open('static/search_hints.json', 'w', encoding='utf-8') as f:
            json.dump(hints, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка генерации подсказок поиска: {e}")

def migrate_data():
    """
    Выполняет однократную миграцию из старого формата `servers.json`
    в новый зашифрованный `servers.json.enc`.
    Также мигрирует из локальных файлов в директорию данных приложения.
    """
    # Путь к файлам в старой директории проекта
    old_json_path = 'data/servers.json'
    old_enc_path = 'data/servers.json.enc'
    
    # Путь к файлу в новой директории данных
    new_enc_path = os.path.join(APP_DATA_DIR, 'data', 'servers.json.enc')
    
    # Сначала проверяем, нужно ли мигрировать из старого json в новый enc
    if os.path.exists(old_json_path) and not os.path.exists(old_enc_path) and not os.path.exists(new_enc_path):
        print("Обнаружен старый файл данных. Выполняется миграция...")
        try:
            # Загружаем старые данные
            with open(old_json_path, 'r', encoding='utf-8') as f:
                servers = json.load(f)
            
            # Сохраняем их в новом зашифрованном формате в новой директории
            json_string = json.dumps(servers, ensure_ascii=False, indent=2)
            encrypted_data = fernet.encrypt(json_string.encode('utf-8'))
            with open(new_enc_path, 'wb') as f:
                f.write(encrypted_data)

            # Обновляем config.json, чтобы использовать новый файл по умолчанию
            app.config['active_data_file'] = os.path.join('data', 'ai_services.json.enc')
            save_app_config()
            
            # Переименовываем старый файл, чтобы избежать повторной миграции
            os.rename(old_json_path, old_json_path + '.bak')
            print(f"Миграция успешно завершена. Данные сохранены в {new_enc_path}.")
            print(f"Старый файл переименован в {old_json_path}.bak.")
        except Exception as e:
            print(f"Ошибка миграции данных: {e}")
    
    # Затем проверяем, нужно ли мигрировать из старого зашифрованного формата в новую директорию
    elif os.path.exists(old_enc_path) and not os.path.exists(new_enc_path):
        print("Выполняется миграция шифрованного файла в новую директорию...")
        try:
            # Копируем файл в новую директорию
            os.makedirs(os.path.dirname(new_enc_path), exist_ok=True)
            with open(old_enc_path, 'rb') as src, open(new_enc_path, 'wb') as dst:
                dst.write(src.read())
            
            # Обновляем config.json, чтобы использовать новый файл по умолчанию
            app.config['active_data_file'] = os.path.join('data', 'ai_services.json.enc')
            save_app_config()
            
            print(f"Миграция файла в новую директорию завершена успешно.")
        except Exception as e:
            print(f"Ошибка миграции файла: {e}")
    
    # Если файл данных не прикреплен или не существует, создаем его
    active_file = get_active_data_path()
    if not active_file or not os.path.exists(active_file):
        print("Активный файл данных не прикреплен или не существует. Создание файла по умолчанию...")
        default_path = os.path.join('data', 'ai_services.json.enc')
        full_path = os.path.join(APP_DATA_DIR, default_path)
        
        # Создаем пустой файл, если он не существует
        if not os.path.exists(full_path):
            try:
                json_string = json.dumps([], ensure_ascii=False, indent=2)
                encrypted_data = fernet.encrypt(json_string.encode('utf-8'))
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'wb') as f:
                    f.write(encrypted_data)
                    
                # Обновляем config.json, чтобы использовать новый файл по умолчанию
                app.config['active_data_file'] = default_path
                save_app_config()
                
                print(f"Создан новый файл данных: {full_path}")
            except Exception as e:
                print(f"Ошибка создания файла данных: {e}")

# Выполняем проверку и миграцию при старте приложения
migrate_data()
migrate_data()

# OAuth функции для выбора предпочитаемого метода входа
def get_all_oauth_methods(service_name):
    """
    Возвращает все доступные OAuth методы для сервиса
    """
    all_methods = {}
    
    # Добавляем специфичные для сервиса методы
    specific = get_service_specific_oauth(service_name)
    all_methods.update(specific)
    
    # Добавляем универсальные методы
    universal = get_oauth_urls(service_name)
    all_methods.update(universal)
    
    return all_methods

def get_selected_oauth_method(service):
    """
    Возвращает выбранный OAuth метод для сервиса
    """
    preferred_method = service.get('preferred_oauth_method')
    if not preferred_method:
        return None
        
    all_methods = get_all_oauth_methods(service.get('name', 'Unknown'))
    return all_methods.get(preferred_method)

# OAuth функции (должны быть определены до их использования в маршрутах)
def get_oauth_urls(service_name):
    """
    Возвращает словарь с OAuth URL для популярных провайдеров для конкретного сервиса
    """
    oauth_providers = {
        'google': {
            'name': 'Google',
            'url': f'https://accounts.google.com/oauth/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=YOUR_REDIRECT_URI&scope=openid%20email%20profile&response_type=code&service={service_name}',
            'icon': '🔐',
            'class': 'btn-google'
        },
        'apple': {
            'name': 'Apple ID',
            'url': f'https://appleid.apple.com/auth/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=YOUR_REDIRECT_URI&response_type=code&scope=name%20email&service={service_name}',
            'icon': '🍎',
            'class': 'btn-apple'
        },
        'github': {
            'name': 'GitHub',
            'url': f'https://github.com/login/oauth/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=YOUR_REDIRECT_URI&scope=user:email&service={service_name}',
            'icon': '🐙',
            'class': 'btn-github'
        },
        'microsoft': {
            'name': 'Microsoft',
            'url': f'https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=YOUR_REDIRECT_URI&scope=openid%20email%20profile&service={service_name}',
            'icon': '🪟',
            'class': 'btn-microsoft'
        }
    }
    return oauth_providers

def get_service_specific_oauth(service_name):
    """
    Возвращает специфичные для сервиса OAuth ссылки
    """
    service_lower = service_name.lower()
    
    if 'cursor' in service_lower:
        return {
            'cursor': {
                'name': 'Cursor Account',
                'url': 'https://cursor.sh/login',
                'icon': '⚡',
                'class': 'btn-primary'
            }
        }
    elif 'chatgpt' in service_lower or 'openai' in service_lower:
        return {
            'openai': {
                'name': 'OpenAI Account',
                'url': 'https://chat.openai.com/auth/login',
                'icon': '🤖',
                'class': 'btn-primary'
            }
        }
    elif 'medium' in service_lower:
        return {
            'medium': {
                'name': 'Medium Account',
                'url': 'https://medium.com/m/signin',
                'icon': '📝',
                'class': 'btn-primary'
            }
        }
    elif 'notion' in service_lower:
        return {
            'notion': {
                'name': 'Notion Account',
                'url': 'https://www.notion.so/login',
                'icon': '📄',
                'class': 'btn-primary'
            }
        }
    elif 'figma' in service_lower:
        return {
            'figma': {
                'name': 'Figma Account',
                'url': 'https://www.figma.com/login',
                'icon': '🎨',
                'class': 'btn-primary'
            }
        }
    
    return {}

@app.template_filter('encrypt_warning')
def encrypt_warning_filter(text):
    """
    Фильтр для выделения предупреждений о зашифрованных данных
    """
    if isinstance(text, str) and "⚠️ Данные зашифрованы старым ключом" in text:
        return f'<span class="encrypted-data-warning">{text}</span>'
    return text

@app.after_request
def add_security_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

@app.errorhandler(500)
def internal_error(error):
    """Обработчик внутренних ошибок сервера."""
    print(f"❌ Internal Server Error: {error}")
    import traceback
    traceback.print_exc()
    return render_template('error.html', error=error), 500

@app.route('/')
@yubikey_auth.require_auth if yubikey_auth else (lambda f: f)
def index():
    servers = load_ai_services()
    
    def get_os_icon(os_name):
        os_lower = os_name.lower()
        if 'windows' in os_lower:
            return 'bi-windows'
        if 'ubuntu' in os_lower:
            return 'bi-box-seam'
        if 'debian' in os_lower:
            return 'bi-box'
        if 'centos' in os_lower:
            return 'bi-archive'
        if 'linux' in os_lower:
            return 'bi-server'
        return 'bi-question-circle'
    
    def mask_url_path(url_string):
        if not url_string or not url_string.strip():
            return "⚠️ Данные зашифрованы старым ключом"
        try:
            parsed = urlparse(url_string)
            # Отображаем только схему и хост. Добавляем /... если есть путь или порт.
            display_url = f"{parsed.scheme}://{parsed.hostname}"
            has_path = parsed.path and parsed.path != '/'
            has_port = parsed.port is not None
            if has_path or has_port:
                display_url += "/..."
            else:
                return url_string # Возвращаем как есть, если нечего скрывать
            return display_url
        except Exception:
            return url_string 

    for server in servers:
        server['os_icon'] = get_os_icon(server.get('os', ''))
        server['masked_panel_url'] = mask_url_path(server.get('panel_url', ''))
        
    return render_template('index.html', 
                          servers=servers,
                          get_oauth_urls=get_oauth_urls,
                          get_service_specific_oauth=get_service_specific_oauth,
                          get_selected_oauth_method=get_selected_oauth_method,
                          get_all_oauth_methods=get_all_oauth_methods)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/add', methods=['GET', 'POST'])
@yubikey_auth.require_auth if yubikey_auth else lambda f: f
def add_service():
    if request.method == 'POST':
        services = load_ai_services()
        
        # Генерация уникального ID как целое число
        if services:
            new_service_id = max(s.get('id', 0) for s in services) + 1
        else:
            new_service_id = 1

        new_service = {
            "id": new_service_id,
            "name": request.form.get('name'),
            "service_type": request.form.get('service_type'),
            "provider": request.form.get('provider'),
            "login_url": request.form.get('login_url'),
            "preferred_oauth_method": request.form.get('preferred_oauth_method'),
            "credentials": {
                "username": encrypt_data(request.form.get('username')),
                "password": encrypt_data(request.form.get('password')),
                "additional_info": encrypt_data(request.form.get('additional_info'))
            },
            # Список дополнительных учетных данных (массив)
            "credentials_list": [],
            "subscription": {
                "plan_name": request.form.get('plan_name'),
                "cost_monthly": float(request.form.get('cost_monthly')) if request.form.get('cost_monthly') else 0.0,
                "currency": request.form.get('currency'),
                "billing_cycle": request.form.get('billing_cycle'),
                "next_payment_date": request.form.get('next_payment_date'),
                "auto_renewal": 'auto_renewal' in request.form,
                "payment_method": request.form.get('payment_method'),
                "notes": request.form.get('subscription_notes')
            },
            "personal_cabinet": {
                "dashboard_url": request.form.get('dashboard_url'),
                "account_email": encrypt_data(request.form.get('account_email'))
            },
            "features": [f.strip() for f in request.form.get('features', '').split(',') if f.strip()],
            "status": request.form.get('status'),
            "notes": request.form.get('notes'),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        # Градиент
        new_service['gradient_color'] = request.form.get('gradient_color', '#667eea')
        
        # Автоматическая генерация градиента
        base_rgb = [
            int(new_service['gradient_color'][1:3], 16),
            int(new_service['gradient_color'][3:5], 16),
            int(new_service['gradient_color'][5:7], 16)
        ]
        
        # Создаем более темный оттенок
        darker_rgb = [
            max(0, min(255, int(base_rgb[0] * 0.7))),
            max(0, min(255, int(base_rgb[1] * 0.7))),
            max(0, min(255, int(base_rgb[2] * 0.7)))
        ]
        
        # Преобразуем в hex
        gradient_color2 = '#{:02x}{:02x}{:02x}'.format(darker_rgb[0], darker_rgb[1], darker_rgb[2])
        
        new_service['gradient_color1'] = new_service['gradient_color']
        new_service['gradient_color2'] = gradient_color2
        new_service['gradient_css'] = f"linear-gradient(135deg, {new_service['gradient_color1']} 0%, {new_service['gradient_color2']} 100%)"

        # Обработка иконки
        if 'icon_filename' in request.files:
            file = request.files['icon_filename']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                # Добавляем ID к имени файла для уникальности
                unique_filename = f"{new_service_id}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                new_service['icon_filename'] = unique_filename

        services.append(new_service)
        new_service['credentials_list'] = collect_extra_credentials(request.form)
        save_ai_services(services)
        flash('AI-сервис успешно добавлен!', 'success')
        return redirect('/')
    
    # Для GET запроса
    # Загружаем схему для динамического формирования полей формы
    try:
        schema_path = 'ai_services_schema.json'
        if getattr(sys, 'frozen', False):
            schema_path = os.path.join(sys._MEIPASS, schema_path)
        print(f"🔍 Попытка загрузки схемы: {schema_path}")
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        print(f"✅ Схема загружена: {len(schema)} ключей")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"⚠️ Ошибка загрузки схемы: {e}")
        print(f"🔧 Создание схемы по умолчанию...")
        try:
            create_default_schema()
            # Пробуем загрузить из текущей директории
            with open('ai_services_schema.json', 'r', encoding='utf-8') as f:
                schema = json.load(f)
                print(f"✅ Схема по умолчанию загружена")
        except Exception as e2:
            print(f"❌ Ошибка создания схемы по умолчанию: {e2}")
            # Используем схему по умолчанию в коде
            schema = {
                "service_types": [
                    "AI Development Tool", 
                    "AI Writing Assistant", 
                    "AI Image Generator", 
                    "AI Video Generator", 
                    "Media Platform", 
                    "Professional Network", 
                    "Cloud Service", 
                    "Productivity Tool"
                ],
                "supported_currencies": ["USD", "EUR", "RUB", "GBP"],
                "billing_cycles": ["weekly", "monthly", "quarterly", "yearly"],
                "status_options": ["active", "inactive", "trial", "expired", "cancelled"]
            }
            print(f"✅ Использована встроенная схема")
    
    return render_template('add_service.html', schema=schema)

@app.route('/delete/<service_id>', methods=['POST'])
@yubikey_auth.require_auth if yubikey_auth else (lambda f: f)
def delete_service(service_id):
    services = load_ai_services()
    # Приводим service_id к int для корректного сравнения с данными
    try:
        service_id_int = int(service_id)
    except ValueError:
        flash('Неверный ID сервиса.', 'danger')
        return redirect('/')
    
    service_to_delete = next((s for s in services if s['id'] == service_id_int), None)
    
    if service_to_delete:
        # Удаление файла иконки, если он есть
        if service_to_delete.get('icon_filename'):
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], service_to_delete['icon_filename']))
            except OSError as e:
                print(f"Ошибка при удалении иконки: {e}")
                flash(f"Не удалось удалить файл иконки: {service_to_delete['icon_filename']}", 'warning')

        services = [s for s in services if s['id'] != service_id_int]
        save_ai_services(services)
        flash('AI-сервис успешно удален.', 'success')
    else:
        flash('AI-сервис не найден.', 'danger')
        
    return redirect('/')


@app.route('/delete-all-services', methods=['POST'])
@yubikey_auth.require_auth if yubikey_auth else (lambda f: f)
def delete_all_services():
    """Удаляет все AI-сервисы с подтверждением"""
    try:
        services = load_ai_services()

        if not services:
            flash('Нет сервисов для удаления.', 'info')
            return redirect(url_for('index'))

        # Удаляем все иконки
        for service in services:
            if service.get('icon_filename'):
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], service['icon_filename']))
                except OSError as e:
                    print(f"Ошибка при удалении иконки {service['icon_filename']}: {e}")

        # Очищаем список сервисов
        save_ai_services([])

        flash(f'Все {len(services)} AI-сервисов успешно удалены.', 'success')

        # Логируем событие
        log_security_event('delete_all_services', f'Удалено {len(services)} сервисов')

    except Exception as e:
        print(f"Ошибка при удалении всех сервисов: {e}")
        flash('Произошла ошибка при удалении сервисов.', 'danger')

    return redirect(url_for('index'))



@app.route('/edit/<service_id>', methods=['GET', 'POST'])
@yubikey_auth.require_auth if yubikey_auth else (lambda f: f)
def edit_service(service_id):
    services = load_ai_services()
    
    # Приводим service_id к int для корректного сравнения с данными
    try:
        service_id_int = int(service_id)
    except ValueError:
        flash('Неверный ID сервиса.', 'danger')
        return redirect('/')
    
    service = next((s for s in services if s['id'] == service_id_int), None)
    
    if service is None:
        flash('AI-сервис не найден.', 'danger')
        return redirect('/')

    # Дешифруем чувствительные данные для отображения в форме
    decrypted_service = copy.deepcopy(service)
    # Гарантируем наличие вложенных структур для старых записей
    if 'credentials' not in decrypted_service or not isinstance(decrypted_service.get('credentials'), dict):
        decrypted_service['credentials'] = {}
    if 'personal_cabinet' not in decrypted_service or not isinstance(decrypted_service.get('personal_cabinet'), dict):
        decrypted_service['personal_cabinet'] = {}
    if 'subscription' not in decrypted_service or not isinstance(decrypted_service.get('subscription'), dict):
        decrypted_service['subscription'] = {}
    if 'features' not in decrypted_service or not isinstance(decrypted_service.get('features'), list):
        decrypted_service['features'] = []
    if 'gradient_color' not in decrypted_service or not decrypted_service.get('gradient_color'):
        decrypted_service['gradient_color'] = '#667eea'
    # Заполняем безопасные значения по умолчанию для полей, используемых шаблоном
    decrypted_service['subscription'].setdefault('plan_name', '')
    decrypted_service['subscription'].setdefault('cost_monthly', 0.0)
    decrypted_service['subscription'].setdefault('currency', 'USD')
    decrypted_service['subscription'].setdefault('billing_cycle', 'monthly')
    decrypted_service['subscription'].setdefault('next_payment_date', '')
    decrypted_service['subscription'].setdefault('auto_renewal', False)
    decrypted_service['subscription'].setdefault('payment_method', '')
    decrypted_service['subscription'].setdefault('notes', '')
    decrypted_service['personal_cabinet'].setdefault('dashboard_url', '')
    
    decrypted_service['credentials']['username'] = decrypt_data(service.get('credentials', {}).get('username'))
    decrypted_service['credentials']['additional_info'] = decrypt_data(service.get('credentials', {}).get('additional_info'))
    decrypted_service['personal_cabinet']['account_email'] = decrypt_data(service.get('personal_cabinet', {}).get('account_email'))
    
    if request.method == 'POST':
        # Обновляем данные из формы
        service['name'] = request.form.get('name')
        service['service_type'] = request.form.get('service_type')
        service['provider'] = request.form.get('provider')
        service['login_url'] = request.form.get('login_url')
        service['preferred_oauth_method'] = request.form.get('preferred_oauth_method')
        
        # Обновление учетных данных
        if 'credentials' not in service or not isinstance(service.get('credentials'), dict):
            service['credentials'] = {}
        service['credentials']['username'] = encrypt_data(request.form.get('username'))
        if request.form.get('password'): # Обновляем пароль, только если он был введен
            service['credentials']['password'] = encrypt_data(request.form.get('password'))
        service['credentials']['additional_info'] = encrypt_data(request.form.get('additional_info'))
        service['credentials_list'] = collect_extra_credentials(request.form, service.get('credentials_list', []))

        # Обновление подписки
        service['subscription'] = {
            "plan_name": request.form.get('plan_name'),
            "cost_monthly": float(request.form.get('cost_monthly')) if request.form.get('cost_monthly') else 0.0,
            "currency": request.form.get('currency'),
            "billing_cycle": request.form.get('billing_cycle'),
            "next_payment_date": request.form.get('next_payment_date'),
            "auto_renewal": 'auto_renewal' in request.form,
            "payment_method": request.form.get('payment_method'),
            "notes": request.form.get('subscription_notes')
        }
        
        # Обновление личного кабинета
        if 'personal_cabinet' not in service or not isinstance(service.get('personal_cabinet'), dict):
            service['personal_cabinet'] = {}
        service['personal_cabinet']['dashboard_url'] = request.form.get('dashboard_url')
        service['personal_cabinet']['account_email'] = encrypt_data(request.form.get('account_email'))
        
        service['features'] = [f.strip() for f in request.form.get('features', '').split(',') if f.strip()]
        service['status'] = request.form.get('status')
        service['notes'] = request.form.get('notes')
        service['updated_at'] = datetime.now().isoformat()
        
        # Градиент
        service['gradient_color'] = request.form.get('gradient_color', '#667eea')
        
        # Автоматическая генерация градиента
        base_rgb = [
            int(service['gradient_color'][1:3], 16),
            int(service['gradient_color'][3:5], 16),
            int(service['gradient_color'][5:7], 16)
        ]
        
        # Создаем более темный оттенок
        darker_rgb = [
            max(0, min(255, int(base_rgb[0] * 0.7))),
            max(0, min(255, int(base_rgb[1] * 0.7))),
            max(0, min(255, int(base_rgb[2] * 0.7)))
        ]
        
        # Преобразуем в hex
        gradient_color2 = '#{:02x}{:02x}{:02x}'.format(darker_rgb[0], darker_rgb[1], darker_rgb[2])
        
        service['gradient_color1'] = service['gradient_color']
        service['gradient_color2'] = gradient_color2
        service['gradient_css'] = f"linear-gradient(135deg, {service['gradient_color1']} 0%, {service['gradient_color2']} 100%)"
        
        # Обработка иконки
        if 'icon_filename' in request.files:
            file = request.files['icon_filename']
            if file and file.filename != '':
                # Удаляем старую иконку
                if service.get('icon_filename'):
                    try:
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], service['icon_filename']))
                    except OSError:
                        pass # Игнорируем, если файла нет
                
                filename = secure_filename(file.filename)
                unique_filename = f"{service['id']}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                service['icon_filename'] = unique_filename

        save_ai_services(services)
        flash('AI-сервис успешно обновлен!', 'success')
        return redirect(url_for('index', highlight_id=service['id']))

    # Для GET запроса
    # Загружаем схему для динамического формирования полей формы
    try:
        schema_path = 'ai_services_schema.json'
        if getattr(sys, 'frozen', False):
             schema_path = os.path.join(sys._MEIPASS, schema_path)
        print(f"🔍 Попытка загрузки схемы: {schema_path}")
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        print(f"✅ Схема загружена: {len(schema)} ключей")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"⚠️ Ошибка загрузки схемы: {e}")
        print(f"🔧 Создание схемы по умолчанию...")
        try:
            create_default_schema()
            # Пробуем загрузить из текущей директории
            with open('ai_services_schema.json', 'r', encoding='utf-8') as f:
                schema = json.load(f)
                print(f"✅ Схема по умолчанию загружена")
        except Exception as e2:
            print(f"❌ Ошибка создания схемы по умолчанию: {e2}")
            # Используем схему по умолчанию в коде
            schema = {
                "service_types": [
                    "AI Development Tool", 
                    "AI Writing Assistant", 
                    "AI Image Generator", 
                    "AI Video Generator", 
                    "Media Platform", 
                    "Professional Network", 
                    "Cloud Service", 
                    "Productivity Tool"
                ],
                "supported_currencies": ["USD", "EUR", "RUB", "GBP"],
                "billing_cycles": ["weekly", "monthly", "quarterly", "yearly"],
                "status_options": ["active", "inactive", "trial", "expired", "cancelled"]
            }
            print(f"✅ Использована встроенная схема")
    
    return render_template('edit_service.html', service=decrypted_service, schema=schema)

@app.route('/service/<service_id>/receipts/add', methods=['POST'])
def add_receipt(service_id):
    services = load_ai_services()
    # Приводим service_id к int для корректного сравнения с данными
    try:
        service_id_int = int(service_id)
    except ValueError:
        return jsonify({'error': 'Неверный ID сервиса'}), 400
    
    service = next((s for s in services if s['id'] == service_id_int), None)
    
    if service is None:
        return jsonify({'error': 'Сервис не найден'}), 404

    if 'receipt_file' not in request.files:
        return jsonify({"error": "Файл чека отсутствует"}), 400
    
    file = request.files['receipt_file']
    description = request.form.get('description', 'Чек')

    if file and file.filename != '' and allowed_file(file.filename):
        original_filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_filename = f"{service_id}_{timestamp}_{original_filename}"
        
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
        
        if 'payment_info' not in service: service['payment_info'] = {}
        if 'receipts' not in service['payment_info']: service['payment_info']['receipts'] = []
            
        new_receipt = {
            'filename': unique_filename,
            'original_name': original_filename,
            'description': description,
            'upload_date': datetime.now().isoformat()
        }
        service['payment_info']['receipts'].append(new_receipt)
        
        save_ai_services(services)
        
        # Возвращаем добавленный чек с отформатированной датой для UI
        new_receipt['formatted_date'] = datetime.fromisoformat(new_receipt['upload_date']).strftime('%Y-%m-%d %H:%M')
        return jsonify(new_receipt)
    
    return jsonify({"error": "Недопустимый файл"}), 400

@app.route('/service/<service_id>/receipts/delete/<path:filename>', methods=['POST'])
def delete_receipt(service_id, filename):
    services = load_ai_services()
    # Приводим service_id к int для корректного сравнения с данными
    try:
        service_id_int = int(service_id)
    except ValueError:
        return jsonify({'error': 'Неверный ID сервиса'}), 400
    
    service = next((s for s in services if s['id'] == service_id_int), None)
    
    if service is None:
        return jsonify({'error': 'Сервис не найден'}), 404

    receipts = service.get('payment_info', {}).get('receipts', [])
    receipt_to_delete = next((r for r in receipts if r.get('filename') == filename), None)
    
    if not receipt_to_delete:
        return jsonify({"error": "Чек не найден"}), 404

    # Удаляем файл с диска
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            os.remove(filepath)
    except OSError as e:
        print(f"Ошибка удаления файла {filepath}: {e}") # Логгируем, но не останавливаем процесс

    # Удаляем запись из JSON
    service['payment_info']['receipts'].remove(receipt_to_delete)
    save_ai_services(services)
    
    return jsonify({"success": True, "message": "Чек удален"})





@app.route('/help')
@yubikey_auth.require_auth if yubikey_auth else (lambda f: f)
def help_page():
    """Отображает страницу справки с содержимым TERMINAL_HELP.md."""
    return render_template('help.html')

@app.route('/about')
@yubikey_auth.require_auth if yubikey_auth else (lambda f: f)
def about_page():
    app_info = app.config.get('app_info', {})
    return render_template('about.html', app_info=app_info)


@app.route('/settings')
@yubikey_auth.require_auth if yubikey_auth else (lambda f: f)
def settings_page():
    """Отображает страницу управления данными."""
    return render_template('settings.html')

@app.route('/data/export')
@yubikey_auth.require_auth if yubikey_auth else (lambda f: f)
def export_data():
    """Отдает текущий активный файл данных для скачивания."""
    active_file = get_active_data_path()
    if not active_file or not os.path.exists(active_file):
        flash('Нет активного файла данных для экспорта.', 'warning')
        return redirect('/settings')
    
    # Для PyWebView создаем копию файла в папке Downloads для удобного доступа
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_filename = f"ai_services_export_{timestamp}.enc"
        export_dir = get_export_dir()
        export_path = os.path.join(export_dir, export_filename)
        
        # Копируем файл в папку Downloads
        import shutil
        shutil.copy2(active_file, export_path)
        
        flash(f'✅ Файл данных экспортирован как: {export_filename} в папку Downloads', 'success')
        
        return send_from_directory(
                export_dir, 
            export_filename, 
        as_attachment=True
    )
    except Exception as e:
        flash(f'Ошибка при экспорте: {str(e)}', 'danger')
        return redirect('/settings')

@app.route('/data/export_key')
@yubikey_auth.require_auth if yubikey_auth else (lambda f: f)
def export_key():
    """Экспортирует SECRET_KEY в виде .env файла для скачивания."""
    try:
        # Создаем .env файл в папке Downloads
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        key_filename = f"SECRET_KEY_{timestamp}.env"
        export_dir = get_export_dir()
        key_path = os.path.join(export_dir, key_filename)
        
        with open(key_path, 'w', encoding='utf-8') as f:
            f.write(f"SECRET_KEY={SECRET_KEY}\n")
            f.write(f"FLASK_SECRET_KEY=portable_app_key\n")
        
        flash(f'✅ Ключ шифрования экспортирован как: {key_filename} в папку Downloads', 'success')
        
        return send_from_directory(
            export_dir,
            key_filename,
            as_attachment=True
        )
    except Exception as e:
        flash(f'Ошибка при экспорте ключа: {str(e)}', 'danger')
        return redirect('/settings')

@app.route('/data/export_package')
@yubikey_auth.require_auth if yubikey_auth else (lambda f: f)
def export_package():
    """Создает ZIP архив с данными, ключом и загруженными файлами."""
    try:
        import zipfile
        
        # Проверяем наличие активного файла данных
        active_file = get_active_data_path()
        if not active_file or not os.path.exists(active_file):
            flash('Нет активного файла данных для экспорта.', 'warning')
            return redirect('/settings')
        
        # Создаем ZIP файл в папке Downloads
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f'ai_services_backup_{timestamp}.zip'
        export_dir = get_export_dir()
        zip_path = os.path.join(export_dir, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Добавляем файл данных сервера
            zipf.write(active_file, f"servers_{timestamp}.enc")
            
            # Создаем и добавляем файл с ключом
            env_content = f"SECRET_KEY={SECRET_KEY}\nFLASK_SECRET_KEY=portable_app_key\n"
            zipf.writestr("SECRET_KEY.env", env_content)
            
            # Добавляем загруженные файлы (если они есть)
            uploads_dir = os.path.join(get_app_data_dir(), "uploads")
            if os.path.exists(uploads_dir):
                for filename in os.listdir(uploads_dir):
                    file_path = os.path.join(uploads_dir, filename)
                    if os.path.isfile(file_path):
                        zipf.write(file_path, f"uploads/{filename}")
            
            # Добавляем README с инструкциями
            readme_content = f"""AI Manager - Экспорт данных
===========================================

Дата экспорта: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}

Содержимое архива:
- servers_{timestamp}.enc - Зашифрованные данные AI-сервисов
- SECRET_KEY.env - Ключ шифрования (поместите в папку с приложением)
- uploads/ - Загруженные файлы (иконки, документы и т.д.)

Инструкция по импорту:
1. Скопируйте SECRET_KEY.env в папку с новой установкой AI Manager
2. Переименуйте SECRET_KEY.env в .env
3. Перезапустите приложение
4. В разделе "Настройки" -> "Управление данными" импортируйте файл servers_{timestamp}.enc
5. Скопируйте содержимое папки uploads/ в папку uploads/ новой установки

ВАЖНО: Храните этот архив в безопасном месте. Любой, кто имеет доступ к нему,
может расшифровать ваши данные о AI-сервисах!
"""
            zipf.writestr("README.txt", readme_content)
        
        flash(f'✅ Полный архив создан как: {zip_filename} в папке Downloads', 'success')
        
        # Отправляем ZIP файл
        return send_from_directory(
            export_dir,
            zip_filename,
            as_attachment=True
        )
        
    except Exception as e:
        flash(f'Ошибка при создании архива: {str(e)}', 'danger')
        return redirect('/settings')

@app.route('/data/import', methods=['POST'])
def import_data():
    global app_config
    try:
        uploaded_file = request.files['data_file']
        if uploaded_file and allowed_file(uploaded_file.filename) and uploaded_file.filename.endswith('.enc'):
            # Создаем уникальное имя файла с временной меткой
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"imported_{timestamp}_{secure_filename(uploaded_file.filename)}"
            
            # Получаем директорию для хранения данных
            app_data_dir = get_app_data_dir()
            data_dir = os.path.join(app_data_dir, "data")
            
            # Убедимся, что директория существует
            os.makedirs(data_dir, exist_ok=True)
            
            file_path = os.path.join(data_dir, filename)
            uploaded_file.save(file_path)
            
            # Проверяем, что файл действительно зашифрован и может быть прочитан с нашим ключом
            try:
                with open(file_path, 'rb') as f:
                    encrypted_data = f.read()
                
                # Расшифровываем файл с текущим ключом
                decrypted_data = fernet.decrypt(encrypted_data)
                servers_data = json.loads(decrypted_data.decode('utf-8'))
                
                # КРИТИЧЕСКИ ВАЖНО: Если файл уже зашифрован текущим ключом,
                # но содержит поля, зашифрованные другим ключом - перешифровываем их
                # (это может случиться при смене ключа и последующем импорте)
                reencrypted_servers_data = []
                for server in servers_data:
                    # Пытаемся перешифровать каждый сервис (если нужно)
                    # Используем тот же ключ для external и current - если поля уже
                    # зашифрованы текущим ключом, функция их не изменит
                    reencrypted_server = re_encrypt_service_data(server, fernet, fernet)
                    reencrypted_servers_data.append(reencrypted_server)
                
                # Сохраняем перешифрованные данные обратно в файл
                json_string = json.dumps(reencrypted_servers_data, ensure_ascii=False, indent=2)
                encrypted_data = fernet.encrypt(json_string.encode('utf-8'))
                with open(file_path, 'wb') as f:
                    f.write(encrypted_data)
                
                flash('Файл данных успешно импортирован и прикреплен!', 'success')
            except (InvalidToken, json.JSONDecodeError, Exception) as e:
                # Удаляем файл, если он не может быть расшифрован
                os.remove(file_path)
                flash('Ошибка: файл не может быть расшифрован или поврежден. Возможно, он создан с другим ключом.', 'danger')
                return redirect('/settings')
            
            # Обновляем конфигурацию для использования нового файла
            app.config['active_data_file'] = file_path
            save_app_config()
            return redirect('/settings')
        else:
            flash('Неверный тип файла. Пожалуйста, выберите файл .enc', 'danger')
    except Exception as e:
        flash(f'Ошибка при импорте файла: {str(e)}', 'danger')
    return redirect('/settings')

@app.route('/data/import_external', methods=['POST'])
def import_external_data():
    global app_config
    try:
        uploaded_file = request.files['external_file']
        external_key = request.form.get('external_key', '').strip()
        
        if not uploaded_file or not external_key:
            flash('Необходимо выбрать файл и указать внешний ключ шифрования.', 'danger')
            return redirect('/settings')
            
        if not uploaded_file.filename.endswith('.enc'):
            flash('Неверный тип файла. Пожалуйста, выберите файл .enc', 'danger')
            return redirect('/settings')
        
        # Проверяем формат ключа (должен быть в формате Fernet)
        try:
            # Попытаемся создать экземпляр Fernet с предоставленным ключом
            # Это лучше, чем проверка префикса, так как ключи могут иметь разные префиксы
            test_fernet = Fernet(external_key.encode())
        except Exception:
            flash('Неверный формат ключа шифрования. Ключ должен быть действительным ключом Fernet.', 'danger')
            return redirect('/settings')
        
        # Создаем временный файл для проверки
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            uploaded_file.save(temp_file.name)
            temp_file_path = temp_file.name
        
        try:
            # Пытаемся расшифровать файл с внешним ключом
            fernet_external = Fernet(external_key.encode())
            with open(temp_file_path, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = fernet_external.decrypt(encrypted_data)
            servers_data = json.loads(decrypted_data.decode('utf-8'))
            
            # Проверяем структуру данных
            if not isinstance(servers_data, list):
                raise ValueError("Неверная структура данных")
            
            # Данные корректны, теперь перешифровываем их с текущим ключом
            # и объединяем с текущими данными
            current_servers = []
            current_file = get_active_data_path()
            
            # Загружаем текущие данные, если файл существует
            if current_file and os.path.exists(current_file):
                try:
                    with open(current_file, 'rb') as f:
                        current_encrypted = f.read()
                    # decrypt_data ожидает строку, поэтому декодируем bytes в строку
                    current_decrypted = fernet.decrypt(current_encrypted).decode('utf-8')
                    current_servers = json.loads(current_decrypted)
                except Exception:
                    current_servers = []
            
            # КРИТИЧЕСКИ ВАЖНО: Перешифровываем все импортированные сервисы с текущим ключом
            reencrypted_servers_data = []
            for server in servers_data:
                reencrypted_server = re_encrypt_service_data(server, fernet_external, fernet)
                reencrypted_servers_data.append(reencrypted_server)
            
            # Заменяем servers_data на перешифрованные данные
            servers_data = reencrypted_servers_data
            
            # Получаем списки существующих IP адресов и имен для предотвращения дублей
            existing_ips = {server.get('ip', '') for server in current_servers if server.get('ip')}
            existing_names = {server.get('name', '') for server in current_servers if server.get('name')}
            
            # Находим максимальный ID среди существующих серверов
            max_id = 0
            for server in current_servers:
                if 'id' in server and isinstance(server['id'], int):
                    max_id = max(max_id, server['id'])
            
            # Фильтруем импортируемые сервера и присваиваем новые ID
            new_servers = []
            skipped_count = 0
            for server in servers_data:
                server_ip = server.get('ip', '')
                server_name = server.get('name', '')
                
                # Проверяем на дублирование по IP или имени
                if server_ip in existing_ips or server_name in existing_names:
                    skipped_count += 1
                    continue
                
                # Присваиваем новый уникальный ID
                max_id += 1
                server['id'] = max_id
                new_servers.append(server)
                
                # Добавляем в списки для отслеживания дублей
                if server_ip:
                    existing_ips.add(server_ip)
                if server_name:
                    existing_names.add(server_name)
            
            # Объединяем данные
            combined_servers = current_servers + new_servers
            
            # Создаем новый файл с объединенными данными
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ai_services_merged_{timestamp}.enc"
            
            app_data_dir = get_app_data_dir()
            data_dir = os.path.join(app_data_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            
            file_path = os.path.join(data_dir, filename)
            
            # Шифруем объединенные данные нашим ключом
            json_string = json.dumps(combined_servers, ensure_ascii=False, indent=2)
            encrypted_with_our_key = fernet.encrypt(json_string.encode('utf-8'))
            with open(file_path, 'wb') as f:
                f.write(encrypted_with_our_key)
            
            # Обновляем конфигурацию
            app.config['active_data_file'] = file_path
            save_app_config()
            
            # Информируем пользователя о результате
            if new_servers:
                message = f'Успешно импортировано {len(new_servers)} новых серверов!'
                if skipped_count > 0:
                    message += f' Пропущено {skipped_count} дублирующихся серверов.'
                flash(message, 'success')
            else:
                flash('Все сервера из импортируемого файла уже существуют в вашем списке.', 'info')
            
        except InvalidToken:
            flash('Ошибка: неверный ключ шифрования. Проверьте правильность введенного ключа.', 'danger')
        except json.JSONDecodeError:
            flash('Ошибка: файл содержит некорректные данные.', 'danger')
        except Exception as e:
            flash(f'Ошибка при импорте: {str(e)}', 'danger')
        finally:
            # Удаляем временный файл
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
    except Exception as e:
        flash(f'Ошибка при обработке файла: {str(e)}', 'danger')
    
    return redirect('/settings')

@app.route('/data/detach', methods=['POST'])
def detach_data():
    """Открепляет текущий файл данных."""
    if app.config.get('active_data_file'):
        app.config['active_data_file'] = None
        save_app_config()
        flash('Файл данных успешно откреплен.', 'info')
    
    return redirect('/')


@app.route('/check_ip/<ip_address>')
def check_ip(ip_address):
    try:
        ip_check_url = app.config.get('service_urls', {}).get('ip_check_api', 'https://ipinfo.io/{ip}/json').format(ip=ip_address)
        response = requests.get(ip_check_url, timeout=5)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": f"Ошибка запроса: статус {response.status_code}"}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Не удалось подключиться к сервису: {e}"}), 500

@app.route('/settings/change-key', methods=['POST'])
@yubikey_auth.require_auth if yubikey_auth else (lambda f: f)
def change_main_key():
    """Смена главного ключа с перешифровкой всех данных."""
    global SECRET_KEY, fernet  # Добавляем объявление глобальных переменных
    
    try:
        new_key = request.form.get('new_key', '').strip()
        confirm_key = request.form.get('confirm_key', '').strip()
        
        # Проверяем, что ключи совпадают
        if new_key != confirm_key:
            flash('Ошибка: ключи не совпадают.', 'danger')
            return redirect('/settings')
        
        # Проверяем формат нового ключа
        if not new_key:
            flash('Ошибка: новый ключ не может быть пустым.', 'danger')
            return redirect('/settings')
            
        try:
            # Проверяем, что новый ключ корректный для Fernet
            test_fernet = Fernet(new_key.encode())
        except Exception:
            flash('Ошибка: некорректный формат ключа. Ключ должен быть в формате Fernet.', 'danger')
            return redirect('/settings')
        
        # Загружаем текущие данные с существующим ключом
        current_servers = load_ai_services()
        current_servers = [re_encrypt_service_data(item, fernet, test_fernet) for item in current_servers]
        def remove_display_fields(value):
            if isinstance(value, dict):
                return {k: remove_display_fields(v) for k, v in value.items() if not k.endswith('_decrypted')}
            if isinstance(value, list):
                return [remove_display_fields(v) for v in value]
            return value
        current_servers = remove_display_fields(current_servers)
        
        # Создаем резервную копию с временной меткой
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_before_key_change_{timestamp}.enc"
        
        app_data_dir = get_app_data_dir()
        data_dir = os.path.join(app_data_dir, "data")
        backup_path = os.path.join(data_dir, backup_filename)
        
        # Создаем резервную копию
        if app.config.get('active_data_file') and os.path.exists(app.config['active_data_file']):
            shutil.copy2(app.config['active_data_file'], backup_path)
        
        # Сохраняем старые значения для отката в случае ошибки
        old_key = os.environ.get('SECRET_KEY')
        old_secret_key = SECRET_KEY
        old_fernet = fernet
        
        # Устанавливаем новый ключ в переменную окружения
        os.environ['SECRET_KEY'] = new_key
        
        # Обновляем файл .env в правильной директории
        is_frozen = getattr(sys, 'frozen', False)
        if is_frozen:
            # В упакованном приложении сохраняем .env в пользовательской директории данных
            app_data_dir = get_app_data_dir()
            env_file = os.path.join(app_data_dir, '.env')
        else:
            # В режиме разработки сохраняем в корне проекта
                env_file = '.env'
        
        env_lines = []
        
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                env_lines = f.readlines()
        
        # Обновляем или добавляем SECRET_KEY
        key_updated = False
        for i, line in enumerate(env_lines):
            if line.startswith('SECRET_KEY='):
                env_lines[i] = f'SECRET_KEY={new_key}\n'
                key_updated = True
                break
        
        if not key_updated:
            env_lines.append(f'SECRET_KEY={new_key}\n')
        
        try:
            with open(env_file, 'w') as f:
                f.writelines(env_lines)
        except PermissionError:
            # Если не можем записать в основной файл, попробуем в пользовательской директории
            app_data_dir = get_app_data_dir()
            fallback_env_file = os.path.join(app_data_dir, '.env')
            with open(fallback_env_file, 'w') as f:
                f.writelines(env_lines)
        
        # Создаем новый зашифрованный файл с новым ключом
        new_filename = f"ai_services_reencrypted_{timestamp}.enc"
        new_file_path = os.path.join(data_dir, new_filename)
        
        try:
            # Обновляем глобальные переменные СНАЧАЛА
            SECRET_KEY = new_key
            os.environ['SECRET_KEY'] = new_key
            fernet = Fernet(new_key.encode())
            
            # Перешифровываем данные с новым ключом
            with open(new_file_path, 'wb') as f:
                f.write(encrypt_data(json.dumps(current_servers)).encode())
            
            # Обновляем конфигурацию приложения
            app.config['active_data_file'] = new_file_path
            save_app_config()
            
            flash(f'✅ Ключ успешно изменен! Создан новый файл данных: {new_filename}. Резервная копия сохранена как: {backup_filename}', 'success')
            
        except Exception as e:
            # Откатываем ВСЕ изменения в случае ошибки
            os.environ['SECRET_KEY'] = old_key
            SECRET_KEY = old_secret_key
            fernet = old_fernet
            
            # Восстанавливаем старый .env файл
            old_env_lines = []
            for line in env_lines:
                if line.startswith('SECRET_KEY='):
                    old_env_lines.append(f'SECRET_KEY={old_key}\n')
                else:
                    old_env_lines.append(line)
            
            try:
                with open(env_file, 'w') as f:
                    f.writelines(old_env_lines)
            except PermissionError:
                # Если не можем записать в основной файл, попробуем в пользовательской директории
                app_data_dir = get_app_data_dir()
                fallback_env_file = os.path.join(app_data_dir, '.env')
                with open(fallback_env_file, 'w') as f:
                    f.writelines(old_env_lines)
            
            flash(f'Ошибка при перешифровке данных: {str(e)}. Изменения отменены.', 'danger')
            
    except Exception as e:
        flash(f'Ошибка при смене ключа: {str(e)}', 'danger')
    
    return redirect('/settings')

@app.route('/settings/verify-key-data', methods=['POST'])
@yubikey_auth.require_auth if yubikey_auth else (lambda f: f)
def verify_key_data():
    """Проверка соответствия ключа и данных без импорта."""
    try:
        uploaded_file = request.files.get('verify_file')
        test_key = request.form.get('verify_key', '').strip()
        
        if not uploaded_file or not test_key:
            flash('Необходимо выбрать файл и указать ключ для проверки.', 'danger')
            return redirect('/settings')
        
        if not uploaded_file.filename.endswith('.enc'):
            flash('Неверный тип файла. Выберите файл .enc', 'danger')
            return redirect('/settings')
        
        # Проверяем формат ключа
        try:
            test_fernet = Fernet(test_key.encode())
        except Exception:
            flash('❌ Некорректный формат ключа Fernet.', 'danger')
            return redirect('/settings')
        
        # Читаем файл
        file_content = uploaded_file.read()
        
        try:
            # Пытаемся расшифровать
            decrypted_data = test_fernet.decrypt(file_content).decode()
            data = json.loads(decrypted_data)
            
            # Анализируем содержимое
            if isinstance(data, list):
                server_count = len(data)
                
                # Собираем информацию о серверах
                providers = set()
                server_names = []
                
                for server in data:
                    if isinstance(server, dict):
                        if 'provider' in server:
                            providers.add(server['provider'])
                        if 'name' in server:
                            server_names.append(server['name'])
                
                provider_list = ', '.join(sorted(providers)) if providers else 'Не указано'
                name_preview = ', '.join(server_names[:3])
                if len(server_names) > 3:
                    name_preview += f' и еще {len(server_names) - 3}'
                
                flash(f'✅ Ключ подходит! Найдено серверов: {server_count}. Провайдеры: {provider_list}. Серверы: {name_preview}', 'success')
            else:
                flash('✅ Ключ подходит, но структура данных неожиданная.', 'warning')
                
        except InvalidToken:
            flash('❌ Ключ не подходит к этому файлу данных.', 'danger')
        except json.JSONDecodeError:
            flash('❌ Файл расшифрован, но содержит некорректные JSON данные.', 'danger')
        except Exception as e:
            flash(f'❌ Ошибка при проверке: {str(e)}', 'danger')
            
    except Exception as e:
        flash(f'Ошибка при обработке файла: {str(e)}', 'danger')
    
    return redirect('/settings')

@app.route('/settings/generate-key', methods=['POST'])
@yubikey_auth.require_auth if yubikey_auth else (lambda f: f)
def generate_new_key():
    """Генерация нового случайного ключа Fernet."""
    try:
        new_key = Fernet.generate_key().decode()
        return jsonify({'success': True, 'key': new_key})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/shutdown')
def shutdown():
    os.kill(os.getpid(), signal.SIGINT)
    return 'Сервер выключается...'

@app.route('/clipboard', methods=['POST'])
def set_clipboard():
    try:
        payload = request.get_json(silent=True) or {}
        text = payload.get('text', '')
        if sys.platform == 'darwin':
            try:
                pbcopy_path = '/usr/bin/pbcopy'
                args = [pbcopy_path] if os.path.exists(pbcopy_path) else ['pbcopy']
                proc = subprocess.Popen(args, stdin=subprocess.PIPE)
                proc.communicate(input=(text or '').encode('utf-8'))
                if proc.returncode == 0:
                    return jsonify({'success': True})
                osa_script = f'set the clipboard to {json.dumps(text or "")}'
                rc = subprocess.call(['/usr/bin/osascript', '-e', osa_script])
                return jsonify({'success': rc == 0})
            except Exception:
                try:
                    osa_script = f'set the clipboard to {json.dumps(text or "")}'
                    rc = subprocess.call(['/usr/bin/osascript', '-e', osa_script])
                    return jsonify({'success': rc == 0})
                except Exception as e2:
                    return jsonify({'success': False, 'error': str(e2)}), 500
        else:
            try:
                import pyperclip
                pyperclip.copy(text or '')
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def _is_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(('127.0.0.1', port))
            return True
        except OSError:
            return False

# --- Надёжный запуск сервера на свободном порте (без конфликтов) ---
SERVER_PORT = None
_WSGI_SERVER = None


def _start_flask_server():
    global SERVER_PORT, _WSGI_SERVER
    try:
        _WSGI_SERVER = make_server('127.0.0.1', 0, app)
        SERVER_PORT = _WSGI_SERVER.server_port
        print(f"🚀 Flask сервер запущен на http://127.0.0.1:{SERVER_PORT}")
        _WSGI_SERVER.serve_forever()
    except Exception as e:
        print(f"❌ Ошибка запуска Flask сервера: {e}")
        import traceback
        traceback.print_exc()

def create_default_schema():
    """
    Создает базовую схему данных, если она отсутствует
    """
    default_schema = {
        "service_types": [
            "AI Development Tool", 
            "AI Writing Assistant", 
            "AI Image Generator", 
            "AI Video Generator", 
            "Media Platform", 
            "Professional Network", 
            "Cloud Service", 
            "Productivity Tool"
        ],
        "supported_currencies": ["USD", "EUR", "RUB", "GBP"],
        "billing_cycles": ["weekly", "monthly", "quarterly", "yearly"],
        "status_options": ["active", "inactive", "trial", "expired", "cancelled"]
    }
    
    try:
        with open('ai_services_schema.json', 'w', encoding='utf-8') as f:
            json.dump(default_schema, f, indent=2, ensure_ascii=False)
        print("✅ Создана базовая схема данных")
    except Exception as e:
        print(f"❌ Ошибка создания схемы данных: {e}")

# Вызываем создание схемы при старте приложения
if not is_frozen and not Path('ai_services_schema.json').exists():
    create_default_schema()

# Добавляем фильтры и тесты для Jinja2
def regex_replace(s, find, replace):
    """A non-optimal implementation of a regex replace."""
    return re.sub(find, replace, s)

def regex_search(pattern, string):
    """Check if the pattern matches the string."""
    return re.search(pattern, string) is not None

# Регистрация фильтров и тестов
app.jinja_env.filters['regex_replace'] = regex_replace
app.jinja_env.tests['regex_search'] = regex_search

@app.route('/yubikey/login', methods=['GET', 'POST'])
def yubikey_login():
    """Обработчик входа YubiKey с улучшенной обработкой ошибок"""
    try:
        print(f"🔍 yubikey_login: method={request.method}, yubikey_auth={yubikey_auth is not None}")
        
        # Проверяем статус сети для передачи в шаблон
        is_online = check_internet_connection()
        
        # Если YubiKey включен, но ключи не настроены, направляем в настройки
        try:
            if yubikey_auth and yubikey_auth.enabled and len(yubikey_auth.get_keys()) == 0:
                flash('YubiKey ключи не настроены. Укажите Client ID и Secret Key в разделе «Настройки».', 'warning')
                return redirect('/settings')
        except Exception:
            pass
        
        if request.method == 'POST':
            otp = request.form.get('otp', '').strip()
            print(f"🔍 Проверка OTP: {otp[:10]}... (длина: {len(otp)})")
            
            if not otp:
                print("⚠️ OTP не предоставлен")
                flash('Введите OTP от YubiKey', 'danger')
                return render_template('yubikey_login.html', is_online=is_online)
                
            try:
                if yubikey_auth:
                    success, message = yubikey_auth.verify_otp(otp)
                    if success:
                        session['yubikey_authenticated'] = True
                        print("✅ YubiKey аутентификация успешна")
                        flash('Аутентификация YubiKey успешна!', 'success')
                        return redirect('/')
                    else:
                        print(f"❌ YubiKey аутентификация неуспешна: {message}")
                        flash(f'Неверный OTP: {message}', 'danger')
                else:
                    print("❌ YubiKey модуль не инициализирован")
                    flash('YubiKey модуль не доступен', 'danger')
            except Exception as e:
                print(f"❌ Ошибка при проверке OTP: {e}")
                import traceback
                traceback.print_exc()
                flash(f'Ошибка при проверке OTP: {e}', 'error')
        
        print("✅ Рендеринг страницы входа YubiKey")
        try:
            is_dev = bool(os.getenv('FLASK_ENV') == 'development' or app.debug)
        except Exception:
            is_dev = False
        allowed_ids = []
        try:
            if yubikey_auth and hasattr(yubikey_auth, 'allowed_public_ids'):
                allowed_ids = sorted(list(yubikey_auth.allowed_public_ids))
        except Exception:
            allowed_ids = []
        return render_template('yubikey_login.html', is_online=is_online, is_dev=is_dev, allowed_public_ids=allowed_ids)
        
    except Exception as e:
        print(f"❌ Критическая ошибка в yubikey_login: {e}")
        import traceback
        traceback.print_exc()
        flash('Произошла ошибка при обработке запроса', 'error')
        try:
            is_dev = bool(os.getenv('FLASK_ENV') == 'development' or app.debug)
        except Exception:
            is_dev = False
        allowed_ids = []
        try:
            if yubikey_auth and hasattr(yubikey_auth, 'allowed_public_ids'):
                allowed_ids = sorted(list(yubikey_auth.allowed_public_ids))
        except Exception:
            allowed_ids = []
        return render_template('yubikey_login.html', is_online=check_internet_connection(), is_dev=is_dev, allowed_public_ids=allowed_ids)

@app.route('/yubikey/logout')
def yubikey_logout():
    session.pop('yubikey_authenticated', None)
    flash('Вы вышли из системы', 'info')
    return redirect('/yubikey/login')

@app.route('/yubikey/setup', methods=['GET', 'POST'])
def yubikey_setup():
    if not yubikey_auth:
        flash('YubiKey модуль не доступен', 'danger')
        return redirect('/')
        
    if request.method == 'POST':
        client_id = request.form.get('client_id', '').strip()
        secret_key = request.form.get('secret_key', '').strip()
        key_name = request.form.get('key_name', '').strip()
        public_id_input = request.form.get('public_id', '').strip()
        public_ids = []
        if public_id_input:
            candidates = [p.strip() for p in public_id_input.split(',') if p.strip()]
            try:
                modhex12 = re.compile(r'^[cbdefghijklnrtuv]{12}$')
                public_ids = [p for p in candidates if modhex12.match(p)]
            except Exception:
                public_ids = candidates

        # Ветвь 1: обновление списка разрешённых public id без добавления ключа
        if (not client_id and not secret_key) and public_ids:
            try:
                for pid in public_ids:
                    yubikey_auth.allowed_public_ids.add(pid)
                yubikey_auth.save_config()
                flash('Список разрешённых public id обновлён', 'success')
            except Exception as e:
                flash(f'Ошибка сохранения public id: {e}', 'danger')
        # Ветвь 2: добавление ключа (и при необходимости public id)
        elif client_id and secret_key:
            if yubikey_auth.add_key(client_id, secret_key, key_name, public_ids=public_ids or None):
                try:
                    if public_ids:
                        for pid in public_ids:
                            yubikey_auth.allowed_public_ids.add(pid)
                        yubikey_auth.save_config()
                except Exception:
                    pass
                flash('YubiKey успешно добавлен!', 'success')
            else:
                flash('Ошибка при добавлении ключа', 'danger')
        else:
            flash('Укажите Client ID и Secret Key или только публичный ID(ы) для ограничения доступа', 'warning')
    
    # Передаем данные для отображения
    keys = yubikey_auth.get_keys() if yubikey_auth else []
    return render_template('yubikey_setup.html', yubikey_auth=yubikey_auth, keys=keys)

@app.route('/yubikey/remove/<int:key_index>', methods=['POST'])
def yubikey_remove_key(key_index):
    if yubikey_auth:
        removed_key = yubikey_auth.remove_key(key_index)
        if removed_key:
            flash(f'Ключ "{removed_key["name"]}" удален', 'success')
        else:
            flash('Ошибка при удалении ключа', 'danger')
    return redirect('/yubikey/setup')

@app.route('/yubikey/instructions')
def yubikey_instructions():
    return render_template('yubikey_instructions.html')

# Конфигурация PIN разработчика: env -> config.json -> '1234'
def get_developer_pin() -> str:
    try:
        env_pin = os.getenv('DEV_PIN') or os.getenv('DEVELOPER_PIN')
        if env_pin and str(env_pin).strip():
            return str(env_pin).strip()
        cfg_pin = (app.config.get('security', {}) or {}).get('dev_pin') if isinstance(app.config.get('security'), dict) else None
        if cfg_pin and str(cfg_pin).strip():
            return str(cfg_pin).strip()
    except Exception:
        pass
    return '1234'

@app.route('/dev_login', methods=['POST'])
def dev_login():
    """Скрытый вход для разработчика по PIN (двойной клик по имени разработчика).
    При корректном PIN устанавливает yubikey_authenticated=True в сессии.
    Источник PIN: ENV (DEV_PIN/DEVELOPER_PIN) -> config.json (security.dev_pin) -> '1234'
    """
    try:
        payload = request.get_json(silent=True) or {}
        pin = payload.get('pin') or request.form.get('pin')
        expected = get_developer_pin()
        if str(pin).strip() == expected:
            session['yubikey_authenticated'] = True
            try:
                log_security_event("DEV_LOGIN", "Developer PIN accepted", request.remote_addr)
            except Exception:
                pass
            return jsonify({'success': True})
        else:
            try:
                log_security_event("DEV_LOGIN_FAIL", "Invalid developer PIN", request.remote_addr)
            except Exception:
                pass
            return jsonify({'success': False}), 401
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/secret/login', methods=['POST'])
def secret_login():
    try:
        if not yubikey_auth:
            return jsonify({'success': False, 'message': 'YubiKey модуль не доступен'}), 400
        if yubikey_auth.is_secret_login_blocked():
            remaining = yubikey_auth.get_secret_login_block_remaining()
            return jsonify({'success': False, 'message': f'Блокировка {remaining} сек', 'blocked': True, 'remaining_seconds': remaining}), 429
        pin = request.form.get('pin', '').strip()
        if not pin:
            return jsonify({'success': False, 'message': 'Введите PIN'}), 400
        success, message = yubikey_auth.secret_authenticate(pin)
        if success:
            session['yubikey_authenticated'] = True
        status = 200 if success else 400
        return jsonify({'success': success, 'message': message}), status
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'}), 500

@app.route('/secret/change_pin', methods=['POST'])
def change_secret_pin():
    try:
        if not yubikey_auth:
            return jsonify({'success': False, 'message': 'YubiKey модуль не доступен'}), 400
        old_pin = request.form.get('old_pin', '').strip()
        new1 = request.form.get('new_pin1', '').strip()
        new2 = request.form.get('new_pin2', '').strip()
        if new1 != new2:
            return jsonify({'success': False, 'message': 'Новые PIN-коды не совпадают'})
        if not new1 or len(new1) < 4:
            return jsonify({'success': False, 'message': 'PIN >= 4 символов'})
        success, message = yubikey_auth.change_secret_pin(old_pin, new1)
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'}), 500

if __name__ == "__main__":
    try:
        # Выполняем проверку и миграцию при старте приложения
        print("🔄 Выполнение миграции данных...")
        migrate_data()
        
        # Запускаем Flask в отдельном потоке
        print("🔄 Запуск Flask в отдельном потоке...")
        flask_thread = threading.Thread(target=_start_flask_server)
        flask_thread.daemon = True
        flask_thread.start()
        
        # Ждём, пока сервер поднимется и задаст порт
        for _ in range(100):
            if SERVER_PORT:
                break
            time.sleep(0.05)

        def on_closing():
            print("Окно закрывается, отправка запроса на выключение...")
            try:
                # Отправляем запрос на выключение, чтобы корректно остановить сервер
                requests.get(f'http://127.0.0.1:{SERVER_PORT}/shutdown', timeout=1)
            except requests.exceptions.RequestException:
                # Это нормально, так как сервер умрет до получения ответа
                pass

        # Создаем окно PyWebView
        print("🔄 Создание GUI окна...")
        window = webview.create_window(
            'AllManagerC',
            f'http://127.0.0.1:{SERVER_PORT or 5050}',
            width=1280,
            height=800,
            resizable=True
        )
        window.events.closing += on_closing

        # Запускаем GUI
        print("🚀 Запуск GUI приложения...")
        webview.start(debug=False) # debug=True может помочь с отладкой, если что-то пойдет не так

        # После закрытия окна PyWebView, главный поток продолжится здесь.
        print("Приложение закрыто.")
    except Exception as e:
        print(f"❌ Критическая ошибка при запуске приложения: {e}")
        import traceback
        traceback.print_exc()
        input("Нажмите Enter для выхода...")
