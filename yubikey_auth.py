import json
from pathlib import Path
from flask import session, redirect, url_for, flash, request
from yubico_client import Yubico
from yubico_client.yubico_exceptions import YubicoError, InvalidClientIdError, SignatureVerificationError
from datetime import datetime
import socket
import time
import re

# Кэш результата онлайна, чтобы не дёргать сеть слишком часто
_LAST_ONLINE_TS = 0.0
_LAST_ONLINE_RESULT = False

def check_internet_connection(timeout: float = 0.7, cache_ttl: float = 10.0, retries: int = 2) -> bool:
    """Устойчивый и быстрый детектор онлайна.
    Стратегия:
    - Кэшируем результат на cache_ttl секунд, чтобы избежать миганий UI
    - Прямой TCP (без DNS) к публичным адресам: 1.1.1.1:443, 8.8.8.8:443, 9.9.9.9:443
    - DNS + TCP к api.yubico.com:443 (пробуем несколько A-записей)
    - Онлайн, если (хотя бы один прямой TCP успешен) и (DNS разрешился и хотя бы одна попытка TCP к api.yubico.com успешна)
      В качестве послабления: если прямой TCP успешен и DNS разрешился (но TCP к api.yubico.com не прошёл), считаем онлайн
      чтобы избежать ложных оффлайнов при временных сбоях Yubico.
    """
    global _LAST_ONLINE_TS, _LAST_ONLINE_RESULT
    now = time.time()
    if now - _LAST_ONLINE_TS < cache_ttl:
        return _LAST_ONLINE_RESULT

    def try_connect(host_port_pairs):
        for (h, p) in host_port_pairs:
            for _ in range(max(1, retries)):
                try:
                    with socket.create_connection((h, p), timeout=timeout):
                        return True
                except Exception:
                    continue
        return False

    # 1) Прямой TCP к популярным DNS‑резолверам (без DNS)
    direct_ok = try_connect([("1.1.1.1", 443), ("8.8.8.8", 443), ("9.9.9.9", 443)])

    # 2) DNS + TCP к api.yubico.com (пробуем несколько IP)
    yubico_tcp_ok = False
    dns_ok = False
    try:
        # Получаем несколько адресов
        infos = socket.getaddrinfo("api.yubico.com", 443, proto=socket.IPPROTO_TCP)
        targets = []
        for info in infos:
            addr = info[-1]
            if isinstance(addr, tuple) and len(addr) >= 2:
                targets.append((addr[0], 443))
        dns_ok = len(targets) > 0
        # Пробуем несколько IP
        if targets:
            yubico_tcp_ok = try_connect(targets[:3])
    except Exception:
        dns_ok = False
        yubico_tcp_ok = False

    result = (direct_ok and yubico_tcp_ok) or (direct_ok and dns_ok)
    _LAST_ONLINE_TS, _LAST_ONLINE_RESULT = now, result
    if not result:
        try:
            print(f"🔌 Интернет офлайн/нестабилен: direct_ok={direct_ok}, dns_ok={dns_ok}, yubico_tcp_ok={yubico_tcp_ok}")
        except Exception:
            pass
    return result

