# Сборка AllManagerC для этого Mac

Проверено 23 сентября 2026: macOS 26.6.2, Apple Silicon arm64,
Python 3.13.9, PyInstaller 6.16.0. Собираем объединённый проект из AiManage-Clean.

## 1. Проверить окружение

Из папки AiManage-Clean:

```bash
uname -m
xcode-select -p
.venv/bin/python -c 'import flask, webview, AppKit, WebKit, PIL, PyInstaller; print(PyInstaller.__version__)'
```

В этом проекте рабочее окружение `.venv` уже есть. Для нового Mac создайте его
и установите зависимости (добавка Qt на macOS не нужна):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install Flask requests python-dotenv cryptography Werkzeug Jinja2 pywebview yubico-client pyinstaller pillow
```

Нужны Xcode Command Line Tools и штатные `codesign`, `ditto`, `hdiutil`.
`create-dmg` не требуется. Текущий скрипт собирает arm64 для Apple Silicon.

## 2. Запустить тесты

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Тесты используют временные данные. В том числе проверяют сохранение ключа
и чтение базы после повторного запуска упакованного приложения.

## 3. Собрать приложение

Выберите новую папку результата; существующее приложение не перезаписывается:

```bash
bash build_macos.sh --stage app --output dist/macos-arm64-20260923
```

Для следующей сборки укажите другое имя папки. Можно выполнить оба этапа сразу
командой `bash build_macos.sh`: скрипт сам создаст папку с датой и временем.
Для другого Python задайте `BUILD_PYTHON=/путь/к/python` перед командой.

Результат — `dist/macos-arm64-20260923/AllManagerC.app`.

Скрипт `tools/build_macos.py`:

- создаёт `.icns` из GitHub-иконки `static/images/ALLc.png`;
- включает шаблоны, статику, схему и чистый конфиг;
- не включает `.env`, базы, загруженные файлы и настройки YubiKey;
- использует Cocoa/WebKit и исключает Qt;
- проверяет подпись через `codesign --verify --deep --strict`;
- сохраняет старые сборки и виртуальные окружения.

При работе из Codex PyInstaller может запросить разрешение на запись своего
кэша в `~/Library/Application Support/pyinstaller`. Это служебный кэш сборки.

## 4. Проверить запуск

```bash
open dist/macos-arm64-20260923/AllManagerC.app
```

Для проверки с отдельными пустыми данными можно запустить исполняемый файл:

```bash
ALLMANAGERC_DATA_DIR=/tmp/allmanagerc-test-profile \
  dist/macos-arm64-20260923/AllManagerC.app/Contents/MacOS/AllManagerC
```

Обычный запуск хранит данные и ключ в
`~/Library/Application Support/AllManagerC`. Первый запуск создаёт собственный
ключ; следующие должны использовать его повторно. Исходные базы обоих проектов
по-прежнему сохранены отдельно, их импорт пользователь отложил.

## 5. Создать DMG

После проверки приложения, с той же папкой результата:

```bash
bash build_macos.sh --stage dmg --output dist/macos-arm64-20260923
```

Результат: `AllManagerC_Installer_v5.6.0_arm64.dmg` и файл `.dmg.sha256` рядом.
Внутри образа — `AllManagerC.app` и ссылка на `/Applications`.

`hdiutil` требует доступа к системным устройствам дисковых образов. При ошибке
`Device not configured` в песочнице Codex разрешите выполнение вне песочницы.
Если подготовленная папка `dmg-content` уже создана, повторить только упаковку:

```bash
hdiutil create -volname 'AllManagerC 5.6.0' \
  -srcfolder dist/macos-arm64-20260923/dmg-content \
  -format UDZO -fs HFS+ \
  dist/macos-arm64-20260923/AllManagerC_Installer_v5.6.0_arm64.dmg
