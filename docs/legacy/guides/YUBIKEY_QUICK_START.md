# 🚀 YUBIKEY QUICK START - БЫСТРЫЙ СТАРТ

## 🎯 ЦЕЛЬ
Быстро добавить YubiKey аутентификацию в любой Flask проект за 30 минут.

## 📋 МИНИМАЛЬНЫЕ ТРЕБОВАНИЯ

### Установка
```bash
pip install flask yubico-client python-dotenv
```

### Структура
```
project/
├── app.py
├── yubikey_auth.py
├── yubikey_config.json
├── .env
└── templates/
    ├── yubikey_login.html
    └── layout.html
```

## 🔧 БЫСТРАЯ РЕАЛИЗАЦИЯ

### 1. Модуль аутентификации (yubikey_auth.py)
Этот модуль инкапсулирует всю логику. Он проверяет интернет-соединение и автоматически выбирает метод проверки: онлайн через API Yubico или офлайн по списку статических паролей.

```python
import json
import os
import socket
from functools import wraps
from flask import session, redirect, url_for, flash
from yubico_client import Yubico
from yubico_client.yubico_exceptions import YubicoError

def check_internet_connection(host="api.yubico.com", port=443, timeout=2):
    """Проверяет наличие интернет-соединения."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except (socket.error, socket.timeout):
        return False

class YubiKeyAuth:
    def __init__(self, static_passwords=None, config_file='yubikey_config.json'):
        self.config_file = config_file
        self.static_passwords = static_passwords or []
        self.keys = self.load_keys()
    
    def load_keys(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load().get('keys', [])
            return []
        except:
            return []
    
    def save_keys(self):
        try:
            with open(self.config_file, 'w') as f:
                json.dump({'keys': self.keys}, f, indent=2)
            return True
        except:
            return False
    
    def add_key(self, client_id, secret_key, key_name):
        self.keys.append({
            'client_id': client_id,
            'secret_key': secret_key,
            'name': key_name
        })
        return self.save_keys()
    
    def verify_otp(self, otp):
        """Гибридная проверка: онлайн, если есть интернет, иначе офлайн."""
        if not otp:
            return False, "OTP не может быть пустым"

        if check_internet_connection():
        if not self.keys:
                return False, "Онлайн-ключи не настроены"
            for key_data in self.keys:
                try:
                    client = Yubico(key_data['client_id'], key_data['secret_key'])
                    if client.verify(otp):
                        session.pop('offline_auth', None)
                        return True, f"Онлайн-ключ '{key_data['name']}' подтвержден"
                except YubicoError:
                continue
            return False, "Неверный онлайн OTP"
        else:
            if not self.static_passwords:
                return False, "Офлайн-пароли не настроены"
            if otp in self.static_passwords:
                session['offline_auth'] = True
                return True, "Офлайн-пароль подтвержден"
            return False, "Неверный офлайн-пароль"
    
    def is_authenticated(self):
        return session.get('yubikey_authenticated', False)
    
    def require_auth(self, f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Для простоты примера, если ключей нет, доступ разрешен
            if not self.keys and not self.static_passwords:
                return f(*args, **kwargs)
            if not self.is_authenticated():
                flash('Требуется YubiKey', 'warning')
                return redirect(url_for('yubikey_login'))
            return f(*args, **kwargs)
        return decorated_function
    
    def login(self, otp):
        success, message = self.verify_otp(otp)
        if success:
            session['yubikey_authenticated'] = True
        return success, message
    
    def logout(self):
        session.pop('yubikey_authenticated', None)
        session.pop('offline_auth', None)
```

### 2. Основное приложение (app.py)
Приложение теперь загружает переменные из `.env` файла, включая список статических паролей, и передает их в модуль аутентификации.

```python
from flask import Flask, render_template, request, redirect, url_for, session, flash
from yubikey_auth import YubiKeyAuth
import os
from dotenv import load_dotenv

load_dotenv() # Загружаем переменные из .env

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default-secret-key-change-me')

# Загружаем статические пароли из .env и преобразуем в список
static_passwords_str = os.environ.get('YUBIKEY_STATIC_PASSWORDS', '')
static_passwords = [p.strip() for p in static_passwords_str.split(',') if p.strip()]

yubikey_auth = YubiKeyAuth(static_passwords=static_passwords)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/yubikey/login', methods=['GET', 'POST'])
def yubikey_login():
    if request.method == 'POST':
        otp = request.form.get('otp', '').strip()
        if otp:
            success, message = yubikey_auth.login(otp)
            if success:
                flash(message, 'success')
                return redirect(url_for('index'))
            else:
                flash(message, 'error')
        else:
            flash('Введите OTP', 'error')
    
    return render_template('yubikey_login.html')

@app.route('/yubikey/setup', methods=['GET', 'POST'])
@yubikey_auth.require_auth
def yubikey_setup():
    if request.method == 'POST':
        client_id = request.form.get('client_id', '').strip()
        secret_key = request.form.get('secret_key', '').strip()
        key_name = request.form.get('key_name', '').strip()
        
        if all([client_id, secret_key, key_name]):
            if yubikey_auth.add_key(client_id, secret_key, key_name):
                flash(f'Ключ {key_name} добавлен', 'success')
            else:
                flash('Ошибка добавления', 'error')
        else:
            flash('Заполните все поля', 'error')
    
    return render_template('yubikey_setup.html', keys=yubikey_auth.keys)

@app.route('/yubikey/logout')
def yubikey_logout():
    yubikey_auth.logout()
    flash('Вы вышли', 'info')
    return redirect(url_for('index'))

@app.route('/protected')
@yubikey_auth.require_auth
def protected():
    return "Защищенная страница"

if __name__ == '__main__':
    app.run(debug=True)
```

