# Instagram Telegram Scraper

A Python tool that scrapes Instagram profiles from hashtags and extracts Telegram links using Selenium and PyQt5 GUI.

![App Screenshot](https://i.imgur.com/CYNMQ6n.png)

## Table of Contents
- [Features](#features)
- [Technical Stack](#technical-stack)
- [Installation](#installation)
- [Usage](#usage)
- [Output](#output)
- [Disclaimer](#disclaimer)
- [Русская Версия](#русская-версия)

## Features

- 🖥️ **Graphical Interface**: User-friendly PyQt5 GUI with progress tracking
- 🔒 **Account Rotation**: Automatic switching between multiple accounts to prevent blocking
- 📊 **Real-time Monitoring**: Live progress updates for both posts and profiles
- 🧩 **Session Recovery**: Resume interrupted scraping sessions
- 👻 **Headless Mode**: Option to run without browser GUI
- 📂 **Auto-saving**: Results saved to `profiles.txt` and `telegram.txt`

## Technical Stack

- **Python 3.7+**
- **Selenium 4.0+** (Web automation)
- **PyQt5** (GUI framework)
- **Multi-threading** for responsive UI

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/TheBatmanCoder/TelegramInstagramParser
   cd TelegramInstagramParser
   ```

2. Update Selenium to latest version:
   ```bash
   python -m pip install --upgrade selenium
   ```

3. Add your Instagram accounts to uid.txt (one per line, format: username:password)

Note: The script automatically handles ChromeDriver installation - no manual setup needed.

## Usage

1. Launch the application:
   ```bash
   python parser.py
   ```

2. Configure your search:
   - Enter target hashtag (without #)
   - Set scroll count (1-20 recommended)
   - Toggle headless mode if needed

3. Start scraping:
   - Click "Start" button
   - View real-time logs in the GUI
   - Results appear as they're found

4. Completion:
   - Results automatically save when finished
   - Can safely stop and resume later

## Output

Two output files are generated:

1. instagram_[hashtag]_profiles.txt
   Contains all discovered Instagram profile URLs

2. instagram_[hashtag]_telegram.txt
   Contains all extracted Telegram links (t.me/...)

## Disclaimer

This tool is for educational purposes only. Use it responsibly and respect Instagram's Terms of Service. The developers are not responsible for any misuse of this tool.

# Русская Версия

Инструмент на Python для сбора профилей Instagram из хэштегов и извлечения ссылок на Telegram с использованием Selenium и графического интерфейса PyQt5.

## Возможности

- 🖥️ **Графический Интерфейс**: Удобный интерфейс PyQt5 с отслеживанием прогресса
- 🔒 **Ротация Аккаунтов**: Автоматическое переключение между несколькими аккаунтами для предотвращения блокировки
- 📊 **Мониторинг в Реальном Времени**: Обновления прогресса для постов и профилей
- 🧩 **Восстановление Сессии**: Возможность продолжить прерванный сбор данных
- 👻 **Фоновый Режим**: Возможность работы без графического интерфейса браузера
- 📂 **Автосохранение**: Результаты сохраняются в `profiles.txt` и `telegram.txt`

## Технический Стек

- **Python 3.7+**
- **Selenium 4.0+** (Веб-автоматизация)
- **PyQt5** (Фреймворк для GUI)
- **Многопоточность** для отзывчивого интерфейса

## Установка

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/TheBatmanCoder/TelegramInstagramParser
   cd TelegramInstagramParser
   ```

2. Обновите Selenium до последней версии:
   ```bash
   python -m pip install --upgrade selenium
   ```

3. Добавьте ваши аккаунты Instagram в файл uid.txt (по одному на строку, формат: логин:пароль)

Примечание: Скрипт автоматически устанавливает ChromeDriver - ручная настройка не требуется.

## Использование

1. Запустите приложение:
   ```bash
   python parser.py
   ```

2. Настройте поиск:
   - Введите целевой хэштег (без #)
   - Установите количество прокруток (рекомендуется 1-20)
   - При необходимости включите фоновый режим

3. Начните сбор данных:
   - Нажмите кнопку "Старт"
   - Следите за логами в реальном времени
   - Результаты появляются по мере обнаружения

4. Завершение:
   - Результаты автоматически сохраняются
   - Можно безопасно остановить и продолжить позже

## Результаты

Создаются два выходных файла:

1. instagram_[hashtag]_profiles.txt
   Содержит все найденные URL профилей Instagram

2. instagram_[hashtag]_telegram.txt
   Содержит все извлеченные ссылки Telegram (t.me/...)

## Отказ от Ответственности

Этот инструмент предназначен только для образовательных целей. Используйте его ответственно и уважайте Условия использования Instagram. Разработчики не несут ответственности за любое неправильное использование этого инструмента.
