# Сборка AllManagerC на macOS

Сборка теперь не требует ручного ввода версии и имени папки. Версия берётся из `config.json`, проверяется скриптом контроля версий, а результат получает уникальное имя с версией, архитектурой и временем сборки.

## Быстрый запуск

После однократной настройки запускайте из корня проекта:

```bash
./build_macos.sh --open
```

Или откройте двойным щелчком `build_macos.command`. После успешной сборки Finder откроет папку результата.

В папке `dist` всегда остаётся понятная структура:

- `AllManagerC-<версия>-<архитектура>-<дата-время>/` — отдельный полный результат;
- `dist/latest` — ссылка на последнюю сборку с DMG;
- `dist/latest-app` — ссылка на последнюю успешно собранную `.app`;
- внутри результата находятся `.app`, DMG, SHA-256, `build-info.json` и `build.log`.

Старые папки не перезаписываются. Команда очистки удаляет старые результаты, но всегда сохраняет последнюю успешную сборку, на которую указывает `dist/latest`:

```bash
./build_macos.sh --clean
```

Если нужно удалить абсолютно все сборки, включая последнюю:

```bash
./build_macos.sh --clean-all
```

Команды удаляют только содержимое `dist`, созданное сборщиком, и не затрагивают исходники, `.venv`, базы или пользовательские данные.

## Однократная настройка

Нужны Xcode Command Line Tools и Python для этой архитектуры:

```bash
xcode-select --install
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-build-macos.txt
```

Если окружение находится в другом месте, задайте его явно:

```bash
BUILD_PYTHON=/path/to/python ./build_macos.sh --open
```

Проверка без сборки:

```bash
./build_macos.sh --check
```

## Режимы сборки

Обычная команда выполняет тесты, собирает приложение и создаёт DMG:

```bash
./build_macos.sh
```

Собрать только приложение можно так:

```bash
./build_macos.sh --stage app
```

После этого DMG создаётся без повторной сборки приложения:

```bash
./build_macos.sh --stage dmg
```

Этот режим использует `dist/latest-app`, поэтому путь и версию указывать не нужно. `--skip-tests` оставлен только для локальной диагностики; перед релизом его не используйте.

`--output` доступен для нестандартного сценария и должен указывать на пустую папку. Обычно он не нужен.

## Версия и релиз

Перед новой публикацией измените версию единой командой:

```bash
python3 scripts/version.py bump patch   # или minor, major, set X.Y.Z
python3 scripts/version.py check
```

Подробные правила синхронизации файлов находятся в [VERSION_MANAGEMENT.md](VERSION_MANAGEMENT.md). Сборка сама остановится при рассинхронизации.

Для создания релиза GitHub используйте имя DMG и хеш из `dist/latest/build-info.json`; пример загрузки без ручного набора версии:

```bash
RELEASE_TAG=$(python3 -c 'import json; print("v" + json.load(open("config.json"))["app_info"]["version"])')
DMG_PATH=$(python3 -c 'import json, pathlib; p=pathlib.Path("dist/latest"); print(p / json.loads((p / "build-info.json").read_text())["dmg"])')
gh release upload "$RELEASE_TAG" "$DMG_PATH" "$DMG_PATH.sha256"
```

Публикация в GitHub не выполняется автоматически.

## Проверка и установка

Откройте приложение из последнего результата:

```bash
open dist/latest/AllManagerC.app
```

В DMG перетащите `AllManagerC.app` в `Applications`. Подпись сборки локальная ad-hoc: нотариальное заверение Apple и Developer ID не используются.

Сборка не включает `.env`, базы, ключи, настройки YubiKey или другие личные данные. Они остаются в `~/Library/Application Support/AllManagerC`.

## Если сборка прервалась

Подробности находятся в `build.log` папки текущего результата. Незавершённая сборка не меняет `dist/latest`. Если ошибка произошла на упаковке DMG, повторите:

```bash
./build_macos.sh --stage dmg
```

Временные файлы находятся в `build/macos` и удаляются автоматически. Для ошибки `hdiutil: Device not configured` запустите сборку в обычном локальном терминале и повторите упаковку DMG.

Сборка Windows выполняется отдельно по [DEPLOYMENT.md](DEPLOYMENT.md); обе платформы должны использовать один Git-тег.
