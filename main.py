# -*- coding: utf-8 -*-
import os
import sys
import csv
import re
import math
import logging
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Поддержка UTF-8 в консоли
for stream in (sys.stdin, sys.stdout, sys.stderr):
    if stream is not None and hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Папка программы: рядом с EXE (PyInstaller) или рядом с main.py
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent


def setup_logging():
    """Лог рядом с программой; если папка защищена от записи — во временную папку."""
    candidates = [BASE_DIR / "trend_scanner_geo.log",
                  Path(tempfile.gettempdir()) / "trend_scanner_geo.log"]
    for path in candidates:
        try:
            logging.basicConfig(
                filename=str(path),
                level=logging.ERROR,
                format="%(asctime)s %(levelname)s %(message)s",
                encoding="utf-8",
            )
            return
        except OSError:
            continue
    logging.basicConfig(level=logging.ERROR)


setup_logging()

DEVELOPER = "Pavel Muv"
CONTACTS = [
    ("YouTube", "https://www.youtube.com/@Pavel_Muv_Lab"),
    ("X", "https://x.com/Pavel_muv"),
]

EXIT_WORDS = {"0", "exit", "quit", "q", "выход", "в"}
API_KEY_ENV = "YOUTUBE_API_KEY"

# Стоимость вызовов YouTube Data API v3 (в единицах квоты)
SEARCH_COST = 100     # search().list
LIST_COST = 1         # videos().list / channels().list / videoCategories().list
DAILY_QUOTA = 10_000  # стандартная суточная квота
MAX_PAGES = 2
API_RETRIES = 3
TRENDS_MAX_CANDIDATES = 500  # верхняя граница; цикл остановится раньше, если нет nextPageToken
# Что искать: 1 — популярное (много просмотров), 2 — набирающее популярность (быстрый рост)
FOCUS_CHOICES = {"1": "popular", "2": "rising"}
# Порядки сортировки поиска для каждого режима
SEARCH_ORDERS_BY_FOCUS = {
    "popular": ("viewCount",),
    "rising": ("date", "viewCount"),  # оба прохода — только по свежим видео (см. RISING_WINDOW_DAYS)
}
# Набирающее популярность: видео не старше N дней и не меньше N просмотров (отсев шума)
RISING_WINDOW_DAYS = 7
MIN_VIEWS_RISING = 100

# Доля видео, получающих метки Popular / Trending (топ 20%)
LABEL_SHARE = 0.2
# Минимальный возраст (в часах) для расчёта VPH, чтобы свежие видео не давали выбросов
MIN_AGE_HOURS_FOR_VPH = 1.0
REGIONS = {
    "1": {"code": "US", "name_ru": "США (US)", "name_en": "United States (US)"},
    "2": {"code": "RU", "name_ru": "Россия (RU)", "name_en": "Russia (RU)"},
    "3": {"code": "GB", "name_ru": "Великобритания (GB)", "name_en": "United Kingdom (GB)"},
    "4": {"code": "DE", "name_ru": "Германия (DE)", "name_en": "Germany (DE)"},
    "5": {"code": "JP", "name_ru": "Япония (JP)", "name_en": "Japan (JP)"},
    "6": {"code": "KZ", "name_ru": "Казахстан (KZ)", "name_en": "Kazakhstan (KZ)"},
    "7": {"code": "ES", "name_ru": "Испания (ES)", "name_en": "Spain (ES)"},
    "8": {"code": "MX", "name_ru": "Мексика (MX)", "name_en": "Mexico (MX)"},
    "9": {"code": "BR", "name_ru": "Бразилия (BR)", "name_en": "Brazil (BR)"},
    "10": {"code": "AR", "name_ru": "Аргентина (AR)", "name_en": "Argentina (AR)"},
    "11": {"code": "IN", "name_ru": "Индия (IN)", "name_en": "India (IN)"},
}

# Язык для relevanceLanguage в поиске (подсказка YouTube, а не жёсткий фильтр)
REGION_LANG = {
    "US": "en", "RU": "ru", "GB": "en", "DE": "de", "JP": "ja", "KZ": "ru",
    "ES": "es", "MX": "es", "BR": "pt", "AR": "es", "IN": "hi",
}