class YubiKeyAuth:
    def __init__(self, app_data_dir, static_passwords=None):
        self.config_file = Path(app_data_dir) / 'yubikey_config.json'
        self.keys = []  # Список ключей вместо одного
        self.enabled = False
        self.static_passwords = static_passwords or []
        # Ограничение по публичным ID (модхекс-префикс OTP, обычно 12 символов)
        self.allowed_public_ids = set()
        # Секретный PIN и антибрут-логика (в файле config.json приложения)
        self.app_data_dir = Path(app_data_dir)
        self.app_config_path = self.app_data_dir / 'config.json'
        self.secret_login_attempts = 0
        self.secret_login_blocked_until = 0
        self.secret_login_block_duration = 30  # секунд

        self.load_config()
        # Если заданы статические пароли, включаем защиту даже без онлайн-ключей
        try:
            if self.static_passwords and len(self.static_passwords) > 0:
                self.enabled = True
        except Exception:
            pass
        # Загружаем разрешённые публичные ID из окружения
        try:
            import os
            env_allowed = os.getenv('YUBIKEY_ALLOWED_PUBLIC_IDS')
            if env_allowed:
                for it in env_allowed.split(','):
                    it = (it or '').strip()
                    if it:
                        self.allowed_public_ids.add(it)
        except Exception:
            pass
    
    def load_config(self):
        """Загружает конфигурацию YubiKey с улучшенной обработкой ошибок."""
        try:
            # Убеждаемся, что директория существует
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            if self.config_file.exists():
                try:
                    with open(self.config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        # Поддержка старого формата (один ключ)
                        if 'client_id' in config and 'secret_key' in config:
                            self.keys = [{
                                'client_id': config.get('client_id'),
                                'secret_key': config.get('secret_key'),
                                'name': 'Основной ключ',
                                'created_at': config.get('created_at', '2024-01-01')
                            }]
                        else:
                            # Новый формат (несколько ключей)
                            self.keys = config.get('keys', [])
                            # Глобально заданный список разрешённых public id
                            try:
                                top_allowed = config.get('allowed_public_ids') or []
                                if isinstance(top_allowed, list):
                                    for it in top_allowed:
                                        if isinstance(it, str) and it.strip():
                                            self.allowed_public_ids.add(it.strip())
                            except Exception:
                                pass
                            # Собираем возможные разрешённые публичные ID из ключей
                            for k in self.keys:
                                for fld in ('public_id', 'public_ids'):
                                    v = k.get(fld)
                                    if isinstance(v, str):
                                        self.allowed_public_ids.add(v.strip())
                                    elif isinstance(v, list):
                                        for it in v:
                                            if isinstance(it, str) and it.strip():
                                                self.allowed_public_ids.add(it.strip())
                        self.enabled = config.get('enabled', False)
                        print(f"✅ Конфигурация YubiKey загружена: {len(self.keys)} ключей")
                except json.JSONDecodeError as e:
                    print(f"⚠️ Ошибка парсинга JSON в {self.config_file}: {e}")
                    self.keys = []
                    self.enabled = False
                except Exception as e:
                    print(f"⚠️ Ошибка чтения файла {self.config_file}: {e}")
                    self.keys = []
                    self.enabled = False
            else:
                print(f"📄 Файл конфигурации YubiKey не найден: {self.config_file}")
                # Безопасный режим по умолчанию для дистрибутива: включаем защиту и просим настроить ключи
                self.keys = []
                self.enabled = True
                try:
                    self.save_config()
                    print("🔒 YubiKey включён по умолчанию. Добавьте ключ в Настройках.")
                except Exception:
                    pass
        except Exception as e:
            print(f"❌ Критическая ошибка загрузки YubiKey: {e}")
            self.keys = []
            self.enabled = False
    
    def save_config(self):
        """Сохраняет конфигурацию YubiKey с улучшенной обработкой ошибок."""
        try:
            # Убеждаемся, что директория существует
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            config = {
                'keys': self.keys,
                'enabled': self.enabled,
                'allowed_public_ids': sorted(list(self.allowed_public_ids)) if self.allowed_public_ids else []
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Конфигурация YubiKey сохранена: {len(self.keys)} ключей")
        except Exception as e:
            print(f"❌ Ошибка сохранения YubiKey: {e}")
            raise
    
    def add_key(self, client_id, secret_key, name=None, public_ids=None):
        """Добавляет новый YubiKey. public_ids — список разрешённых публичных ID."""
        if not name:
            name = f"Ключ {len(self.keys) + 1}"
        
        new_key = {
            'client_id': client_id,
            'secret_key': secret_key,
            'name': name,
            'created_at': datetime.now().isoformat()
        }
        if public_ids:
            if isinstance(public_ids, str):
                public_ids = [public_ids]
            new_key['public_ids'] = [pid.strip() for pid in public_ids if isinstance(pid, str) and pid.strip()]
            for pid in new_key.get('public_ids', []):
                self.allowed_public_ids.add(pid)
        
        self.keys.append(new_key)
        self.enabled = True
        self.save_config()
        return True
    
    def remove_key(self, key_index):
        """Удаляет YubiKey по индексу."""
        if 0 <= key_index < len(self.keys):
            removed_key = self.keys.pop(key_index)
            if not self.keys:
                self.enabled = False
            self.save_config()
            return removed_key
        return None
    
    def get_keys(self):
        """Возвращает список всех ключей."""
        return self.keys

    # ====== СЕКРЕТНЫЙ PIN: хранение и антибрут ======
    def _load_app_config(self):
        try:
            if not self.app_config_path.exists():
                return {}
            with open(self.app_config_path, 'r', encoding='utf-8') as f:
                return json.load(f) or {}
        except Exception:
            return {}

    def _save_app_config(self, cfg: dict):
        try:
            self.app_config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.app_config_path, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения config.json: {e}")
            return False

    def get_secret_pin(self) -> str:
        try:
            import os
            env_pin = os.getenv('DEV_PIN') or os.getenv('DEVELOPER_PIN')
            if env_pin and str(env_pin).strip():
                return str(env_pin).strip()
        except Exception:
            pass
        cfg = self._load_app_config()
        sec = cfg.get('security') or {}
        pin = sec.get('secret_pin', {}).get('current_pin') if isinstance(sec.get('secret_pin'), dict) else None
        if not pin:
            # fallback на security.dev_pin или '1234'
            pin = sec.get('dev_pin') or '1234'
        return str(pin)

    def change_secret_pin(self, old_pin: str, new_pin: str):
        try:
            current = self.get_secret_pin()
            if str(old_pin) != str(current):
                return False, 'Старый PIN неверен'
            cfg = self._load_app_config()
            if 'security' not in cfg or not isinstance(cfg.get('security'), dict):
                cfg['security'] = {}
            # Обновляем новую структуру
            cfg['security']['secret_pin'] = {
                'current_pin': str(new_pin),
                'updated_at': datetime.now().isoformat()
            }
            # Удаляем устаревший dev_pin, чтобы не путал
            if 'dev_pin' in cfg['security']:
                cfg['security'].pop('dev_pin', None)
            ok = self._save_app_config(cfg)
            if not ok:
                return False, 'Не удалось сохранить PIN'
            # Сбросить попытки после смены
            self.secret_login_attempts = 0
            self.secret_login_blocked_until = 0
            return True, 'PIN изменён'
        except Exception as e:
            return False, f'Ошибка: {e}'

    def is_secret_login_blocked(self) -> bool:
        try:
            import time
            return time.time() < float(self.secret_login_blocked_until or 0)
        except Exception:
            return False

    def get_secret_login_block_remaining(self) -> int:
        try:
            import time
            remaining = int((self.secret_login_blocked_until or 0) - time.time())
            return max(0, remaining)
        except Exception:
            return 0

    def block_secret_login(self):
        try:
            import time
            self.secret_login_blocked_until = time.time() + int(self.secret_login_block_duration)
        except Exception:
            pass

    def secret_authenticate(self, pin: str):
        try:
            if self.is_secret_login_blocked():
                return False, f"Блокировка {self.get_secret_login_block_remaining()} сек"
            if not pin:
                return False, 'Введите PIN'
            if str(pin).strip() == str(self.get_secret_pin()).strip():
                self.secret_login_attempts = 0
                session['yubikey_authenticated'] = True
                return True, 'Успех'
            # Неверный PIN
            self.secret_login_attempts += 1
            if self.secret_login_attempts >= 3:
                self.block_secret_login()
                self.secret_login_attempts = 0
                return False, 'Слишком много попыток. Временная блокировка.'
            return False, 'Неверный PIN'
        except Exception as e:
            return False, f'Ошибка аутентификации: {e}'

    
    def is_authenticated(self):
        """Проверяет, аутентифицирован ли пользователь с улучшенной обработкой ошибок."""
        try:
            # Проверяем, есть ли активный контекст запроса
            from flask import has_request_context
            if not has_request_context():
                print("⚠️ is_authenticated вызван вне контекста запроса")
                return False
            
            return session.get('yubikey_authenticated', False)
        except Exception as e:
            print(f"⚠️ Ошибка в is_authenticated: {e}")
            return False
    
    def verify_otp(self, otp):
        """Строгая проверка в зависимости от режима.
        Онлайн: только динамический OTP (ModHex 44) через YubiCloud.
        Офлайн: только статические пароли из .env.
        """
        if not otp:
            return False, "OTP не может быть пустым"

        online = check_internet_connection()

        # Онлайн-режим: принимаем только динамический OTP
        if online:
            # Явно отклоняем статические пароли в онлайн-режиме
            if self.static_passwords and otp in self.static_passwords:
                return False, "В онлайн-режиме используйте динамический OTP"

            # Строгая проверка формата для онлайн-ключа (YubiKey OTP): 44 символа ModHex
            if not re.match(r'^[cbdefghijklnrtuv]{44}$', otp):
                return False, "Неверный формат динамического OTP"

            if not self.keys:
                return False, "Онлайн-ключи не настроены"

            status_to_message = {
                'REPLAYED_OTP': "Код уже был использован. Нажмите кнопку ещё раз (сгенерируйте новый).",
                'BAD_OTP': "Неверный одноразовый код. Нажмите кнопку на ключе ещё раз.",
                'NO_SUCH_CLIENT': "Неверный Client ID. Проверьте числовой Client ID.",
                'BAD_SIGNATURE': "Неверный Secret Key. Проверьте Secret Key.",
                'MISSING_PARAMETER': "Отсутствуют параметры запроса.",
                'BACKEND_ERROR': "Сбой на стороне Yubico. Повторите позже.",
                'REPLAYED_REQUEST': "Повтор запроса. Попробуйте ещё раз.",
                'NOT_ENOUGH_ANSWERS': "Недостаточно ответов сервера Yubico.",
                'OPERATION_NOT_ALLOWED': "Операция OTP запрещена для вашего ключа."
            }

            for key_data in self.keys:
                try:
                    client_id = key_data.get('client_id')
                    secret_key = key_data.get('secret_key')
                    if not client_id or not secret_key:
                        continue

                    # Быстрая валидация формата Secret Key (base64)
                    try:
                        import base64, binascii
                        base64.b64decode(str(secret_key).encode('ascii'), validate=True)
                    except (binascii.Error, ValueError, UnicodeError):
                        return False, "Secret Key в настройках некорректен (ожидается base64 из кабинета Yubico)"

                    client = Yubico(client_id, secret_key)
                    response = client.verify(otp, return_response=True)
                    # Расширенная диагностика статуса ответа
                    try:
                        status = getattr(response, 'status', None)
                    except Exception:
                        status = None
                    if status is None and isinstance(response, dict):
                        status = response.get('status')
                    try:
                        print(f"🧪 Yubico response: {getattr(response, 'status', None)} | raw={response}")
                    except Exception:
                        pass

                    if status == 'OK':
                        # Проверка привязки к устройству по публичному ID (первые 12 modhex символов)
                        try:
                            public_id = str(otp)[:12]
                        except Exception:
                            public_id = None
                        if self.allowed_public_ids:
                            if not public_id or public_id not in self.allowed_public_ids:
                                return False, "OTP от непозволенного ключа (public id не в списке разрешённых)"
                        else:
                            # Если список не задан — авто-привязка к первому успешному public id
                            if public_id and len(public_id) == 12:
                                self.allowed_public_ids.add(public_id)
                                try:
                                    self.save_config()
                                    print(f"🔒 Автопривязка к ключу: {public_id}")
                                except Exception:
                                    pass
                        session['yubikey_authenticated'] = True
                        return True, "Онлайн-пароль подтвержден"

                    if status:
                        human_message = status_to_message.get(status, f"Ошибка Yubico: {status}")
                        return False, human_message

                    return False, "Не удалось подтвердить OTP (нет статуса ответа). Проверьте Client ID/Secret Key и повторите."
                except InvalidClientIdError:
                    return False, "Неверный Client ID."
                except SignatureVerificationError:
                    return False, "Неверный Secret Key."
                except YubicoError as e:
                    msg = str(e) or "YubicoError"
                    lower_msg = msg.lower()
                    if 'timeout' in lower_msg or 'timed out' in lower_msg:
                        return False, "Тайм-аут соединения с YubiCloud."
                    if 'network' in lower_msg or 'connection' in lower_msg:
                        return False, "Нет связи с YubiCloud."
                    return False, f"Ошибка Yubico: {msg}"

            return False, "Неверный онлайн OTP"

        # Офлайн-режим: принимаем только статический пароль
        if self.static_passwords and otp in self.static_passwords:
            session['yubikey_authenticated'] = True
            session['offline_auth'] = True
            return True, "Офлайн-пароль подтвержден"

        if self.static_passwords:
            return False, "В офлайн-режиме используйте статический пароль"
        return False, "Статические пароли не настроены"
    
    def require_auth(self, f):
        def decorated(*args, **kwargs):
            try:
                from flask import request
                endpoint = (request.endpoint or '').strip()
            except Exception:
                endpoint = ''

            # Если защита отключена — пропускаем
            if not self.enabled:
                return f(*args, **kwargs)

            # Если ключи ещё не заданы — разрешаем только настройки/мастер
            try:
                if len(self.get_keys()) == 0:
                    if endpoint in ('settings_page', 'yubikey_setup', 'static'):
                        return f(*args, **kwargs)
                    # Убираем флаг аутентификации, чтобы исключить доступ по старой сессии
                    try:
                        session.pop('yubikey_authenticated', None)
                    except Exception:
                        pass
                    return redirect(url_for('yubikey_setup'))
            except Exception:
                pass

            # Во всех остальных случаях требуется аутентификация
            if not self.is_authenticated():
                return redirect(url_for('yubikey_login'))
            return f(*args, **kwargs)
        decorated.__name__ = f.__name__
        return decorated

yubikey_auth = None

def init_yubikey_auth(app_data_dir):
    """Инициализирует YubiKey аутентификацию с улучшенной обработкой ошибок."""
    global yubikey_auth
    try:
        print(f"🔧 Инициализация YubiKey в директории: {app_data_dir}")
        
        # Загружаем статические пароли из переменных окружения
        import os
        import sys
        from dotenv import load_dotenv
        
        # Улучшенная загрузка .env файла для работы в дистрибутиве
        def load_env_file():
            """Загружает .env файл из различных возможных мест."""
            from pathlib import Path
            
            if getattr(sys, 'frozen', False):
                env_path = Path(app_data_dir) / '.env'
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
                elif sys.platform == 'win32':
                    from pathlib import Path as _P
                    possible_paths.append(_P(os.environ.get('APPDATA', str(Path.home()))) / 'AllManagerC' / '.env')
                    possible_paths.append(Path(sys.executable).parent / '.env')
                else:
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
                if env_path.exists():
                    print(f"📁 [yubikey_auth] Найден .env файл: {env_path}")
                    load_dotenv(env_path)
                    return True
            
            print(f"❌ [yubikey_auth] .env файл не найден в следующих местах:")
            for path in possible_paths:
                print(f"   - {path} {'✅' if path.exists() else '❌'}")
            return False
        
        # Загружаем .env файл
        load_env_file()
        static_passwords_str = os.getenv('YUBIKEY_STATIC_PASSWORDS')
        static_passwords = []
        if static_passwords_str:
            static_passwords = [p.strip() for p in static_passwords_str.split(',')]
            print(f"🤫 {len(static_passwords)} статических паролей YubiKey загружено.")

        yubikey_auth = YubiKeyAuth(app_data_dir, static_passwords)
        print(f"✅ YubiKey инициализирован: enabled={yubikey_auth.enabled}, keys={len(yubikey_auth.keys)}")
        return yubikey_auth 
    except Exception as e:
        print(f"❌ Ошибка инициализации YubiKey: {e}")
        return None 