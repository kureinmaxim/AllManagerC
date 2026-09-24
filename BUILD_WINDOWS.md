# Сборка AllManagerC на Windows

Сборка полностью автоматизирована: версия читается из `config.json`, имя папки и установщика создаются автоматически. Вручную менять версию в `AllManagerC.iss` не требуется.

## Однократная настройка

Установите Python 3.11+ и [Inno Setup 6](https://jrsoftware.org/isinfo.php). Затем откройте PowerShell в корне проекта:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Если Inno Setup установлен не в стандартный каталог, укажите путь к компилятору:

```powershell
$env:ISCC = 'D:\Tools\Inno Setup 6\ISCC.exe'
```

## Проверка окружения

```powershell
.\.venv\Scripts\python.exe build_windows.py --check
```

Команда проверяет синхронизацию версии во всех файлах. Сборка остановится, если версии различаются.

## Сборка

```powershell
.\.venv\Scripts\python.exe build_windows.py
```

Скрипт выполняет PyInstaller, запускает Inno Setup и создаёт результат в новой папке:

```text
dist\AllManagerC-<версия>-windows-<дата-время>\
├── app\
├── AllManagerC_Installer_v<версия>.exe
└── build-info.json
```

Папка `dist\latest` содержит копию последней успешной сборки. Для установки запускайте EXE из этой папки или из папки конкретного релиза.

## Обслуживание папки dist

Удалить старые результаты, сохранив последний:

```powershell
.\.venv\Scripts\python.exe build_windows.py --clean
```

Удалить все созданные Windows-артефакты:

```powershell
.\.venv\Scripts\python.exe build_windows.py --clean-all
```

Команды работают только с `dist` и не затрагивают исходники, `.venv`, пользовательские базы или настройки приложения.

## Новая версия

Перед публикацией новой версии:

```powershell
py -3 scripts/version.py bump patch
py -3 scripts/version.py check
.\.venv\Scripts\python.exe build_windows.py
```

Вместо `patch` можно использовать `minor`, `major` или задать версию явно через `scripts/version.py set X.Y.Z`. Windows и macOS для одного релиза собирайте из одного Git-коммита и используйте один тег.

## Установка и проверка

Запустите `AllManagerC_Installer_v<версия>.exe`, выберите установку ярлыка на рабочем столе при необходимости и после завершения запустите приложение из меню Пуск. Пользовательские данные сохраняются в `%APPDATA%\AllManagerC` и не удаляются при деинсталляции.

Сборка включает иконку приложения из `static\images\icon.ico`, шаблоны, статику, переводы и схему данных. `.env`, базы, ключи и настройки YubiKey в установщик не включаются.

## Диагностика

Если не найден Inno Setup, установите Inno Setup 6 или задайте `$env:ISCC`. Если не найден Python, создайте окружение заново командами настройки. Логи PyInstaller и временные файлы находятся в `build`; их можно удалить после завершения сборки.

Для запуска из исходников используйте [DEPLOYMENT.md](DEPLOYMENT.md). Правила версий описаны в [VERSION_MANAGEMENT.md](VERSION_MANAGEMENT.md).