TEXT = {
    "ru": {
        "title": "TREND-SCANNER-GEO",
        "api_key": "Введите API-ключ YouTube Data API v3",
        "api_key_env": f"API-ключ взят из переменной окружения {API_KEY_ENV}.",
        "checking": "Проверка API-ключа...",
        "api_ok": "API-ключ работает.",
        "api_error": "Не удалось подключиться к YouTube API.",
        "bye": "Работа завершена. До встречи!",
        "count": "Количество результатов (1–50)",
        "region_menu": "Выберите регион (гео) для анализа:",
        "mode_menu": (
            "Выберите режим работы:\n"
            "  1 — Популярные видео (Most Popular)\n"
            "  2 — Поиск по ключевым запросам"
        ),
        "query_prompt": "Введите поисковые запросы через запятую или с новой строки (0 — выход)",
        "searching": "Поиск видео и сбор статистики...",
        "progress_videos": "Получение данных видео",
        "progress_channels": "Получение данных каналов",
        "progress_trends": "Получение трендов",
        "done": "ГОТОВО! АНАЛИЗ ЗАВЕРШЁН",
        "follow": "Больше полезного — в моих соцсетях",
        "brand_line": "TREND-SCANNER-GEO  |  FIND. ANALYZE. GROW.",
        "found": "Найдено уникальных видео",
        "selected": "Видео после обработки",
        "saved_to": "Сохранено в папку",
        "preview": "ИТОГИ ПОИСКА",
        "setup": "НАСТРОЙКА АНАЛИЗА",
        "live_progress": "ХОД РАБОТЫ",
        "empty": "Подходящих видео не найдено.",
        "unknown": "Неизвестно",
        "popular": "Popular",
        "trending": "Trending",
        "published": "Дата публикации",
        "duration": "Длительность",
        "views": "Просмотры",
        "likes": "Лайки",
        "comments": "Комментарии",
        "channel": "Канал",
        "subs": "Подписчики",
        "age": "Возраст, дней",
        "vph": "Средние просмотры в час",
        "ratio": "Просмотры / подписчики",
        "score": "Индекс роста",
        "popularity_label": "Категория",
        "developer": "Разработчик",
        "contacts": "Контакты",
        "invalid": "Некорректный ввод.",
        "no_results": "Попробуйте изменить параметры или запросы.",
        "quota_exceeded": "Квота YouTube Data API на сегодня исчерпана.",
        "key_rejected": "Ключ отклонён или доступ запрещён.",
        "chart_unavailable": "Для этого региона список трендов сейчас недоступен. Выберите другой регион.",
        "unexpected": "Произошла непредвиденная ошибка (подробности в логе).",
        "mode_trends": "Популярные видео",
        "mode_search": "Поиск",
        "trends_collect": "Сбор трендов для региона",
        "query_label": "Запрос",
        "saving": "Сохранение файлов...",
        "files": "ФАЙЛЫ",
        "quota_estimate": "Ориентировочный расход квоты",
        "quota_of": "из суточных",
        "col_views": "ПРОСМ.",
        "col_vph": "ПРОСМ./Ч",
        "col_dur": "ДЛИТ.",
        "col_channel": "КАНАЛ",
        "col_title": "НАЗВАНИЕ",
        "exported_count": "В итоговый файл включено результатов",
        "geo_fallback": "Ни одно видео не прошло фильтр по региону (каналы из других стран) — показаны результаты без гео-фильтра.",
        "press_enter": "Нажмите Enter для выхода...",
        "search_pass": "проход",
        "country": "Страна канала",
        "focus_menu": (
            "Что искать:\n"
            f"  1 — Популярное (больше всего просмотров)\n"
            f"  2 — Набирающее популярность (быстрый рост, видео за последние {RISING_WINDOW_DAYS} дней)"
        ),
        "focus_label": "Тип",
        "focus_popular": "Популярное",
        "focus_rising": "Набирающее популярность",
        "rising_trends_note": "Для трендов (Most Popular) список берётся из чарта YouTube и ранжируется по индексу роста.",
        "after_rising": "После отбора по росту осталось",
        "after_geo": "После фильтра по региону осталось",
        "fewer_than_count": "Найдено меньше запрошенного: API отдаёт ограниченный набор. Попробуйте добавить запросов или сменить регион.",
    },
    "en": {
        "title": "TREND-SCANNER-GEO",
        "api_key": "Enter your YouTube Data API v3 key",
        "api_key_env": f"API key taken from the {API_KEY_ENV} environment variable.",
        "checking": "Checking API key...",
        "api_ok": "API key is working.",
        "api_error": "Could not connect to YouTube API.",
        "bye": "Finished. See you!",
        "count": "Number of results (1–50)",
        "region_menu": "Select region (geo) for analysis:",
        "mode_menu": (
            "Select mode:\n"
            "  1 — Most Popular videos\n"
            "  2 — Search by Keywords"
        ),
        "query_prompt": "Enter queries separated by commas or new lines (0 to exit)",
        "searching": "Searching videos and collecting statistics...",
        "progress_videos": "Fetching video data",
        "progress_channels": "Fetching channel data",
        "progress_trends": "Fetching trends",
        "done": "ALL DONE! ANALYSIS COMPLETE",
        "follow": "More from me — follow my channels",
        "brand_line": "TREND-SCANNER-GEO  |  FIND. ANALYZE. GROW.",
        "found": "Unique videos found",
        "selected": "Processed videos",
        "saved_to": "Saved in folder",
        "preview": "SEARCH SUMMARY",
        "setup": "SEARCH & TRENDS SETUP",
        "live_progress": "LIVE PROGRESS",
        "empty": "No matching videos found.",
        "unknown": "Unknown",
        "popular": "Popular",
        "trending": "Trending",
        "published": "Published",
        "duration": "Duration",
        "views": "Views",
        "likes": "Likes",
        "comments": "Comments",
        "channel": "Channel",
        "subs": "Subscribers",
        "age": "Age, days",
        "vph": "Average views per hour",
        "ratio": "Views / subscribers",
        "score": "Growth score",
        "popularity_label": "Category",
        "developer": "Developer",
        "contacts": "Contacts",
        "invalid": "Invalid input.",
        "no_results": "Try changing parameters or queries.",
        "quota_exceeded": "The YouTube Data API quota for today is exhausted.",
        "key_rejected": "The key was rejected or access is denied.",
        "chart_unavailable": "The trends chart is currently unavailable for this region. Choose another region.",
        "unexpected": "An unexpected error occurred (see the log for details).",
        "mode_trends": "Most Popular",
        "mode_search": "Search",
        "trends_collect": "Collecting trends for region",
        "query_label": "Query",
        "saving": "Saving files...",
        "files": "FILES",
        "quota_estimate": "Estimated quota cost",
        "quota_of": "of daily",
        "col_views": "VIEWS",
        "col_vph": "VPH",
        "col_dur": "LEN",
        "col_channel": "CHANNEL",
        "col_title": "TITLE",
        "exported_count": "Results included in the output file",
        "geo_fallback": "No video passed the region filter (channels from other countries) — showing results without the geo filter.",
        "press_enter": "Press Enter to exit...",
        "search_pass": "pass",
        "country": "Channel country",
        "focus_menu": (
            "What to look for:\n"
            f"  1 — Popular (most views)\n"
            f"  2 — Gaining popularity (fast growth, videos from the last {RISING_WINDOW_DAYS} days)"
        ),
        "focus_label": "Type",
        "focus_popular": "Popular",
        "focus_rising": "Gaining popularity",
        "rising_trends_note": "For trends (Most Popular) the list comes from the YouTube chart and is ranked by growth score.",
        "after_rising": "Videos left after growth selection",
        "after_geo": "Videos left after region filter",
        "fewer_than_count": "Fewer results than requested: the API returns a limited set. Try more queries or another region.",
    },
}