### 3. Шаблон входа (templates/yubikey_login.html)
Добавим небольшую подсказку для пользователя.
```html
{% extends "layout.html" %}

{% block content %}
<div class="container mt-5">
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h4>Вход с YubiKey</h4>
                </div>
                <div class="card-body">
                    <form method="POST">
                        <div class="mb-3">
                            <label for="otp" class="form-label">OTP код</label>
                            <input type="text" 
                                   class="form-control" 
                                   id="otp" 
                                   name="otp" 
                                   placeholder="Коснитесь YubiKey для ввода кода"
                                   maxlength="44"
                                   required
                                   autofocus>
                            <div class="form-text">Короткое касание для онлайн-входа, длинное — для офлайн.</div>
                        </div>
                        <button type="submit" class="btn btn-primary w-100">Войти</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### 4. Шаблон настройки (templates/yubikey_setup.html)
Код остается прежним, но теперь он работает с новой логикой.

### 5. Базовый layout (templates/layout.html)
Обновим Bootstrap и добавим индикатор офлайн-режима.
```html
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}Приложение{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('index') }}">Приложение</a>
            <div class="navbar-nav ms-auto">
                {% if session.get('yubikey_authenticated') %}
                    {% if session.get('offline_auth') %}
                        <span class="navbar-text text-warning me-3">
                            <i class="bi bi-wifi-off"></i> Офлайн-режим
                        </span>
                    {% else %}
                        <span class="navbar-text text-success me-3">
                            <i class="bi bi-shield-check"></i> YubiKey активен
                        </span>
                    {% endif %}
                    <a class="nav-link" href="{{ url_for('yubikey_setup') }}">Настройки</a>
                    <a class="nav-link" href="{{ url_for('yubikey_logout') }}">Выйти</a>
                {% else %}
                    <a class="nav-link" href="{{ url_for('yubikey_login') }}">Войти</a>
                {% endif %}
            </div>
        </div>
    </nav>
    
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            <div class="container mt-3">
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'danger' if category == 'error' else category }}">{{ message }}</div>
                {% endfor %}
            </div>
        {% endif %}
    {% endwith %}
    
    {% block content %}{% endblock %}
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
```

## 🚀 ЗАПУСК

### 1. Получите Yubico API ключи (для онлайн-режима)
- Зарегистрируйтесь на https://developers.yubico.com/
- Создайте приложение и получите **Client ID** и **Secret Key**.

### 2. (Опционально) Настройте статический пароль (для офлайн-режима)
Используйте приложение **YubiKey Manager** для настройки одного из слотов ключа на вывод статического пароля.
- **Applications -> OTP -> Configure Slot 2 (Long Touch)**.
- Выберите **Static Password**.
- Сгенерируйте пароль (рекомендуется > 32 символов) и **надежно сохраните его**. Он понадобится на следующем шаге.
- Повторите для всех ключей, которые вы хотите использовать офлайн.

### 3. Создайте .env файл
В корне проекта создайте файл `.env` и добавьте в него:
```dotenv
# Секретный ключ для сессий Flask
SECRET_KEY="ВАШ_СЛУЧАЙНЫЙ_СЕКРЕТНЫЙ_КЛЮЧ"

# Статические пароли через запятую (для офлайн-входа)
YUBIKEY_STATIC_PASSWORDS=<ваши_статические_пароли>
```

### 4. Запустите приложение
```bash
python app.py
```

### 5. Настройте первый онлайн-ключ
- Приложение запустится, но пока не защищено.
- Перейдите на http://localhost:5000/yubikey/setup
- Добавьте Client ID, Secret Key и название для вашего первого ключа.

### 6. Протестируйте вход
- Выйдите и снова зайдите на http://localhost:5000/yubikey/login.
- **Онлайн-вход**: Коротко коснитесь YubiKey.
- **Офлайн-вход**: Отключите интернет и удерживайте кнопку YubiKey 2-3 секунды.

## 🛡️ ЗАЩИТА МАРШРУТОВ

```python
@app.route('/admin')
@yubikey_auth.require_auth
def admin():
    return "Админ панель"

@app.route('/settings')
@yubikey_auth.require_auth
def settings():
    return "Настройки"
```

## 🔧 НАСТРОЙКА ДЛЯ PRODUCTION

```python
# config.py
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True

# app.py
from config import Config
app.config.from_object(Config)
```

## 📚 ПОЛНАЯ ВЕРСИЯ

Для полной реализации с расширенными возможностями используйте:
**`YUBIKEY_DEVELOPMENT_PROMPT.md`** - подробный промт с полным опытом разработки.

---

**Готово!** Ваше приложение теперь защищено гибридной YubiKey аутентификацией! 🔐 