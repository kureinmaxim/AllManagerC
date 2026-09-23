# 🔐 ПРОМТ: РАЗРАБОТКА С YUBIKEY АУТЕНТИФИКАЦИЕЙ

## 🎯 ЦЕЛЬ ПРОМТА

Этот промт содержит полный опыт разработки системы двухфакторной аутентификации с использованием YubiKey для веб-приложений. Используйте его для добавления аналогичной функциональности в любой проект.

## 📋 ПРЕДВАРИТЕЛЬНЫЕ ТРЕБОВАНИЯ

### Технический стек
- **Backend**: Python Flask/Django/FastAPI
- **Frontend**: HTML/CSS/JavaScript (Bootstrap для UI)
- **Криптография**: Python cryptography library
- **API**: Yubico API для верификации OTP
- **Хранение данных**: JSON/CSV/SQLite с шифрованием

### Необходимые знания
- Базовое понимание веб-разработки
- Знакомство с Python
- Понимание принципов безопасности
- Опыт работы с API

## 🚀 ПОШАГОВАЯ ИНСТРУКЦИЯ РАЗРАБОТКИ

### Шаг 1: Настройка Yubico Developer Account

**1.1 Регистрация на Yubico Developer Console**
```bash
# Перейдите на https://developers.yubico.com/
# Создайте аккаунт и войдите в Developer Console
```

**1.2 Создание приложения**
- В Developer Console создайте новое приложение
- Получите **Client ID** и **Secret Key**
- Настройте домены для API (localhost для разработки)

**1.3 Получение ключей**
- Приобретите YubiKey (рекомендуется несколько для резервирования)
- Протестируйте ключи на https://demo.yubico.com/

### Шаг 2: Установка зависимостей

**2.1 Python пакеты**
```bash
pip install cryptography requests flask pywebview
```

**2.2 Структура проекта**
```
project/
├── app.py                    # Основное приложение
├── yubikey_auth.py          # Модуль аутентификации YubiKey
├── yubikey_config.json      # Конфигурация ключей
├── .env                     # Секретные ключи
├── templates/               # HTML шаблоны
│   ├── yubikey_login.html
│   ├── yubikey_setup.html
│   └── yubikey_instructions.html
└── static/                  # CSS/JS файлы
```

### Шаг 3: Создание модуля аутентификации

**3.1 Основной класс YubiKeyAuth**
```python
import json
import requests
import os
from cryptography.fernet import Fernet
from functools import wraps
from flask import session, redirect, url_for, flash

class YubiKeyAuth:
    def __init__(self, config_file='yubikey_config.json'):
        self.config_file = config_file
        self.keys = self.load_keys()
        self.api_url = "https://api.yubico.com/wsapi/2.0/verify"
    
    def load_keys(self):
        """Загрузка конфигурации ключей из файла"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Ошибка загрузки конфигурации: {e}")
            return {}
    
    def save_keys(self):
        """Сохранение конфигурации ключей"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.keys, f, indent=2)
            return True
        except Exception as e:
            print(f"Ошибка сохранения конфигурации: {e}")
            return False
    
    def add_key(self, client_id, secret_key, key_name):
        """Добавление нового YubiKey"""
        if not self.keys:
            self.keys = {}
        
        self.keys[key_name] = {
            'client_id': client_id,
            'secret_key': secret_key,
            'active': True
        }
        
        return self.save_keys()
    
    def remove_key(self, key_name):
        """Удаление YubiKey"""
        if key_name in self.keys:
            del self.keys[key_name]
            return self.save_keys()
        return False
    
    def verify_otp(self, otp):
        """Верификация OTP через Yubico API"""
        if not self.keys:
            return False, "Нет настроенных ключей"
        
        for key_name, key_data in self.keys.items():
            if not key_data.get('active', False):
                continue
            
            params = {
                'id': key_data['client_id'],
                'otp': otp,
                'nonce': os.urandom(16).hex()
            }
            
            try:
                response = requests.get(self.api_url, params=params)
                if response.status_code == 200:
                    lines = response.text.split('\n')
                    status = None
                    
                    for line in lines:
                        if line.startswith('status='):
                            status = line.split('=')[1]
                            break
                    
                    if status == 'OK':
                        return True, f"Успешная аутентификация с ключом {key_name}"
                    else:
                        continue
                        
            except Exception as e:
                print(f"Ошибка API запроса: {e}")
                continue
        
        return False, "Неверный OTP код"
    
    def is_authenticated(self):
        """Проверка аутентификации пользователя"""
        return session.get('yubikey_authenticated', False)
    
    def require_auth(self, f):
        """Декоратор для защиты маршрутов"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not self.is_authenticated():
                flash('Требуется аутентификация YubiKey', 'warning')
                return redirect(url_for('yubikey_login'))
            return f(*args, **kwargs)
        return decorated_function
    
    def login(self, otp):
        """Вход в систему"""
        success, message = self.verify_otp(otp)
        if success:
            session['yubikey_authenticated'] = True
            session['yubikey_key_used'] = message
        return success, message
    
    def logout(self):
        """Выход из системы"""
        session.pop('yubikey_authenticated', None)
        session.pop('yubikey_key_used', None)
```