# ───────────────────────── helpers ─────────────────────────

def choose_language():
    print("\n1. Русский")
    print("2. English")
    while True:
        choice = input("> ").strip()
        if choice == "1":
            return "ru"
        if choice == "2":
            return "en"
        print("Введите 1 или 2 / Enter 1 or 2")


def read_api_key(lang):
    """Ключ из переменной окружения или обычный (видимый) ввод — вставка Ctrl+V работает."""
    t = TEXT[lang]
    env_key = os.environ.get(API_KEY_ENV, "").strip()
    if env_key:
        print(f"\n  {t['api_key_env']}")
        return env_key
    return input(f"\n  {t['api_key']}: ").strip()


def parse_queries(raw):
    queries = re.split(r"[,;\n]+", raw)
    result = []
    seen = set()
    for query in queries:
        query = query.strip()
        key = query.casefold()
        if query and key not in seen:
            result.append(query)
            seen.add(key)
    return result


def to_int(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


_DURATION_RE = re.compile(
    r"P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?"
)


def parse_duration(value):
    """ISO 8601 -> секунды. Поддерживает недели, дни, дробные секунды."""
    match = _DURATION_RE.fullmatch(value or "")
    if not match or not value or value == "P":
        return None
    weeks, days, hours, minutes, seconds = match.groups()
    return int(
        int(weeks or 0) * 604800
        + int(days or 0) * 86400
        + int(hours or 0) * 3600
        + int(minutes or 0) * 60
        + float(seconds or 0)
    )


def format_duration(seconds, unknown):
    if seconds is None:
        return unknown
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02}:{secs:02}"
    return f"{minutes}:{secs:02}"


