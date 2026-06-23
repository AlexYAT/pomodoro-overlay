# Pomodoro Overlay Timer

Полупрозрачный Pomodoro-таймер в виде плавающего окна поверх всех приложений.  
Python 3.11+, [PySide6](https://pypi.org/project/PySide6/) (Qt6), без лишних зависимостей.

## Возможности

- **Режимы:** Work / Short Break / Long Break (по умолчанию 25 / 5 / 15 минут)
- **Циклы:** после N рабочих сессий — длинный перерыв (N настраивается, по умолчанию 4)
- **Управление:** Start / Pause / Reset / Skip; автопереход между режимами (опционально)
- **Окно:** frameless, always-on-top, полупрозрачность, закруглённые углы, перетаскивание, ресайз по углу
- **Кольцо прогресса:** от 12 часов по часовой стрелке, показывает «сколько прошло» (0..100%)
- **Клик по окну** — start/pause; **автозапуск** только для перерывов
- **После перерыва:** показ времени следующего помодорo, моргание окна, полная непрозрачность до старта
- **Горячие клавиши (в фокусе окна):** Space — start/pause, R — reset, S — skip, Esc — скрыть окно
- **Меню:** сброс всех счётчиков (новый день без перезапуска)
- **Настройки:** длительности, N для long break, авто-переход, прозрачность (превью), размер (S/M/L), click-through (Windows)
- **Уведомления:** системный трей + звук при старте и завершении сессии

## Скачать (portable, Windows)

Собранный **один файл** `PomodoroOverlay.exe` — в [Releases](https://github.com/AlexYAT/pomodoro-overlay/releases) на GitHub.

Либо соберите сами:

```powershell
build_portable.cmd
```

Результат: `dist\PomodoroOverlay.exe` — не требует установки Python, можно положить в любую папку и запускать.

## Быстрый старт (из исходников)

```bash
git clone https://github.com/AlexYAT/pomodoro-overlay.git
cd pomodoro-overlay
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
python main.py
```

**Windows:** двойной клик по `run.cmd` (после создания `.venv` и `pip install`).  
Если не запускается — `run_debug.cmd` покажет ошибку в консоли.

## Скрытие и показ окна

По **Esc** окно скрывается, приложение остаётся в трее:

- **Двойной клик** по иконке в трее, или  
- **ПКМ** → **Show**

## Горячие клавиши

| Клавиша | Действие |
|---------|----------|
| Space | Start / Pause |
| R | Сброс текущей сессии |
| S | Skip (следующий режим) |
| Esc | Скрыть окно |
| ПКМ | Контекстное меню |

## Сборка portable exe

```powershell
pip install -r requirements.txt -r requirements-dev.txt
pyinstaller pomodoro.spec --noconfirm --clean
```

Или: `build_portable.cmd`

**macOS (app bundle):**

```bash
pip install pyinstaller
pyinstaller --windowed --name "Pomodoro Overlay" \
  --add-data "resources:resources" \
  main.py
```

## Публикация релиза

Исходный код хранится в этом репозитории. Готовый `PomodoroOverlay.exe` публикуется как asset [GitHub Release](https://github.com/AlexYAT/pomodoro-overlay/releases) и **не коммитится** в Git (каталог `dist/` в `.gitignore`).

Сборка для maintainer:

1. `build_portable.cmd` → `dist\PomodoroOverlay.exe`
2. GitHub → **Releases** → создать тег и прикрепить exe (+ `checksums.txt` с SHA-256)

## Принципы проекта

- Один локальный пользователь — приложение для личного использования (dogfooding).
- Работа без аккаунта и без интернета после установки/скачивания.
- Без рекламы, телеметрии и фоновых сервисов после закрытия.
- Минимум зависимостей (PySide6 + стандартная библиотека Python).
- Portable Windows exe — один файл, без установщика.
- Новые функции добавляются только при подтверждённой личной необходимости.

## Структура проекта

| Файл | Назначение |
|------|------------|
| `main.py` | Точка входа, трей, уведомления, звук |
| `timer_engine.py` | Логика таймера (`time.monotonic()`, без Qt) |
| `overlay_window.py` | Overlay-окно, кольцо, drag/resize, горячие клавиши |
| `settings.py` | QSettings, геометрия и настройки |
| `settings_dialog.py` | Диалог настроек |
| `pomodoro.spec` | Сборка PyInstaller (one-file) |
| `resources/` | Опционально: `icon.png`, `complete.wav` |
| `tests/` | Тесты `timer_engine` |

## Тесты

```bash
python -m unittest discover -s tests -v
```

## Ограничения платформ

- **Click-through:** только Windows (`WA_TransparentForMouseEvents`)
- **Системный трей:** зависит от ОС; без трея остаётся визуальная пульсация кольца

## Точность таймера

Время считается по `time.monotonic()`; `QTimer` только обновляет UI (~15 fps). Пауза и работа в фоне не накапливают дрейф.

## Лицензия

[MIT](LICENSE) — свободное использование, изменение и распространение с сохранением уведомления об авторских правах.