**3.2 Декоратор для защиты маршрутов**
```python
# Использование декоратора
@app.route('/protected')
@yubikey_auth.require_auth
def protected_page():
    return "Эта страница защищена YubiKey"
```

### Шаг 4: Создание Flask маршрутов

**4.1 Основные маршруты аутентификации**
```python
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from yubikey_auth import YubiKeyAuth

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key')

# Инициализация YubiKey аутентификации
yubikey_auth = YubiKeyAuth()

@app.route('/yubikey/login', methods=['GET', 'POST'])
def yubikey_login():
    if request.method == 'POST':
        otp = request.form.get('otp', '').strip()
        
        if not otp:
            flash('Введите OTP код', 'error')
            return render_template('yubikey_login.html')
        
        success, message = yubikey_auth.login(otp)
        
        if success:
            flash(message, 'success')
            return redirect(url_for('index'))
        else:
            flash(message, 'error')
    
    return render_template('yubikey_login.html')

@app.route('/yubikey/setup', methods=['GET', 'POST'])
@yubikey_auth.require_auth
def yubikey_setup():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            client_id = request.form.get('client_id', '').strip()
            secret_key = request.form.get('secret_key', '').strip()
            key_name = request.form.get('key_name', '').strip()
            
            if not all([client_id, secret_key, key_name]):
                flash('Заполните все поля', 'error')
            else:
                if yubikey_auth.add_key(client_id, secret_key, key_name):
                    flash(f'Ключ {key_name} успешно добавлен', 'success')
                else:
                    flash('Ошибка добавления ключа', 'error')
        
        elif action == 'remove':
            key_name = request.form.get('key_name')
            if yubikey_auth.remove_key(key_name):
                flash(f'Ключ {key_name} удален', 'success')
            else:
                flash('Ошибка удаления ключа', 'error')
    
    return render_template('yubikey_setup.html', keys=yubikey_auth.keys)

@app.route('/yubikey/logout')
def yubikey_logout():
    yubikey_auth.logout()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))

@app.route('/yubikey/instructions')
def yubikey_instructions():
    return render_template('yubikey_instructions.html')
```

### Шаг 5: Создание HTML шаблонов