def _error_content(error):
    try:
        return error.content.decode("utf-8", errors="ignore")
    except AttributeError:
        return str(error)


def is_quota_error(error):
    if not isinstance(error, HttpError):
        return False
    content = _error_content(error)
    return "quotaExceeded" in content or "dailyLimitExceeded" in content


def is_chart_error(error):
    if not isinstance(error, HttpError):
        return False
    return "videoChartNotFound" in _error_content(error) or getattr(error.resp, "status", None) == 404


def is_key_error(error):
    if not isinstance(error, HttpError):
        return False
    status = getattr(error.resp, "status", None)
    return status in (400, 401, 403) and not is_quota_error(error)


def cell_text(value, empty="—"):
    return empty if value is None else str(value)


def execute(request):
    """Единая точка выполнения запросов с повторами при временных сбоях."""
    return request.execute(num_retries=API_RETRIES)


def connect_api(api_key):
    youtube = build("youtube", "v3", developerKey=api_key, cache_discovery=False)
    # Дешёвый (1 единица) и стабильный запрос для проверки ключа
    execute(youtube.videoCategories().list(part="snippet", regionCode="US"))
    return youtube


def estimate_quota(mode_choice, count, queries_count=0, focus="popular"):
    """Верхняя оценка расхода квоты для одного запуска."""
    if mode_choice == "1":
        ids = count if focus == "popular" else TRENDS_MAX_CANDIDATES
        cost = math.ceil(ids / 50) * LIST_COST  # mostPopular
    else:
        passes = len(SEARCH_ORDERS_BY_FOCUS[focus])
        cost = queries_count * MAX_PAGES * passes * SEARCH_COST
        ids = queries_count * MAX_PAGES * 50 * passes

    batches = max(1, math.ceil(ids / 50))
    cost += batches * LIST_COST          # videos().list
    cost += batches * LIST_COST          # channels().list (верхняя оценка)
    return cost


# ───────────────────────── console output ─────────────────────────

def print_header(lang):
    t = TEXT[lang]
    line = "=" * 68
    print("\n" + line)
    print(f"  {t['title']}  |  {t['brand_line']}")
    print(line)
    print("  YouTube Data API v3  •  Trends & Search Toolkit")
    print(f"  {t['developer']}: {DEVELOPER}")
    print("-" * 68)


def show_progress(label, current, total, finish=False):
    total = max(int(total), 1)
    current = min(max(int(current), 0), total)
    width = 28
    filled = int(width * current / total)
    bar = "█" * filled + "░" * (width - filled)
    percent = int(100 * current / total)
    line = f"  {label:<28} [{bar}] {percent:3d}%  {current}/{total}"
    print("\r" + line + ("\n" if finish else ""), end="", flush=True)


def print_section(title):
    print(f"\n{'─' * 68}\n  {title}\n{'─' * 68}")


def print_summary(videos, lang):
    t = TEXT[lang]
    print_section(t["preview"])
    print(
        f"  {'#':>2}  "
        f"{t['col_views']:>9}  "
        f"{t['col_vph']:>9}  "
        f"{t['col_dur']:>8}  "
        f"{t['col_channel']:<22}  "
        f"{t['col_title']}"
    )
    print("  " + "─" * 64)
    for index, video in enumerate(videos, 1):
        channel = video["channel"].replace("\n", " ")[:22]
        title = video["title"].replace("\n", " ")
        if len(title) > 48:
            title = title[:45] + "..."
        vph = video["views_per_hour"]
        vph_text = f"{vph:>9,.1f}" if vph is not None else f"{'—':>9}"
        print(
            f"  {index:>2}  "
            f"{video['views']:>9,}  "
            f"{vph_text}  "
            f"{video['duration']:>8}  "
            f"{channel:<22}  "
            f"{title}"
        )
    print(f"\n  {t['exported_count']}: {len(videos)}.")


# ───────────────────────── YouTube API Logic ─────────────────────────

def fetch_trending_videos(youtube, region_code, max_results):
    """Постранично собирает mostPopular; останавливается, когда нет nextPageToken."""
    video_ids = []
    next_page = None
    target = min(max(int(max_results), 1), TRENDS_MAX_CANDIDATES)
    while len(video_ids) < target:
        params = {
            "part": "snippet",
            "chart": "mostPopular",
            "regionCode": region_code,
            "maxResults": min(50, target - len(video_ids)),
        }
        if next_page:
            params["pageToken"] = next_page
        response = execute(youtube.videos().list(**params))
        for item in response.get("items", []):
            video_id = item.get("id")
            if video_id and video_id not in video_ids:
                video_ids.append(video_id)
        next_page = response.get("nextPageToken")
        if not next_page or not response.get("items"):
            break
    return video_ids


