# 📊 TREND-SCANNER-GEO

[ English ] | [ Русский ]

**TREND-SCANNER-GEO** — это мощная консольная утилита на Python для автоматического анализа трендов, вирусных видео и конкурентной разведки на YouTube с привязкой к географическим регионам.

Инструмент работает на базе **YouTube Data API v3** и позволяет находить скрытые вирусные ролик с высокой скоростью набора просмотров, отсеивать нерелевантный контент и мгновенно экспортировать готовые аналитические отчеты.

---

## 🌐 README in English

### Key Features
* **Geographical Targeting:** Analyze trends and search results for 11 targeted regions (US, RU, GB, DE, JP, KZ, ES, MX, BR, AR, IN) with automatic region-channel filtering.
* **Dual Operating Modes:**
  * **Most Popular:** Fetches current YouTube charts for the selected region.
  * **Search by Keywords:** Batch search by topics/keywords with regional priority.
* **Smart Content Focus:**
  * **Popular:** Highest total view count.
  * **Gaining Popularity (Rising):** Finds fast-growing videos (published within the last 7 days) and ranks them by growth velocity.
* **Advanced Metrics & Metrics Calculation:**
  * **VPH (Views Per Hour):** Real-time hourly view gain.
  * **Views/Subscribers Ratio:** Detects outlier videos performing way above the channel's baseline.
  * **Growth Score (0–100):** Weighted velocity index that accounts for hidden metrics safely.
* **Multi-Format Export:** Automatic export into `output/` folder in **CSV** (UTF-8 BOM), **Markdown** (compatible with Notion & Obsidian), and **TXT** formats.
* **EXE Ready:** Fully compatible with PyInstaller, equipped with auto-pause on exit and fallback logging for protected folders.

---

### Quick Start & Installation

#### Requirements
* Python 3.9+
* YouTube Data API v3 Key ([How to get API Key](https://console.cloud.google.com/))

#### Installation
1. Clone or download this repository.
2. Install the required dependencies:
```bash
pip install google-api-python-client
```

#### Launching the Script
* **Via Python:**
```bash
python main_2.py
```
* **Environment Variable Support:** You can pass your key via `YOUTUBE_API_KEY` to skip manual input:
```bash
# Windows PowerShell
$env:YOUTUBE_API_KEY="YOUR_API_KEY"
python main_2.py
```

#### Building executable (.exe)
Build a single standalone `.exe` file using PyInstaller:
```bash
pip install pyinstaller
python -m PyInstaller --onefile main_2.py
```
The compiled executable will appear in the `dist/` folder.

---

## 🇷🇺 README на Русском

### Основные возможности
* **Географическая привязка (Гео):** Глубокий анализ трендов и выдачи для 11 ключевых регионов (США, Россия, Великобритания, Германия, Япония, Казахстан, Испания, Мексика, Бразилия, Аргентина, Индия) с гео-фильтрацией стран каналов.
* **Два режима работы:**
  * **Популярные видео (Most Popular):** Выгрузка официальных чартов YouTube выбранной страны.
  * **Поиск по ключевым запросам:** Массовый анализ тем с учетом регионального языка и приоритетов.
* **Умный фокус поиска:**
  * **Популярное:** Видео с максимальным количеством просмотров.
  * **Набирающее популярность (Rising):** Поиск быстрых «прорывов» (видео не старше 7 дней) с автоматическим ранжированием по скорости набора аудитории.
* **Углубленные метрики анализа:**
  * **VPH (Просмотры в час):** Динамика прироста просмотров в реальном времени.
  * **Просмотры / Подписчики:** Выявление аномально успешных роликов на небольших каналах.
  * **Индекс роста (Growth Score 0–100):** Авторский балансировочный индекс, адаптирующийся под скрытые лайки и подписчиков.
* **Тройной экспорт:** Автоматическое сохранение отчетов в папку `output/` в форматах **CSV** (с корректной кодировкой для Excel), **Markdown** (для Notion / Obsidian) и **TXT**.
* **Готов к сборке в EXE:** Учтены особенности работы с PyInstaller (автопауза консоли, безопасные логи, консольная кодировка UTF-8).

---

### Быстрый запуск и установка

#### Требования
* Python 3.9+
* API-ключ YouTube Data API v3 ([Инструкция по получению](https://console.cloud.google.com/))

#### Установка
1. Скачайте файлы проекта.
2. Установите необходимую библиотеку:
```bash
pip install google-api-python-client
```

#### Запуск программы
* **Через Python:**
```bash
python main_2.py
```
* **Переменная окружения (опционально):** Чтобы каждый раз не вводить ключ, задайте переменную `YOUTUBE_API_KEY`:
```bash
# Windows PowerShell
$env:YOUTUBE_API_KEY="ВАШ_API_КЛЮЧ"
python main_2.py
```

#### Сборка в `.exe` файл
Скомпилируйте скрипт в один файл для запуска без установленного Python:
```bash
pip install pyinstaller
python -m PyInstaller --onefile main_2.py
```
Готовый исполняемый файл появится в папке `dist/`.

---

## 👨‍💻 Developer & Contacts / Разработчик и контакты

* **Developer:** Pavel Muv
* **YouTube:** [@Pavel_Muv_Lab](https://www.youtube.com/@Pavel_Muv_Lab)
* **X (Twitter):** [@Pavel_muv](https://x.com/Pavel_muv)

---
`TREND-SCANNER-GEO | FIND. ANALYZE. GROW.`