**5.1 Страница входа (yubikey_login.html)**
```html
{% extends "layout.html" %}

{% block content %}
<div class="container mt-5">
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h4 class="mb-0">
                        <i class="fas fa-key"></i> Вход с YubiKey
                    </h4>
                </div>
                <div class="card-body">
                    <form method="POST">
                        <div class="mb-3">
                            <label for="otp" class="form-label">OTP код</label>
                            <input type="text" 
                                   class="form-control" 
                                   id="otp" 
                                   name="otp" 
                                   placeholder="Вставьте YubiKey и коснитесь контакта"
                                   maxlength="44"
                                   required>
                            <div class="form-text">
                                Вставьте YubiKey в USB-порт, коснитесь золотого контакта и вставьте сгенерированный код
                            </div>
                        </div>
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-sign-in-alt"></i> Войти
                        </button>
                    </form>
                    
                    <hr>
                    
                    <div class="text-center">
                        <a href="{{ url_for('yubikey_instructions') }}" class="btn btn-outline-info btn-sm">
                            <i class="fas fa-question-circle"></i> Как получить ключи Yubico?
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

**5.2 Страница настройки (yubikey_setup.html)**
```html
{% extends "layout.html" %}

{% block content %}
<div class="container mt-4">
    <h2><i class="fas fa-cog"></i> Настройка YubiKey</h2>
    
    <!-- Добавление нового ключа -->
    <div class="card mb-4">
        <div class="card-header">
            <h5 class="mb-0">Добавить новый ключ</h5>
        </div>
        <div class="card-body">
            <form method="POST">
                <input type="hidden" name="action" value="add">
                <div class="row">
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label for="key_name" class="form-label">Название ключа</label>
                            <input type="text" class="form-control" id="key_name" name="key_name" required>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label for="client_id" class="form-label">Client ID</label>
                            <input type="text" class="form-control" id="client_id" name="client_id" required>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label for="secret_key" class="form-label">Secret Key</label>
                            <input type="password" class="form-control" id="secret_key" name="secret_key" required>
                        </div>
                    </div>
                </div>
                <button type="submit" class="btn btn-success">
                    <i class="fas fa-plus"></i> Добавить ключ
                </button>
            </form>
        </div>
    </div>
    
    <!-- Список существующих ключей -->
    <div class="card">
        <div class="card-header">
            <h5 class="mb-0">Настроенные ключи</h5>
        </div>
        <div class="card-body">
            {% if keys %}
                <div class="table-responsive">
                    <table class="table table-striped">
                        <thead>
                            <tr>
                                <th>Название</th>
                                <th>Client ID</th>
                                <th>Статус</th>
                                <th>Действия</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for key_name, key_data in keys.items() %}
                            <tr>
                                <td>{{ key_name }}</td>
                                <td>{{ key_data.client_id }}</td>
                                <td>
                                    {% if key_data.active %}
                                        <span class="badge bg-success">Активен</span>
                                    {% else %}
                                        <span class="badge bg-secondary">Неактивен</span>
                                    {% endif %}
                                </td>
                                <td>
                                    <form method="POST" style="display: inline;">
                                        <input type="hidden" name="action" value="remove">
                                        <input type="hidden" name="key_name" value="{{ key_name }}">
                                        <button type="submit" class="btn btn-danger btn-sm" 
                                                onclick="return confirm('Удалить ключ {{ key_name }}?')">
                                            <i class="fas fa-trash"></i> Удалить
                                        </button>
                                    </form>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            {% else %}
                <div class="alert alert-info">
                    <i class="fas fa-info-circle"></i> Нет настроенных ключей YubiKey
                </div>
            {% endif %}
        </div>
    </div>
</div>
{% endblock %}
```

**5.3 Инструкции (yubikey_instructions.html)**
```html
{% extends "layout.html" %}