hdiutil verify dist/macos-arm64-20260923/AllManagerC_Installer_v5.6.0_arm64.dmg
shasum -a 256 dist/macos-arm64-20260923/AllManagerC_Installer_v5.6.0_arm64.dmg
```

## 6. Установка

Откройте DMG и перетащите AllManagerC в Applications. Если там уже есть старая
версия, сначала сохраните её, если нужен откат. Запустите приложение из Applications.

Сборка имеет локальную ad-hoc подпись PyInstaller. Developer ID и нотариальное
заверение Apple не выполнялись. Публикация GitHub Release — отдельное действие;
скрипт ничего не отправляет на GitHub.

## 7. Подготовить общий релиз Windows и macOS

Полезные сведения из прежнего QUICK_RELEASE_GUIDE.md перенесены сюда.
Платформы можно собирать в любом порядке. Для одной версии используйте один
Git-тег и один GitHub Release, добавляя в него инсталляторы обеих платформ.
Виртуальные окружения создаются отдельно на каждой системе и не попадают в Git.

Перед публичным релизом объединённого кода:

1. Выберите новый номер версии: локальная сборка пока использует 5.6.0 из конфигурации,
   но содержит более новые изменения. Не переиспользуйте старый опубликованный тег.
2. Согласуйте версию в `config.json`, Windows-инсталляторе `AllManagerC.iss`,
   резервных значениях версии в коде и документации.
3. Обновите `CHANGELOG.md` и подготовьте заметки о новом релизе.
4. Проверьте `git status` и diff; включите в коммит только предназначенные для
   публикации исходники. Личные ключи, базы и `.local-backups` остаются локальными.
5. Создайте аннотированный тег (`git tag -a`) на проверенном коммите.
   Сборки Windows и macOS должны соответствовать этому же коммиту.
6. Проверьте запуск и установку на целевых системах, сохраните SHA256 каждого файла.

Если часть платформ ещё не проверена, релиз можно оставить черновиком или
pre-release. Снимать этот статус следует после проверки всех обещанных сборок.

### Добавить DMG к существующему релизу

Через [страницу релизов проекта](https://github.com/kureinmaxim/AllManagerC/releases):
откройте нужный релиз, выберите Edit, добавьте DMG и файл `.sha256`, укажите
архитектуру arm64 и результаты проверки в описании. Ссылки и хеш обновите в README.

Через GitHub CLI, заменив значения на новый тег и фактический путь:

```bash
RELEASE_TAG=vX.Y.Z
DMG_PATH=dist/папка-сборки/AllManagerC_Installer_vX.Y.Z_arm64.dmg

gh release upload "$RELEASE_TAG" "$DMG_PATH" "$DMG_PATH.sha256"
# Только после завершения проверки всех обещанных платформ:
gh release edit "$RELEASE_TAG" --prerelease=false
```

Эти команды публикуют файлы; они не выполняются скриптом сборки автоматически.
Не используйте `--clobber`, если не намерены заменить уже опубликованный файл.

### Сопутствующая сборка Windows

Выполняется на Windows из того же коммита, со своим Python-окружением:

```powershell
python build_windows.py
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" AllManagerC.iss
```

Оператор `&` нужен PowerShell для запуска программы по пути с пробелами.
Затем добавьте Windows-инсталлятор к тому же релизу.

### Если виртуальное окружение не запускается

Перенесённое с Windows окружение на Mac не работает. Сохраните его при необходимости
и создайте отдельное, например `.venv-macos`, командами из шага 1. Запускайте сборку так:

```bash
BUILD_PYTHON=.venv-macos/bin/python bash build_macos.sh
```

Если отсутствует только pip, попробуйте `python -m ensurepip --upgrade` с Python
нужного окружения. Скрипт сборки больше не удаляет и не пересоздаёт окружения сам.

Связанные документы: [README](README.md), [CHANGELOG](CHANGELOG.md),
[работа на двух платформах](DEPLOYMENT.md).
