> **Единый проект: AllManagerC**
>
> Рабочая папка — `AiManage-Clean`, репозиторий — `kureinmaxim/ai-manager`.
> Сюда объединены функции AiManage и GitHub-версии. Папка AiManage остаётся
> исходным архивом; дальнейшие изменения делайте здесь.
>
> Запуск из этой папки: `venv/bin/python run_app.py` (существующее окружение macOS).
> В новом окружении: `python -m pip install -r requirements.txt`, затем `python run_app.py`.
> Проверки: `python -m unittest discover -s tests -v`.
>
> Базы двух проектов сохранены отдельно и **не объединены** — выбор отложен пользователем.
> Перед импортом старой базы выберите соответствующий ей ключ через импорт с внешним ключом.
> Локальные резервные копии лежат в `.local-backups/before-unification-20260923/`;
> они исключены из Git и содержат конфиденциальные данные.
>
> Подробнее: [результат объединения](docs/UNIFICATION.md).
> Описание релиза 5.6.0 ниже относится к исходной GitHub-версии.

# 🔐 AI Manager - Менеджер AI сервисов

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Security](https://img.shields.io/badge/Security-YubiKey-red.svg)](https://www.yubico.com/)

> Безопасный менеджер для управления API ключами и настройками AI сервисов с поддержкой YubiKey аутентификации

## 🌟 Особенности

- 🔐 **Безопасная аутентификация** с поддержкой YubiKey и статических паролей
- 🔒 **Шифрование данных** - все API ключи хранятся в зашифрованном виде
- 📱 **Современный интерфейс** с адаптивным дизайном
- 🌐 **Веб и GUI версии** - используйте как веб-приложение или десктопную программу
- 📊 **Анализ сервисов** - проверка доступности и статистика использования
- 🔄 **Импорт/Экспорт** - резервное копирование и миграция данных
- 🛡️ **Безопасность** - логирование событий и защита от несанкционированного доступа

## 📋 Содержание

- [Установка](#-установка)
- [Быстрый старт](#-быстрый-старт)
- [Настройка аутентификации](#-настройка-аутентификации)
- [Использование](#-использование)
- [Безопасность](#-безопасность)
- [Разработка](#-разработка)
- [Сборка](#-сборка)
- [Решение проблем](#-решение-проблем)
- [Кросс-платформенная разработка](DEPLOYMENT.md)
- [Лицензия](#-лицензия)

## ⬇️ Скачать

- Последний релиз: [Latest Release](https://github.com/kureinmaxim/ai-manager/releases/latest)
- Прямая ссылка (v5.6.0, macOS DMG): [AllManagerC_Installer_v5.6.0.dmg](https://github.com/kureinmaxim/ai-manager/releases/download/v5.6.0/AllManagerC_Installer_v5.6.0.dmg)
- SHA256(DMG): `будет обновлен после сборки`

## 🚀 Установка

### Требования

- Python 3.8+ (для Windows рекомендуется Python 3.13+)
- pip
- Git

**Примечания:**
- В проекте используется виртуальное окружение `.venv` (с точкой)
- Windows PowerShell: Может потребоваться разрешить выполнение скриптов:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Клонирование репозитория

```bash
git clone https://github.com/your-username/ai-manager.git
cd ai-manager
```

### Установка зависимостей

```bash
# Создание виртуального окружения
# Windows:
python -m venv .venv
# macOS/Linux:
python3 -m venv .venv

# Активация виртуального окружения
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Windows CMD:
.venv\Scripts\activate.bat
# macOS/Linux:
source .venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
```

### Настройка окружения

Создайте файл `.env` в корне проекта:

```bash
# Конфигурация YubiKey
YUBIKEY_STATIC_PASSWORDS=demo123,test123,admin123

# Секретный ключ для Flask (автоматически генерируется)
SECRET_KEY=your-generated-key-here

# Настройки приложения
FLASK_ENV=development
FLASK_DEBUG=True

# Настройки шифрования
ENCRYPTION_KEY_FILE=.env
```

### Генерация секретного ключа

```bash
# Windows:
python -c "from cryptography.fernet import Fernet; print('SECRET_KEY=' + Fernet.generate_key().decode())"
# macOS/Linux:
python3 -c "from cryptography.fernet import Fernet; print('SECRET_KEY=' + Fernet.generate_key().decode())"
```

Скопируйте сгенерированный ключ в файл `.env`.

## 🎯 Быстрый старт

### Способ 1: GUI приложение (рекомендуется)

```bash
# Windows:
python run_app.py
# macOS/Linux:
python3 run_app.py
```

Приложение запустится с графическим интерфейсом в отдельном окне.

### Способ 2: Веб-интерфейс

```bash
# Windows:
python app.py
# macOS/Linux:
python3 app.py
```

Затем откройте браузер и перейдите по адресу: http://127.0.0.1:5050

## 🔐 Настройка аутентификации

### Статические пароли (офлайн-режим)

Отредактируйте файл `.env`:

```bash
YUBIKEY_STATIC_PASSWORDS=your-password1,your-password2,your-password3
```

### YubiKey (онлайн-режим)

1. Получите API ключи от [Yubico](https://www.yubico.com/)
2. Войдите в приложение
3. Перейдите в **Настройки** → **YubiKey**
4. Добавьте полученные ключи

### Комбинированный режим

Настройте оба варианта для работы в любых условиях.

📖 **Подробное руководство:** [АУТЕНТИФИКАЦИЯ.md](АУТЕНТИФИКАЦИЯ.md)

## 💻 Использование

### Первый запуск

1. Запустите приложение
2. Введите один из статических паролей для входа
3. Настройте YubiKey (опционально)
4. Добавьте первые AI сервисы

### Добавление сервиса

1. Нажмите кнопку "Добавить сервис"
2. Заполните форму:
   - **Название** - название AI сервиса
   - **URL** - веб-адрес сервиса
   - **API ключ** - ваш API ключ (будет зашифрован)
   - **Описание** - дополнительная информация

### Управление сервисами

- **Просмотр** - список всех добавленных сервисов
- **Редактирование** - изменение настроек сервиса
- **Удаление** - безопасное удаление с подтверждением
- **Экспорт** - резервное копирование данных

## 🛡️ Безопасность

### Шифрование данных

- Все API ключи шифруются с помощью Fernet
- Ключи шифрования хранятся отдельно от данных
- Поддержка смены ключей шифрования

### Аутентификация

- YubiKey OTP для максимальной безопасности
- Статические пароли для офлайн-режима
- Комбинированный режим для гибкости

### Логирование

- Все действия пользователя логируются
- Безопасное хранение логов
- Аудит доступа к данным

## 🔧 Разработка

### Структура проекта

```
ai-manager/
├── app.py                 # Основное Flask приложение
├── run_app.py            # GUI запуск приложения
├── yubikey_auth.py      # Модуль аутентификации
├── security_logger.py    # Логирование безопасности
├── requirements.txt      # Зависимости Python
├── .env                 # Конфигурация окружения
├── templates/           # HTML шаблоны
├── static/             # Статические файлы
├── data/               # Данные приложения
├── logs/               # Логи
└── tools/              # Вспомогательные инструменты
```

### Запуск в режиме разработки

```bash
# Активация виртуального окружения
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

# Установка зависимостей разработки
pip install -r requirements.txt

# Проверка окружения (опционально)
python check_env.py

# Запуск с отладкой
# Windows:
set FLASK_ENV=development && set FLASK_DEBUG=True && python app.py
# macOS/Linux:
FLASK_ENV=development FLASK_DEBUG=True python3 app.py
```

### Тестирование

```bash
# Запуск тестов (если есть)
python3 -m pytest

# Проверка кода
python3 -m flake8
python3 -m black .
```

## 📦 Сборка

### Создание исполняемого файла

```bash
# Установка PyInstaller
pip install pyinstaller

# Сборка для macOS
chmod +x build_macos.sh
./build_macos.sh

# Сборка для Windows
python build_windows.py
```

### Создание инсталлятора для Windows (Inno Setup)

#### Требования

- [Inno Setup 6.0+](https://jrsoftware.org/isdl.php) - бесплатный инсталлятор для Windows
- Собранное приложение PyInstaller (см. выше)

#### Шаг 1: Сборка приложения с PyInstaller

```powershell
# Активируйте виртуальное окружение (PowerShell)
.\.venv\Scripts\Activate.ps1

# Установите зависимости
pip install -r requirements.txt
pip install pyinstaller

# Запустите скрипт сборки
python build_windows.py
```

После выполнения команды исполняемый файл будет находиться в `dist\AllManagerC\AllManagerC.exe`.

#### Шаг 2: Настройка Inno Setup скрипта

Откройте файл `AllManagerC.iss` и при необходимости измените:

- **AppVersion** - версия приложения (например, `5.6.0`)
- **AppPublisher** - имя издателя
- **AppPublisherURL** - сайт издателя
- **DefaultDirName** - путь установки (по умолчанию `{autopf}\AllManagerC`)

Пример настройки:

```ini
#define MyAppVersion "5.6.0"
#define MyAppPublisher "Your Company"
#define MyAppURL "https://github.com/your-username/ai-manager"
```

#### Шаг 3: Компиляция инсталлятора

**Способ 1: Через GUI Inno Setup**

1. Откройте Inno Setup Compiler
2. Откройте файл `AllManagerC.iss` (File → Open)
3. Нажмите **Build** → **Compile** (или F9)
4. Готовый инсталлятор будет в папке `dist\AllManagerC_Installer.exe`

**Способ 2: Через командную строку**

```bash
# Путь к компилятору Inno Setup (по умолчанию)
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" AllManagerC.iss
```

#### Шаг 4: Проверка инсталлятора

1. Запустите созданный `.exe` файл
2. Следуйте инструкциям установщика
3. Проверьте установку приложения в `C:\Program Files\AllManagerC`
4. Запустите приложение через ярлык на рабочем столе

#### Хранение данных после установки

После установки через инсталлятор:

- **Программные файлы**: `C:\Program Files\AllManagerC\`
- **Пользовательские данные**: `%APPDATA%\AllManagerC\`
  - Конфигурация: `%APPDATA%\AllManagerC\config.json`
  - Данные: `%APPDATA%\AllManagerC\data\`
  - Загрузки: `%APPDATA%\AllManagerC\uploads\`
  - Ключи: `%APPDATA%\AllManagerC\.env`

**Важно:** Пользовательские данные не удаляются при деинсталляции программы.

### Создание инсталлятора для macOS

#### Требования

- macOS 10.13+
- Python 3.8+
- Xcode Command Line Tools (установить через `xcode-select --install`)
- [create-dmg](https://github.com/create-dmg/create-dmg) (опционально): `brew install create-dmg`

#### Автоматическая сборка (рекомендуется)

```bash
# Сделайте скрипт исполняемым (один раз)
chmod +x build_macos.sh

# Запустите сборку
./build_macos.sh
```

Скрипт автоматически:
1. ✅ Проверит `.venv` (пересоздаст, если он от Windows)
2. ✅ Установит все зависимости
3. ✅ Соберет .app с PyInstaller
4. ✅ Создаст DMG инсталлятор
5. ✅ Вычислит SHA256 хеш

> **💡 Совет:** Если у вас уже есть `.venv` от Windows, скрипт автоматически обнаружит это и пересоздаст его для macOS.

После завершения вы получите:
- `dist/AllManagerC.app` - готовое приложение
- `dist/AllManagerC_Installer_v5.6.0.dmg` - инсталлятор для распространения

#### Ручная сборка

Подробные инструкции по ручной сборке, подписанию и нотаризации см. в [BUILD_MACOS.md](BUILD_MACOS.md)

#### Публикация релиза

```bash
# 1. Создайте тег версии
git tag -a v5.6.0 -m "Release version 5.6.0"
git push origin v5.6.0

# 2. Создайте GitHub Release (требуется GitHub CLI)
gh release create v5.6.0 \
    dist/AllManagerC_Installer_v5.6.0.dmg \
    --title "AllManagerC v5.6.0" \
    --notes-file CHANGELOG.md

# 3. Обновите README.md с SHA256 хешем из вывода build_macos.sh
```

#### Хранение данных на macOS

После установки через DMG:

- **Приложение**: `/Applications/AllManagerC.app`
- **Пользовательские данные**: `~/Library/Application Support/AllManagerC/`
  - Конфигурация: `~/Library/Application Support/AllManagerC/config.json`
  - Данные: `~/Library/Application Support/AllManagerC/data/`
  - Ключи: `~/Library/Application Support/AllManagerC/.env`

## ❓ Решение проблем

### Windows: Ошибка активации виртуального окружения

**Проблема:** При активации `.venv\Scripts\activate` появляется ошибка "could not be loaded"

**Решение:**
```powershell
# Используйте правильный скрипт для PowerShell:
.\.venv\Scripts\Activate.ps1

# Или для CMD:
.venv\Scripts\activate.bat
```

### Windows: Ошибка "execution of scripts is disabled"

**Проблема:** PowerShell блокирует выполнение скриптов

**Решение:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Виртуальное окружение не существует

**Проблема:** Ошибка "The term '.\venv\Scripts\Activate.ps1' is not recognized"

**Решение:**
```bash
# Создайте виртуальное окружение:
# Windows:
python -m venv .venv
# macOS/Linux:
python3 -m venv .venv
```

### Использование .venv вместо venv

В этом проекте используется папка `.venv` (с точкой) вместо `venv`. Убедитесь, что все команды используют `.venv`:
- Активация: `.\.venv\Scripts\Activate.ps1` (Windows)
- Активация: `source .venv/bin/activate` (macOS/Linux)

**⚠️ Важно:** Виртуальные окружения специфичны для платформы! `.venv` от Windows не работает на macOS и наоборот.
- `.venv` уже в `.gitignore` и не попадает в git
- При переходе между платформами нужно пересоздать `.venv`
- Скрипт `build_macos.sh` автоматически обнаруживает это и пересоздает окружение

### Проверка окружения разработки

Используйте скрипт `check_env.py` для диагностики:

```bash
# Windows
python check_env.py

# macOS/Linux
python3 check_env.py
```

Скрипт проверит и покажет:
- 🖥️ Операционную систему и архитектуру
- 🐍 Версию Python и путь к интерпретатору
- 📦 Статус виртуального окружения (активно/неактивно)
- 📚 Установленные зависимости и их версии
- ⚙️ Конфигурационные файлы проекта
- 🔀 Статус git и `.gitignore`
- 💡 Рекомендации по исправлению проблем

### Ошибка "did not find executable at python.exe"

**Проблема:** При установке зависимостей появляется ошибка "did not find executable at 'C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe'"

**Причина:** Виртуальное окружение было создано со старой установкой Python, которая больше не доступна

**Решение:** Пересоздайте виртуальное окружение:
```powershell
# Выйдите из виртуального окружения (закройте терминал или откройте новый)
# Удалите старое виртуальное окружение
Remove-Item -Path .venv -Recurse -Force

# Создайте новое
python -m venv .venv

# Активируйте его
.\.venv\Scripts\Activate.ps1

# Установите зависимости
pip install -r requirements.txt
```

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции (`git checkout -b feature/amazing-feature`)
3. Зафиксируйте изменения (`git commit -m 'Add amazing feature'`)
4. Отправьте в ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

### Правила разработки

- Следуйте PEP 8 для Python кода
- Добавляйте комментарии к новым функциям
- Обновляйте документацию при изменении API
- Тестируйте изменения перед отправкой

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл [LICENSE](LICENSE) для получения дополнительной информации.

## 🙏 Благодарности

- [Flask](https://flask.palletsprojects.com/) - веб-фреймворк
- [Yubico](https://www.yubico.com/) - аутентификация
- [Bootstrap](https://getbootstrap.com/) - UI компоненты
- [Cryptography](https://cryptography.io/) - шифрование

## 📞 Поддержка

- 📧 Email: support@example.com
- 🐛 Issues: [GitHub Issues](https://github.com/your-username/ai-manager/issues)
- 📖 Документация: [Wiki](https://github.com/your-username/ai-manager/wiki)

---

⭐ Если проект вам понравился, поставьте звезду на GitHub! 

## Одновременный запуск нескольких приложений

Начиная с v5.5.4, приложение автоматически выбирает свободный локальный порт (предпочитая 5050/5051/5060/5070/5080) и использует уникальное имя cookie сессии `allmanager_session`. Это позволяет запускать одновременно, например, `AllManager.app` и `VPNServer.app`, без конфликтов портов и "перемешивания" сессий.

## 📦 Новые возможности в v5.6.0

- ✅ Улучшенная документация по сборке Windows-инсталлятора с Inno Setup
- ✅ Обновлены все команды для работы с виртуальным окружением `.venv`
- ✅ Добавлен раздел "Решение проблем" с типичными ошибками
- ✅ Полная поддержка PowerShell команд для Windows
- ✅ Обновлены зависимости до последних версий 

## Установка и где хранятся данные

- Windows (инсталлятор):
  - Сборка: соберите приложение PyInstaller командой (см. `build_windows.py`), затем запустите сборку инсталлятора Inno Setup, открыв `AllManagerC.iss` в Inno Setup Compiler и нажав Build.
  - Путь установки по умолчанию: `C:\Program Files\AllManagerC`.
  - Пользовательские данные (не удаляются при удалении программы):
    - Конфиг и служебные файлы: `%APPDATA%\AllManagerC\` (например: `C:\Users\<User>\AppData\Roaming\AllManagerC\`)
    - Активный файл данных: `%APPDATA%\AllManagerC\data\ai_services*.enc`
    - Загрузки (иконки, чеки): `%APPDATA%\AllManagerC\uploads\`
    - `.env` при необходимости также можно хранить здесь.
  - PIN разработчика и Secret PIN:
    - Считывается из переменных окружения `DEV_PIN`/`DEVELOPER_PIN` либо из `%APPDATA%\AllManagerC\config.json` в `security.secret_pin.current_pin` (при смене PIN этот ключ обновляется автоматически).

- macOS (для справки):
  - Данные хранятся в `~/Library/Application Support/AllManagerC/` (если вы собираете .app). 