{% block content %}
<div class="container mt-4">
    <h2><i class="fas fa-question-circle"></i> Как получить ключи Yubico</h2>
    
    <div class="row">
        <div class="col-md-8">
            <div class="card">
                <div class="card-body">
                    <h5>Шаг 1: Регистрация на Yubico Developer Console</h5>
                    <ol>
                        <li>Перейдите на <a href="https://developers.yubico.com/" target="_blank">https://developers.yubico.com/</a></li>
                        <li>Создайте аккаунт или войдите в существующий</li>
                        <li>Перейдите в Developer Console</li>
                    </ol>
                    
                    <h5>Шаг 2: Создание приложения</h5>
                    <ol>
                        <li>Нажмите "Create Application"</li>
                        <li>Заполните форму:
                            <ul>
                                <li><strong>Application Name:</strong> Название вашего приложения</li>
                                <li><strong>Application URL:</strong> http://localhost:5000 (для разработки)</li>
                                <li><strong>Application Description:</strong> Описание приложения</li>
                            </ul>
                        </li>
                        <li>Нажмите "Create Application"</li>
                    </ol>
                    
                    <h5>Шаг 3: Получение ключей</h5>
                    <ol>
                        <li>После создания приложения вы получите:
                            <ul>
                                <li><strong>Client ID:</strong> Длинная строка символов</li>
                                <li><strong>Secret Key:</strong> Секретный ключ для API</li>
                            </ul>
                        </li>
                        <li>Сохраните эти ключи в безопасном месте</li>
                    </ol>
                    
                    <h5>Шаг 4: Приобретение YubiKey</h5>
                    <ol>
                        <li>Купите YubiKey на <a href="https://www.yubico.com/" target="_blank">https://www.yubico.com/</a></li>
                        <li>Рекомендуется приобрести несколько ключей для резервирования</li>
                        <li>Протестируйте ключи на <a href="https://demo.yubico.com/" target="_blank">https://demo.yubico.com/</a></li>
                    </ol>
                    
                    <h5>Шаг 5: Настройка в приложении</h5>
                    <ol>
                        <li>Вернитесь в приложение</li>
                        <li>Перейдите в настройки YubiKey</li>
                        <li>Добавьте полученные Client ID и Secret Key</li>
                        <li>Дайте ключу понятное название</li>
                    </ol>
                </div>
            </div>
        </div>
        
        <div class="col-md-4">
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">Полезные ссылки</h5>
                </div>
                <div class="card-body">
                    <ul class="list-unstyled">
                        <li><a href="https://developers.yubico.com/" target="_blank">Yubico Developer Console</a></li>
                        <li><a href="https://demo.yubico.com/" target="_blank">Демо YubiKey</a></li>
                        <li><a href="https://www.yubico.com/" target="_blank">Купить YubiKey</a></li>
                        <li><a href="https://developers.yubico.com/OTP/OTPs_Explained.html" target="_blank">Как работают OTP</a></li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### Шаг 6: Интеграция с основным приложением

**6.1 Обновление layout.html**
```html
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Приложение{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    {% block extra_css %}{% endblock %}
</head>
<body>
    <!-- Навигационная панель -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('index') }}">
                <i class="fas fa-shield-alt"></i> Защищенное приложение
            </a>
            
            <div class="navbar-nav ms-auto">
                {% if session.get('yubikey_authenticated') %}
                    <span class="navbar-text me-3">
                        <i class="fas fa-key text-success"></i> YubiKey активен
                    </span>
                    <a class="nav-link" href="{{ url_for('yubikey_setup') }}">
                        <i class="fas fa-cog"></i> Настройки YubiKey
                    </a>
                    <a class="nav-link" href="{{ url_for('yubikey_logout') }}">
                        <i class="fas fa-sign-out-alt"></i> Выйти
                    </a>
                {% else %}
                    <a class="nav-link" href="{{ url_for('yubikey_login') }}">
                        <i class="fas fa-sign-in-alt"></i> Войти с YubiKey
                    </a>
                {% endif %}
            </div>
        </div>
    </nav>
    
    <!-- Сообщения -->
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            <div class="container mt-3">
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'danger' if category == 'error' else category }} alert-dismissible fade show">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            </div>
        {% endif %}
    {% endwith %}
    
    <!-- Основной контент -->
    <main>
        {% block content %}{% endblock %}
    </main>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>
```

