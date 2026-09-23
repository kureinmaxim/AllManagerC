# Инструкция по запуску приложения в терминале

Этот файл содержит основные команды для работы с проектом через терминал на macOS.

## Основные команды

### 1. Переход в директорию проекта

Прежде всего, вам нужно перейти в папку с проектом. Скопируйте и вставьте эту команду в терминал:

```bash
cd /Users/olgazaharova/Project/ProjectPython/AiManage
```

### 2. Активация виртуального окружения

Для корректной работы приложения необходимо активировать виртуальное окружение.

```bash
source venv/bin/activate
```
После активации вы увидите `(venv)` в начале строки терминала.

### 3. Запуск приложения

После активации окружения, используйте одну из следующих команд для запуска приложения:

#### Запуск с GUI окном (рекомендуется):
```bash
python3 run_app.py
```

#### Запуск только веб-сервера (без GUI):
```bash
python3 app.py
```

**Примечание**: `app.py` может сразу закрываться в режиме разработки из-за проблем с GUI. Используйте `run_app.py` для стабильной работы с GUI окном.

---

## Единая команда для запуска

Вы можете объединить все шаги в одну команду для быстрого запуска:

#### С GUI окном (рекомендуется):
```bash
cd /Users/olgazaharova/Project/ProjectPython/AiManage && source venv/bin/activate && python3 run_app.py
```

#### Только веб-сервер:
```bash
cd /Users/olgazaharova/Project/ProjectPython/AiManage && source venv/bin/activate && python3 app.py
```

---

## Управление зависимостями

### Установка новых пакетов

Если нужно установить дополнительные пакеты Python:

```bash
source venv/bin/activate && pip install название_пакета
```

### Обновление списка зависимостей

После установки новых пакетов обновите requirements.txt:

```bash
source venv/bin/activate && pip freeze > requirements.txt
```

### Установка всех зависимостей из requirements.txt

При первой настройке или после клонирования проекта:

```bash
source venv/bin/activate && pip install -r requirements.txt
```

---

## Работа с данными

### Создание ключа шифрования

Если файл `.env` отсутствует, создайте новый ключ шифрования:

```bash
python3 -c "from cryptography.fernet import Fernet; print('SECRET_KEY=' + Fernet.generate_key().decode())" > .env
```

### Просмотр текущего ключа

Чтобы увидеть ваш текущий ключ шифрования:

```bash
cat .env
```

### Проверка данных

Для расшифровки и просмотра данных используйте встроенную утилиту:

```bash
source venv/bin/activate && python3 decrypt_tool.py
```

### Просмотр схемы данных AI-сервисов

Для изучения структуры данных AI-сервисов:

```bash
source venv/bin/activate && python3 ai_services_viewer.py
```

---

## Полезные команды для разработки

### Просмотр структуры проекта

```bash
tree -I 'venv|__pycache__|*.pyc|.git' -a
```

Если `tree` не установлена:

```bash
find . -type f -not -path "./venv/*" -not -path "./.git/*" -not -name "*.pyc" | head -20
```

### Поиск файлов

Найти все `.html` файлы:

```bash
find . -name "*.html" -not -path "./venv/*"
```

Найти все файлы с данными:

```bash
find . -name "*.enc" -o -name "*.json" -not -path "./venv/*"
```

### Проверка синтаксиса Python

```bash
source venv/bin/activate && python3 -m py_compile app.py
```

---

## Сборка приложения

### Сборка для macOS

```bash
source venv/bin/activate && python3 build_macos.py
```

### Установка PyInstaller (если не установлен)

```bash
source venv/bin/activate && pip install pyinstaller
```

---

## Работа с Git

### Статус изменений

```bash
git status
```

### Просмотр изменений

```bash
git diff
```

### Фиксация изменений

```bash
git add .
git commit -m "Описание изменений"
```

### Просмотр истории

```bash
git log --oneline | head -10
```

---

## Диагностика и отладка

### Проверка портов

Проверить, свободен ли порт 5050:

```bash
lsof -i :5050
```

### Завершение процессов на порту

Если порт занят:

```bash
lsof -ti:5050 | xargs kill -9
```

### Просмотр логов

Если приложение запущено с выводом в файл:

```bash
tail -f app.log
```

### Проверка места на диске

```bash
df -h
du -sh *
```

---

## Полезные алиасы

Добавьте эти строки в `~/.zshrc` для быстрого доступа:

```bash
# AI Manager
alias ai-cd='cd /Users/olgazaharova/Project/ProjectPython/AiManage'
alias ai-run='cd /Users/olgazaharova/Project/ProjectPython/AiManage && source venv/bin/activate && python3 run_app.py'
alias ai-run-web='cd /Users/olgazaharova/Project/ProjectPython/AiManage && source venv/bin/activate && python3 app.py'
alias ai-build='cd /Users/olgazaharova/Project/ProjectPython/AiManage && source venv/bin/activate && python3 build_macos.py'
alias ai-key='cd /Users/olgazaharova/Project/ProjectPython/AiManage && cat .env'
alias ai-data='cd /Users/olgazaharova/Project/ProjectPython/AiManage && source venv/bin/activate && python3 decrypt_tool.py'
alias ai-schema='cd /Users/olgazaharova/Project/ProjectPython/AiManage && source venv/bin/activate && python3 ai_services_viewer.py'
```

После добавления выполните:

```bash
source ~/.zshrc
```

Теперь вы можете использовать короткие команды:
- `ai-cd` - перейти в папку проекта
- `ai-run` - запустить приложение с GUI окном (рекомендуется)
- `ai-run-web` - запустить только веб-сервер (без GUI)
- `ai-build` - собрать приложение
- `ai-key` - показать ключ шифрования
- `ai-data` - просмотреть данные AI-сервисов
- `ai-schema` - показать схему данных

---

## Дополнительные команды

### Остановка приложения

Для остановки приложения, запущенного в терминале, просто нажмите комбинацию клавиш:

```
Ctrl + C
```

### Очистка терминала

```bash
clear
```

### Информация о системе

```bash
system_profiler SPSoftwareDataType | grep "System Version"
python3 --version
pip --version
```

---

## Новые функции

### Поддержка тем интерфейса

Приложение теперь поддерживает переключение между светлой и темной темой через значок в верхней панели. Выбранная тема сохраняется автоматически.

### Изменение масштаба интерфейса

Приложение теперь поддерживает изменение масштаба интерфейса (80%, 90%, 100%) через значок лупы в верхней панели.

### Импорт из другой установки

Новая функция позволяет импортировать данные AI-сервисов из других установок с использованием внешнего ключа шифрования. Доступна в разделе "Настройки".

### Улучшенная система экспорта

Доступны три варианта экспорта:
- **Экспорт данных** - только AI-сервисы (.enc файл)
- **Экспорт ключа** - только ключ шифрования (.env файл)
- **Полный экспорт** - ZIP архив с данными, ключом и файлами

### Исправления YubiKey (v4.3.5)

- ✅ Исправлена ошибка "Internal Server Error" при повторной проверке YubiKey
- ✅ Добавлена зависимость `yubico-client>=1.13.0`
- ✅ Создан стабильный скрипт запуска `run_app.py`
- ✅ Исправлены синтаксические ошибки в `app.py`
- ✅ Улучшена стабильность GUI окна

---

## Решение проблем

### Проблема с правами доступа

```bash
chmod +x venv/bin/activate
```

### Переустановка виртуального окружения

```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Проблемы с PyWebView на macOS

```bash
source venv/bin/activate && pip install --upgrade pywebview
```

### Проблемы с криптографией

Если возникают ошибки с криптографией:

```bash
source venv/bin/activate && pip install --upgrade cryptography
```

### Сброс данных (ОСТОРОЖНО!)

Для полного сброса данных AI-сервисов (удаляет все сервисы):

```bash
rm data/ai_services.json.enc*
```

**ВНИМАНИЕ:** Эта команда необратимо удаляет все ваши AI-сервисы!

### Проблемы с YubiKey

Если возникают ошибки "Internal Server Error" при работе с YubiKey:

1. **Проверьте зависимости**:
```bash
source venv/bin/activate && pip install "yubico-client>=1.13.0"
```

2. **Используйте правильный скрипт запуска**:
```bash
python3 run_app.py  # вместо python3 app.py
```

3. **Проверьте синтаксис**:
```bash
source venv/bin/activate && python3 -c "import app; print('✅ Синтаксис корректен')"
```

### Восстановление удаленных файлов

Если случайно удалили `app.py`:

```bash
git restore app.py
```

## 📚 ДОПОЛНИТЕЛЬНАЯ ДОКУМЕНТАЦИЯ

- `QUICK_DEBUG.md` - краткое руководство по быстрой отладке
- `DEBUG_GUIDE.md` - подробное руководство по отладке через браузер
- `FINAL_DIAGNOSIS.md` - детальный диагноз проблем и план действий
- `memory-bank/tasks.md` - задачи и прогресс разработки
- `BUILD.md` - инструкции по сборке приложения

Для получения дополнительной помощи обратитесь к документации проекта или справке в приложении. 