def search_video_ids(youtube, query, region_code, max_pages=MAX_PAGES, progress_callback=None,
                     language=None, video_duration=None, order="date", published_after=None):
    """Возвращает уникальные ID. order='date' — свежие загрузки; 'viewCount' — популярные."""
    video_ids = []
    next_page = None
    for page_index in range(max_pages):
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "order": order,
            "regionCode": region_code,
            "maxResults": 50,
        }
        if published_after:
            params["publishedAfter"] = published_after
        if language:
            params["relevanceLanguage"] = language
        if video_duration:
            params["videoDuration"] = video_duration
        if next_page:
            params["pageToken"] = next_page

        response = execute(youtube.search().list(**params))
        next_page = response.get("nextPageToken")
        for item in response.get("items", []):
            video_id = item.get("id", {}).get("videoId")
            if video_id and video_id not in video_ids:
                video_ids.append(video_id)

        finished = not next_page or page_index + 1 == max_pages
        if progress_callback:
            progress_callback(max_pages if finished else page_index + 1, max_pages, finished)
        if finished:
            break
    return video_ids


def get_video_and_channel_data(youtube, video_ids, lang):
    videos = []
    video_batches = list(range(0, len(video_ids), 50))

    for batch_index, start in enumerate(video_batches, 1):
        response = execute(youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(video_ids[start:start + 50]),
        ))
        videos.extend(response.get("items", []))
        show_progress(
            TEXT[lang]["progress_videos"],
            batch_index,
            len(video_batches),
            finish=(batch_index == len(video_batches)),
        )

    channel_ids = list(dict.fromkeys(
        item.get("snippet", {}).get("channelId", "") for item in videos
    ))
    channel_ids = [cid for cid in channel_ids if cid]

    channels = {}
    channel_batches = list(range(0, len(channel_ids), 50))
    for batch_index, start in enumerate(channel_batches, 1):
        response = execute(youtube.channels().list(
            part="statistics,snippet",
            id=",".join(channel_ids[start:start + 50]),
        ))
        for channel in response.get("items", []):
            channels[channel["id"]] = {
                **channel.get("statistics", {}),
                "country": channel.get("snippet", {}).get("country"),
            }
        show_progress(
            TEXT[lang]["progress_channels"],
            batch_index,
            len(channel_batches),
            finish=(batch_index == len(channel_batches)),
        )

    return videos, channels


# ───────────────────────── analysis & categorization ─────────────────────────

def compute_growth_score(views_per_hour, views_per_subscriber, like_ratio):
    """
    Индекс роста 0–100 из трёх компонентов (макс. 40 / 40 / 20).
    Недоступные компоненты (скрытые лайки или подписчики) исключаются,
    а результат пересчитывается на оставшийся максимум, чтобы видео не штрафовалось.
    """
    parts = []
    if views_per_hour is not None:
        parts.append((min(views_per_hour / 100, 40), 40))
    if views_per_subscriber is not None:
        parts.append((min(views_per_subscriber * 20, 40), 40))
    if like_ratio is not None:
        parts.append((min(like_ratio * 2, 20), 20))
    if not parts:
        return 0.0
    earned = sum(p for p, _ in parts)
    maximum = sum(m for _, m in parts)
    return earned / maximum * 100


def enrich_videos(videos, channels, lang):
    t = TEXT[lang]
    now = datetime.now(timezone.utc)
    results = []

    for item in videos:
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        details = item.get("contentDetails", {})

        try:
            published = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
            age_hours = max((now - published).total_seconds() / 3600, 0.0)
            published_text = published.strftime("%Y-%m-%d %H:%M UTC")
        except (ValueError, KeyError):
            age_hours = None
            published_text = t["unknown"]

        duration_seconds = parse_duration(details.get("duration", ""))

        views = to_int(stats.get("viewCount")) or 0
        likes = to_int(stats.get("likeCount"))
        comments = to_int(stats.get("commentCount"))

        channel_id = snippet.get("channelId", "")
        channel_stats = channels.get(channel_id, {})
        channel_country = channel_stats.get("country")
        subscribers = (
            None if channel_stats.get("hiddenSubscriberCount")
            else to_int(channel_stats.get("subscriberCount"))
        )

        views_per_hour = (
            views / max(age_hours, MIN_AGE_HOURS_FOR_VPH) if age_hours is not None else None
        )
        views_per_subscriber = views / subscribers if subscribers else None
        like_ratio = likes / views * 100 if likes is not None and views else None

        growth_score = compute_growth_score(views_per_hour, views_per_subscriber, like_ratio)

        video_id = item.get("id", "")
        results.append({
            "title": snippet.get("title", ""),
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "channel": snippet.get("channelTitle", ""),
            "published": published_text,
            "duration": format_duration(duration_seconds, t["unknown"]),
            "views": views,
            "likes": likes,
            "comments": comments,
            "subscribers": subscribers,
            "country": channel_country,
            "age_days": round(age_hours / 24, 1) if age_hours is not None else None,
            "views_per_hour": round(views_per_hour, 1) if views_per_hour is not None else None,
            "views_per_subscriber": round(views_per_subscriber, 3) if views_per_subscriber is not None else None,
            "growth_score": round(growth_score, 2),
        })
    return results