**6.2 Защита маршрутов**
```python
# Пример защиты различных маршрутов
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/protected-data')
@yubikey_auth.require_auth
def protected_data():
    return render_template('protected_data.html')

@app.route('/admin')
@yubikey_auth.require_auth
def admin_panel():
    return render_template('admin.html')

@app.route('/settings')
@yubikey_auth.require_auth
def settings():
    return render_template('settings.html')
```

### Шаг 7: Обработка ошибок и безопасность

**7.1 Обработчик ошибок**
```python
@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error=error), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error=error), 404
```

**7.2 Шаблон ошибок (error.html)**
```html
{% extends "layout.html" %}

{% block content %}
<div class="container mt-5">
    <div class="row justify-content-center">
        <div class="col-md-8">
            <div class="card border-danger">
                <div class="card-header bg-danger text-white">
                    <h4 class="mb-0">
                        <i class="fas fa-exclamation-triangle"></i> Ошибка {{ error.code if error.code else '500' }}
                    </h4>
                </div>
                <div class="card-body">
                    <h5>Что произошло?</h5>
                    <p>{{ error.description if error.description else 'Произошла внутренняя ошибка сервера' }}</p>
                    
                    <h5>Что можно сделать?</h5>
                    <ul>
                        <li>Проверьте правильность введенных данных</li>
                        <li>Убедитесь, что у вас есть доступ к этой странице</li>
                        <li>Попробуйте обновить страницу</li>
                        <li>Если проблема повторяется, обратитесь к администратору</li>
                    </ul>
                    
                    <div class="mt-4">
                        <a href="{{ url_for('index') }}" class="btn btn-primary">
                            <i class="fas fa-home"></i> Вернуться на главную
                        </a>
                        <a href="{{ url_for('yubikey_login') }}" class="btn btn-outline-secondary">
                            <i class="fas fa-key"></i> Войти с YubiKey
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### Шаг 8: Тестирование и отладка

**8.1 Тестовые скрипты**
```python
# test_yubikey.py
import requests

def test_yubikey_login():
    """Тест входа с YubiKey"""
    url = "http://localhost:5000/yubikey/login"
    
    # Тест с неверным OTP
    data = {'otp': 'invalid_otp_code'}
    response = requests.post(url, data=data)
    print(f"Неверный OTP: {response.status_code}")
    
    # Тест с пустым OTP
    data = {'otp': ''}
    response = requests.post(url, data=data)
    print(f"Пустой OTP: {response.status_code}")

def test_protected_routes():
    """Тест защищенных маршрутов"""
    session = requests.Session()
    
    # Попытка доступа без аутентификации
    response = session.get("http://localhost:5000/protected-data")
    print(f"Доступ без аутентификации: {response.status_code}")
    
    # Должно быть перенаправление на страницу входа
    assert response.status_code in [302, 401]

if __name__ == "__main__":
    test_yubikey_login()
    test_protected_routes()
```

**8.2 Отладочные команды**
```bash
# Проверка доступности маршрутов
curl -I http://localhost:5000/
curl -I http://localhost:5000/yubikey/login
curl -I http://localhost:5000/yubikey/setup

# Тест формы входа
curl -X POST http://localhost:5000/yubikey/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "otp=test_otp"

# Проверка сессии
curl -b cookies.txt -c cookies.txt http://localhost:5000/protected-data
```

### Шаг 9: Развертывание и production

**9.1 Настройка для production**
```python
# config.py
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    YUBIKEY_CONFIG_FILE = os.environ.get('YUBIKEY_CONFIG_FILE') or 'yubikey_config.json'
    
    # Настройки безопасности
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Настройки Yubico API
    YUBICO_API_URL = "https://api.yubico.com/wsapi/2.0/verify"
    YUBICO_TIMEOUT = 10  # секунды

class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    DEBUG = False
```

**9.2 Переменные окружения**
```bash
# .env
SECRET_KEY=your-super-secret-key-here
YUBIKEY_CONFIG_FILE=/path/to/yubikey_config.json
FLASK_ENV=production
```

**9.3 WSGI конфигурация**
```python
# wsgi.py
from app import app

