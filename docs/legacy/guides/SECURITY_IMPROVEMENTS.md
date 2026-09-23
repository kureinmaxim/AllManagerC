# 🔒 Улучшения безопасности для AI Manager

## Текущие меры безопасности ✅
- Шифрование данных с помощью Fernet
- Отдельное хранение ключа в .env файле
- Автоматическое создание ключей
- Поддержка смены ключа с перешифровкой

## 🛡️ Дополнительные меры безопасности

### 1. **Двухфакторная аутентификация (2FA)**
```python
# Добавить в app.py
import secrets
import hashlib
import time
from functools import wraps

# Глобальные переменные для 2FA
app.config['REQUIRE_2FA'] = True
app.config['SESSION_TIMEOUT'] = 3600  # 1 час
app.config['MAX_LOGIN_ATTEMPTS'] = 3
app.config['LOGIN_ATTEMPTS'] = {}
app.config['LOCKOUT_TIME'] = 900  # 15 минут блокировки

def generate_2fa_code(secret):
    """Генерирует 6-значный код на основе времени и секрета."""
    timestamp = int(time.time() // 30)  # 30-секундные окна
    message = f"{secret}{timestamp}".encode()
    hash_obj = hashlib.sha256(message).hexdigest()
    return str(int(hash_obj[:6], 16))[-6:].zfill(6)

def require_2fa(f):
    """Декоратор для защиты маршрутов 2FA."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not app.config.get('REQUIRE_2FA', False):
            return f(*args, **kwargs)
        
        if '2fa_verified' not in session:
            return redirect(url_for('login_2fa'))
        
        # Проверяем время сессии
        if time.time() - session.get('2fa_time', 0) > app.config['SESSION_TIMEOUT']:
            session.clear()
            return redirect(url_for('login_2fa'))
        
        return f(*args, **kwargs)
    return decorated_function
```

### 2. **Шифрование ключа шифрования**
```python
# Дополнительное шифрование ключа с помощью пароля пользователя
def encrypt_master_key(master_key, password):
    """Шифрует мастер-ключ с помощью пароля пользователя."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    cipher = AES.new(key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(master_key.encode())
    return salt + cipher.nonce + tag + ciphertext

def decrypt_master_key(encrypted_key, password):
    """Расшифровывает мастер-ключ с помощью пароля пользователя."""
    salt = encrypted_key[:16]
    nonce = encrypted_key[16:32]
    tag = encrypted_key[32:48]
    ciphertext = encrypted_key[48:]
    
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    return cipher.decrypt_and_verify(ciphertext, tag).decode()
```

### 3. **Ограничение доступа по IP**
```python
# Добавить в app.py
ALLOWED_IPS = ['127.0.0.1', '::1']  # Только локальный доступ

def check_ip_access():
    """Проверяет, разрешен ли доступ с текущего IP."""
    client_ip = request.remote_addr
    if client_ip not in ALLOWED_IPS:
        abort(403, description="Доступ запрещен с вашего IP-адреса")

@app.before_request
def before_request():
    """Выполняется перед каждым запросом."""
    check_ip_access()
```

### 4. **Логирование безопасности**
```python
import logging
from datetime import datetime

# Настройка логирования безопасности
security_logger = logging.getLogger('security')
security_logger.setLevel(logging.INFO)
handler = logging.FileHandler('security.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
security_logger.addHandler(handler)

def log_security_event(event_type, details):
    """Логирует события безопасности."""
    security_logger.info(f"{event_type}: {details} - IP: {request.remote_addr}")

# Примеры использования:
# log_security_event("LOGIN_ATTEMPT", f"User: {username}")
# log_security_event("DATA_EXPORT", f"File: {filename}")
# log_security_event("KEY_CHANGE", "Master key changed")
```

### 5. **Автоматическое резервное копирование**
```python
import shutil
from datetime import datetime, timedelta

def create_backup():
    """Создает резервную копию данных."""
    backup_dir = os.path.join(APP_DATA_DIR, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(backup_dir, f'backup_{timestamp}.enc')
    
    # Копируем активный файл данных
    active_file = get_active_data_path()
    if active_file and os.path.exists(active_file):
        shutil.copy2(active_file, backup_file)
        
        # Удаляем старые резервные копии (старше 30 дней)
        cleanup_old_backups(backup_dir, days=30)
        
        return backup_file
    return None

def cleanup_old_backups(backup_dir, days=30):
    """Удаляет старые резервные копии."""
    cutoff_date = datetime.now() - timedelta(days=days)
    
    for filename in os.listdir(backup_dir):
        if filename.startswith('backup_') and filename.endswith('.enc'):
            file_path = os.path.join(backup_dir, filename)
            file_time = datetime.fromtimestamp(os.path.getctime(file_path))
            
            if file_time < cutoff_date:
                os.remove(file_path)
```

### 6. **Проверка целостности данных**
```python
import hashlib

def calculate_data_hash(data):
    """Вычисляет хеш данных для проверки целостности."""
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

def verify_data_integrity(servers):
    """Проверяет целостность данных."""
    for server in servers:
        # Проверяем обязательные поля
        required_fields = ['id', 'name', 'provider']
        for field in required_fields:
            if field not in server:
                return False, f"Missing required field: {field}"
        
        # Проверяем формат UUID
        try:
            uuid.UUID(server['id'])
        except ValueError:
            return False, f"Invalid UUID format: {server['id']}"
    
    return True, "Data integrity verified"

# Добавить в функцию save_ai_services
def save_ai_services(servers):
    # Проверяем целостность перед сохранением
    is_valid, message = verify_data_integrity(servers)
    if not is_valid:
        flash(f'Ошибка целостности данных: {message}', 'danger')
        return
    
    # Добавляем хеш данных
    data_hash = calculate_data_hash(servers)
    servers.append({'_integrity_hash': data_hash})
    
    # Сохраняем как обычно...
```