def classify_popularity(videos, lang):
    """
    Popular — топ-20% по просмотрам, Trending — топ-20% по индексу роста
    (минимум по одному видео). Вызывается ПОСЛЕ отбора итогового набора,
    поэтому метки считаются относительно того, что реально попадёт в файл.
    """
    t = TEXT[lang]
    if not videos:
        return videos

    group_size = max(1, math.ceil(len(videos) * LABEL_SHARE))
    by_views = sorted(videos, key=lambda v: v["views"], reverse=True)
    by_growth = sorted(videos, key=lambda v: v["growth_score"], reverse=True)

    popular_ids = {v["video_id"] for v in by_views[:group_size]}
    trending_ids = {v["video_id"] for v in by_growth[:group_size]}

    for video in videos:
        cats = []
        if video["video_id"] in popular_ids:
            cats.append(t["popular"])
        if video["video_id"] in trending_ids:
            cats.append(t["trending"])
        video["popularity_text"] = ", ".join(cats)

    return videos


def export_results(videos, lang, mode_info):
    t = TEXT[lang]
    output_dir = BASE_DIR / "output"
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        probe = output_dir / ".write_test"
        probe.touch()
        probe.unlink()
    except OSError:
        # Папка программы защищена от записи — используем папку пользователя
        output_dir = Path.home() / "TrendScannerGeo_output"
        output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base = output_dir / f"trend_scanner_geo_{timestamp}"

    columns = [
        ("title", "Title"),
        ("url", "URL"),
        ("popularity_text", t["popularity_label"]),
        ("published", t["published"]),
        ("duration", t["duration"]),
        ("views", t["views"]),
        ("likes", t["likes"]),
        ("comments", t["comments"]),
        ("channel", t["channel"]),
        ("subscribers", t["subs"]),
        ("country", t["country"]),
        ("age_days", t["age"]),
        ("views_per_hour", t["vph"]),
        ("views_per_subscriber", t["ratio"]),
        ("growth_score", t["score"]),
    ]

    rows = [dict(v) for v in videos]

    # 1. CSV
    with open(str(base) + ".csv", "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow([t["title"]])
        writer.writerow([t["developer"], DEVELOPER])
        for name, link in CONTACTS:
            writer.writerow([name, link])
        writer.writerow(["Mode Info", mode_info])
        writer.writerow(["Exported", timestamp])
        writer.writerow([])
        writer.writerow([label for _, label in columns])
        for row in rows:
            writer.writerow([cell_text(row.get(key), empty="") for key, _ in columns])

    # 2. Markdown
    with open(str(base) + ".md", "w", encoding="utf-8") as file:
        file.write(f"# {t['title']}\n\n")
        file.write(f"**{t['developer']}:** {DEVELOPER}  \n")
        file.write(f"**{t['contacts']}:** " + " · ".join(f"[{name}]({link})" for name, link in CONTACTS) + "\n\n")
        file.write(f"Mode Info: {mode_info}  \n")
        file.write(f"Exported: {timestamp}\n\n")
        file.write("| " + " | ".join(label for _, label in columns) + " |\n")
        file.write("| " + " | ".join("---" for _ in columns) + " |\n")
        for row in rows:
            cells = []
            for key, _ in columns:
                value = (
                    cell_text(row.get(key))
                    .replace("\\", "\\\\").replace("|", "\\|")
                    .replace("\n", " ").replace("\r", " ")
                )
                if key == "title":
                    value = value.replace("[", "\\[").replace("]", "\\]")
                    value = f"[{value}]({row['url']})"
                cells.append(value)
            file.write("| " + " | ".join(cells) + " |\n")

    # 3. TXT
    with open(str(base) + ".txt", "w", encoding="utf-8") as file:
        file.write(f"{t['title']}\n")
        file.write(f"{t['developer']}: {DEVELOPER}\n")
        for name, link in CONTACTS:
            file.write(f"{name}: {link}\n")
        file.write(f"\nMode Info: {mode_info}\n")
        file.write(f"Exported: {timestamp}\n\n")

        for index, row in enumerate(rows, 1):
            file.write(f"{index}. {row['title']}\n")
            file.write(f"   URL: {row['url']}\n")
            for key, label in columns[2:]:
                file.write(f"   {label}: {cell_text(row.get(key))}\n")
            file.write("\n")

    return base


# ───────────────────────── main loop ─────────────────────────

def run_session(youtube, lang):
    t = TEXT[lang]
    print_section(t["setup"])

    # 1. Регион
    print(f"\n  {t['region_menu']}")
    for k, v in REGIONS.items():
        name = v["name_en"] if lang == "en" else v["name_ru"]
        print(f"  {k} — {name}")

    reg_choice = input("  > ").strip()
    if reg_choice.casefold() in EXIT_WORDS:
        return False
    if reg_choice not in REGIONS:
        print("  ! " + t["invalid"])
        return True
    selected_region = REGIONS[reg_choice]["code"]

    # 2. Режим
    print(f"\n  {t['mode_menu']}")
    mode_choice = input("  > ").strip()
    if mode_choice.casefold() in EXIT_WORDS:
        return False
    if mode_choice not in ("1", "2"):
        print("  ! " + t["invalid"])
        return True

    # 3. Количество
    try:
        count = int(input(f"  {t['count']}: ").strip())
    except ValueError:
        print("  ! " + t["invalid"])
        return True
    if not 1 <= count <= 50:
        print("  ! " + t["invalid"])
        return True

    # 3a. Что искать: популярное / набирающее популярность
    print(f"\n  {t['focus_menu']}")
    focus_choice = input("  > ").strip()
    if focus_choice.casefold() in EXIT_WORDS:
        return False
    if focus_choice not in FOCUS_CHOICES:
        print("  ! " + t["invalid"])
        return True
    focus = FOCUS_CHOICES[focus_choice]
    focus_name = t["focus_" + focus]
    if focus == "rising" and mode_choice == "1":
        print(f"  ℹ {t['rising_trends_note']}")

    # 4. Запросы (только для режима поиска) — до начала работы, чтобы показать квоту
    queries = []
    if mode_choice == "2":
        raw_queries = input(f"  {t['query_prompt']}: ").strip()
        if raw_queries.casefold() in EXIT_WORDS:
            return False
        queries = parse_queries(raw_queries)
        if not queries:
            print("  ! " + t["invalid"])
            return True

    estimated = estimate_quota(mode_choice, count, len(queries), focus)
    print(f"\n  ℹ {t['quota_estimate']}: ~{estimated:,} {t['quota_of']} {DAILY_QUOTA:,}")

    all_ids = []
    print_section(t["live_progress"])

    try:
        if mode_choice == "1":
            mode_info = f"{t['mode_trends']} (Region: {selected_region}; {t['focus_label']}: {focus_name})"
            print(f"  ▸ {t['trends_collect']}: {selected_region}")
            show_progress(t["progress_trends"], 0, 1)
            try:
                fetch_count = count if focus == "popular" else TRENDS_MAX_CANDIDATES
                all_ids = fetch_trending_videos(youtube, selected_region, fetch_count)
            except HttpError as error:
                if is_chart_error(error):
                    print("\n  ✗ " + t["chart_unavailable"])
                    return True
                raise
            show_progress(t["progress_trends"], 1, 1, finish=True)
        else:
            mode_info = (
                f"{t['mode_search']} (Region: {selected_region}; {t['focus_label']}: {focus_name}): "
                f"{' | '.join(queries)}"
            )
            seen_ids = set()
            published_after = None
            if focus == "rising":
                since = datetime.now(timezone.utc) - timedelta(days=RISING_WINDOW_DAYS)
                published_after = since.strftime("%Y-%m-%dT%H:%M:%SZ")
            for q_idx, query in enumerate(queries, 1):
                print(f"\n  ▸ {t['query_label']}: {query}")
                orders = SEARCH_ORDERS_BY_FOCUS[focus]
                for pass_idx, order in enumerate(orders, 1):
                    label = f"{t['query_label']} {q_idx}/{len(queries)} · {t['search_pass']} {pass_idx}/{len(orders)}"
                    show_progress(label, 0, MAX_PAGES)
                    ids = search_video_ids(
                        youtube, query, selected_region, max_pages=MAX_PAGES,
                        language=REGION_LANG.get(selected_region),
                        order=order,
                        published_after=published_after,
                        progress_callback=lambda c, total, fin, l=label: show_progress(l, c, total, fin),
                    )
                    for vid in ids:
                        if vid not in seen_ids:
                            seen_ids.add(vid)
                            all_ids.append(vid)

        if not all_ids:
            print("\n  ! " + t["empty"])
            return True

        print(f"\n  {t['found']}: {len(all_ids)}")
        print(f"\n  [2/3] {t['searching']}")

        raw_videos, channels = get_video_and_channel_data(youtube, all_ids, lang)
        videos = enrich_videos(raw_videos, channels, lang)

        # Гео-фильтр для поиска: regionCode у YouTube — лишь подсказка, поэтому отбрасываем
        # каналы из другой страны. Каналы без указанной страны остаются.
        if mode_choice == "2":
            geo_videos = [v for v in videos if v["country"] in (None, selected_region)]
            print(f"\n  {t['after_geo']} ({selected_region}): {len(geo_videos)}")
            if geo_videos or not videos:
                videos = geo_videos
            else:
                print(f"  ! {t['geo_fallback']}")

        # Сначала отбираем итоговый набор, потом классифицируем уже по нему
        if focus == "rising":
            videos = [v for v in videos if v["views"] >= MIN_VIEWS_RISING]
            if mode_choice == "2":
                videos = [v for v in videos if v["age_days"] is None or v["age_days"] <= RISING_WINDOW_DAYS]
            print(f"\n  {t['after_rising']}: {len(videos)}")
            videos = sorted(
                videos, key=lambda v: (v["growth_score"], v["views_per_hour"] or 0), reverse=True
            )[:count]
        else:
            videos = sorted(videos, key=lambda v: v["views"], reverse=True)[:count]
        videos = classify_popularity(videos, lang)

        if not videos:
            print("\n  ! " + t["empty"])
            print("  " + t["no_results"])
            return True

        print_summary(videos, lang)
        if len(videos) < count:
            print(f"  ℹ {t['fewer_than_count']}")

        print(f"\n  [3/3] {t['saving']}")
        base = export_results(videos, lang, mode_info)

        print_section(t["done"])
        print(f"  ✓ {t['selected']}: {len(videos)}")
        print(f"  ✓ {t['saved_to']}: {base.parent.resolve()}")
        print(f"\n  {t['files']}")
        for ext in (".csv", ".md", ".txt"):
            path = Path(str(base) + ext).resolve()
            print(f"  ✓ {path.name}\n    {path}")

        print("\n" + "=" * 68)
        print(f"  {t['follow']}")
        print(f"  {t['developer']}: {DEVELOPER}")
        for name, link in CONTACTS:
            print(f"  {name:<8} ·  {link}")
        print("=" * 68)

    except HttpError as error:
        logging.exception("API execution failed")
        if is_quota_error(error):
            print("\n  ✗ " + t["quota_exceeded"])
        elif is_key_error(error):
            print("\n  ✗ " + t["key_rejected"])
        else:
            print("\n  ✗ " + t["api_error"])
    except Exception:
        logging.exception("Execution failed")
        print("\n  ✗ " + t["unexpected"])

    return True


def _main():
    try:
        lang = choose_language()
        t = TEXT[lang]
        print_header(lang)

        api_key = read_api_key(lang)
        if not api_key:
            print(f"\n  ! {t['api_error']}")
            return

        print(f"\n  [1/3] {t['checking']}")
        try:
            youtube = connect_api(api_key)
            print("  ✓ " + t["api_ok"])
        except Exception as error:
            logging.exception("API connection failed")
            if is_quota_error(error):
                print("  ✗ " + t["quota_exceeded"])
            elif is_key_error(error):
                print("  ✗ " + t["key_rejected"])
            else:
                print("  ✗ " + t["api_error"])
            return

        while run_session(youtube, lang):
            pass

        print(f"\n  {t['bye']}\n")

    except (KeyboardInterrupt, EOFError):
        print("\n\n  Bye!\n")


def main():
    try:
        _main()
    finally:
        # Двойной клик по EXE: не закрывать окно, пока пользователь не прочитает вывод
        if getattr(sys, "frozen", False):
            try:
                input("\n  Enter...")
            except (EOFError, KeyboardInterrupt):
                pass


if __name__ == "__main__":
    main()