if __name__ == "__main__":
    app.run()
```

## 🔧 ДОПОЛНИТЕЛЬНЫЕ ВОЗМОЖНОСТИ

### Расширенная аутентификация
```python
# Поддержка множественных ключей с приоритетами
def add_key_with_priority(self, client_id, secret_key, key_name, priority=1):
    """Добавление ключа с приоритетом"""
    self.keys[key_name] = {
        'client_id': client_id,
        'secret_key': secret_key,
        'active': True,
        'priority': priority
    }
    return self.save_keys()

# Автоматическая ротация ключей
def rotate_keys(self):
    """Автоматическая смена активных ключей"""
    active_keys = [k for k, v in self.keys.items() if v.get('active')]
    if len(active_keys) > 1:
        # Логика ротации ключей
        pass
```

### Логирование и мониторинг
```python
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('yubikey_auth.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Логирование в методах
def verify_otp(self, otp):
    logger.info(f"Попытка верификации OTP: {otp[:8]}...")
    # ... остальной код
    if success:
        logger.info(f"Успешная аутентификация с ключом {key_name}")
    else:
        logger.warning(f"Неудачная попытка аутентификации: {message}")
```

### Интеграция с базой данных
```python
# SQLAlchemy модель для ключей
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class YubiKey(Base):
    __tablename__ = 'yubikey_keys'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    client_id = Column(String(100), nullable=False)
    secret_key = Column(String(100), nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)
```

## 🚨 ВАЖНЫЕ МОМЕНТЫ БЕЗОПАСНОСТИ

### 1. Защита секретных ключей
- Никогда не храните Secret Key в коде
- Используйте переменные окружения
- Шифруйте конфигурационные файлы
- Ограничивайте доступ к файлам конфигурации

### 2. Валидация OTP
- Проверяйте длину OTP (44 символа)
- Валидируйте формат OTP
- Используйте HTTPS для API запросов
- Ограничивайте количество попыток входа

### 3. Управление сессиями
- Используйте безопасные cookies
- Устанавливайте время жизни сессии
- Реализуйте автоматический выход
- Логируйте все действия пользователей

### 4. Резервное копирование
- Регулярно создавайте резервные копии ключей
- Храните ключи в разных местах
- Тестируйте восстановление из резервных копий
- Документируйте процедуры восстановления

## 📚 РЕСУРСЫ ДЛЯ ИЗУЧЕНИЯ

### Официальная документация
- [Yubico Developer Documentation](https://developers.yubico.com/)
- [Yubico API Reference](https://developers.yubico.com/OTP/OTPs_Explained.html)
- [Flask Security Documentation](https://flask-security.readthedocs.io/)

### Полезные статьи
- [Two-Factor Authentication with YubiKey](https://www.yubico.com/why-yubico/for-individuals/2fa/)
- [Flask Session Management](https://flask.palletsprojects.com/en/2.3.x/quickstart/#sessions)
- [Web Security Best Practices](https://owasp.org/www-project-top-ten/)

### Инструменты для тестирования
- [Yubico Demo](https://demo.yubico.com/)
- [Postman](https://www.postman.com/) для тестирования API
- [OWASP ZAP](https://owasp.org/www-project-zap/) для безопасности

## 🎯 ЗАКЛЮЧЕНИЕ

Этот промт содержит полный опыт разработки системы аутентификации с YubiKey. Используйте его как основу для добавления аналогичной функциональности в любой проект.

**Ключевые принципы:**
1. Безопасность превыше всего
2. Простота использования
3. Надежность и отказоустойчивость
4. Хорошая документация
5. Тестирование и отладка

**Следующие шаги:**
1. Адаптируйте код под ваш проект
2. Настройте Yubico Developer Console
3. Протестируйте функциональность
4. Разверните в production
5. Обучите пользователей

Удачи в разработке! 🚀 