### 7. **Шифрование файлов конфигурации**
```python
def encrypt_config(config_data):
    """Шифрует конфигурацию приложения."""
    json_string = json.dumps(config_data, ensure_ascii=False, indent=2)
    return fernet.encrypt(json_string.encode('utf-8'))

def decrypt_config(encrypted_config):
    """Расшифровывает конфигурацию приложения."""
    try:
        decrypted_data = fernet.decrypt(encrypted_config)
        return json.loads(decrypted_data.decode('utf-8'))
    except Exception:
        return {}

# Использование в save_app_config и load_config_from_path
```

### 8. **Автоматическое обновление ключей**
```python
def rotate_encryption_key():
    """Автоматически обновляет ключ шифрования."""
    # Генерируем новый ключ
    new_key = Fernet.generate_key().decode()
    new_fernet = Fernet(new_key.encode())
    
    # Загружаем текущие данные
    servers = load_ai_services()
    
    # Перешифровываем все данные новым ключом
    for server in servers:
        server = re_encrypt_service_data(server, fernet, new_fernet)
    
    # Сохраняем данные с новым ключом
    save_ai_services(servers)
    
    # Обновляем ключ
    global SECRET_KEY, fernet
    SECRET_KEY = new_key
    fernet = new_fernet
    
    # Сохраняем новый ключ
    env_file = os.path.join(APP_DATA_DIR, '.env')
    with open(env_file, 'w') as f:
        f.write(f'SECRET_KEY={new_key}\n')
    
    return True

# Запускать автоматически каждые 90 дней
```

### 9. **Ограничение экспорта данных**
```python
def limit_export_frequency():
    """Ограничивает частоту экспорта данных."""
    client_ip = request.remote_addr
    current_time = time.time()
    
    if client_ip in app.config.get('EXPORT_ATTEMPTS', {}):
        last_export, count = app.config['EXPORT_ATTEMPTS'][client_ip]
        
        # Максимум 5 экспортов в час
        if current_time - last_export < 3600 and count >= 5:
            return False, "Превышен лимит экспорта. Попробуйте позже."
        
        if current_time - last_export < 3600:
            app.config['EXPORT_ATTEMPTS'][client_ip] = (last_export, count + 1)
        else:
            app.config['EXPORT_ATTEMPTS'][client_ip] = (current_time, 1)
    else:
        app.config.setdefault('EXPORT_ATTEMPTS', {})[client_ip] = (current_time, 1)
    
    return True, "Export allowed"
```

### 10. **Шифрование временных файлов**
```python
def secure_temp_file(data, prefix='temp_'):
    """Создает временный зашифрованный файл."""
    temp_dir = os.path.join(APP_DATA_DIR, 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    # Генерируем случайное имя файла
    temp_filename = f"{prefix}{secrets.token_hex(8)}.enc"
    temp_path = os.path.join(temp_dir, temp_filename)
    
    # Шифруем и сохраняем данные
    encrypted_data = fernet.encrypt(data.encode('utf-8'))
    with open(temp_path, 'wb') as f:
        f.write(encrypted_data)
    
    return temp_path

def cleanup_temp_files():
    """Удаляет временные файлы старше 1 часа."""
    temp_dir = os.path.join(APP_DATA_DIR, 'temp')
    if not os.path.exists(temp_dir):
        return
    
    current_time = time.time()
    for filename in os.listdir(temp_dir):
        file_path = os.path.join(temp_dir, filename)
        if os.path.isfile(file_path):
            file_age = current_time - os.path.getctime(file_path)
            if file_age > 3600:  # 1 час
                os.remove(file_path)
```

## �� Приоритеты внедрения

### Высокий приоритет:
1. **Логирование безопасности** - для отслеживания подозрительной активности
2. **Проверка целостности данных** - для предотвращения повреждения данных
3. **Автоматическое резервное копирование** - для защиты от потери данных

### Средний приоритет:
4. **Ограничение доступа по IP** - для дополнительной защиты
5. **Шифрование конфигурации** - для защиты настроек
6. **Ограничение экспорта** - для предотвращения утечек

### Низкий приоритет:
7. **Двухфакторная аутентификация** - сложно для настольного приложения
8. **Шифрование ключа шифрования** - избыточно для большинства случаев
9. **Автоматическое обновление ключей** - может быть неудобно для пользователей

## 📋 План внедрения

1. **Неделя 1**: Логирование безопасности + проверка целостности
2. **Неделя 2**: Автоматическое резервное копирование
3. **Неделя 3**: Ограничение доступа по IP
4. **Неделя 4**: Шифрование конфигурации + ограничение экспорта

## ⚠️ Важные замечания

- Все изменения должны быть протестированы на копии данных
- Необходимо создать механизм восстановления при сбоях
- Пользователи должны быть уведомлены об изменениях
- Документация должна быть обновлена

