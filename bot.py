from datetime import date, datetime, timedelta
import os
import random
from flask import Flask, jsonify, request
import pytz
import requests
import yfinance as yf

app = Flask(__name__)

# --- Environment Secrets ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
CRON_SECRET = os.environ.get("CRON_SECRET", "clonsilla-dispatch-secure-key")

LAT = 53.3833
LON = -6.4167
TIMEZONE = "Europe/Dublin"

WMO_WEATHER_CODES = {
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Foggy", "🌫"),
    48: ("Depositing rime fog", "🌫"),
    51: ("Light drizzle", "🌦"),
    53: ("Moderate drizzle", "🌧"),
    55: ("Dense drizzle", "🌧"),
    61: ("Slight rain", "🌦"),
    63: ("Moderate rain", "🌧"),
    65: ("Heavy rain", "🌧"),
    71: ("Slight snow", "🌨"),
    73: ("Moderate snow", "❄️"),
    75: ("Heavy snow", "❄️"),
    80: ("Brief rain showers", "🌦"),
    81: ("Moderate rain showers", "🌧"),
    82: ("Violent rain showers", "⛈"),
    95: ("Thunderstorm", "⛈"),
}


# ==========================================
# 1. SALUTATIONS & SIGN-OFFS
# ==========================================
def get_salutation():
    greetings = [
        "Hello, Michael",
        "Good morning, Michael",
        "Hi, Michael",
        "Buongiorno, Michael",
        "Dia dhuit, Michael",
        "Top of the morning, Michael",
    ]
    return random.choice(greetings)


def get_closing_section(now):
    valedictions = [
        "Slán go fóill",
        "Au Revoir",
        "Bye for now",
        "Cheers",
        "Take care",
        "All the best",
    ]
    valediction = random.choice(valedictions)

    # Weekend wishes (Saturday = 5, Sunday = 6)
    if now.weekday() in (5, 6):
        weekend_wishes = [
            "Have a healthy, restful, and relaxing weekend!",
            "Wishing you a peaceful, restorative, and relaxing weekend!",
            "Take time to unwind and enjoy a healthy and relaxing weekend!",
            "Wishing you a wonderfully peaceful and relaxing weekend!",
            "Have a lovely, healthy, and refreshing weekend!",
            "May your weekend be restful, relaxing, and enjoyable!",
        ]
        wish = random.choice(weekend_wishes)
    else:
        weekday_wishes = [
            "Wishing you a productive and enjoyable day ahead!",
            "Have a wonderful, energizing, and productive day!",
            "Wishing you clarity, focus, and a great day ahead!",
            "Have a fantastic, smooth, and productive day!",
            "Wishing you a very successful and fulfilling day!",
            "Have a terrific day ahead!",
        ]
        wish = random.choice(weekday_wishes)

    return f"""----------------------------------------

{valediction} — {wish}

Cubby! 🐻"""


# ==========================================
# 2. WEATHER & SUN (TODAY & TOMORROW)
# ==========================================
def get_weather_and_sun():
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}"
        f"&daily=sunrise,sunset,weathercode,temperature_2m_max,temperature_2m_min"
        f"&hourly=temperature_2m,weathercode"
        f"&timezone={TIMEZONE}"
    )
    try:
        res = requests.get(url, timeout=10).json()
        daily = res.get("daily", {})
        hourly = res.get("hourly", {})

        # Today Sun
        sunrise_today = daily["sunrise"][0].split("T")[1]
        sunset_today = daily["sunset"][0].split("T")[1]

        # Today: Morning (10:00 AM / index 10) & Afternoon (3:00 PM / index 15)
        m_temp_0 = hourly["temperature_2m"][10]
        m_desc_0, m_icon_0 = WMO_WEATHER_CODES.get(
            hourly["weathercode"][10], ("Cloudy", "⛅")
        )
        a_temp_0 = hourly["temperature_2m"][15]
        a_desc_0, a_icon_0 = WMO_WEATHER_CODES.get(
            hourly["weathercode"][15], ("Cloudy", "⛅")
        )
        high_0 = daily["temperature_2m_max"][0]
        low_0 = daily["temperature_2m_min"][0]

        # Tomorrow: Morning (10:00 AM / index 34) & Afternoon (3:00 PM / index 39)
        m_temp_1 = hourly["temperature_2m"][34]
        m_desc_1, m_icon_1 = WMO_WEATHER_CODES.get(
            hourly["weathercode"][34], ("Cloudy", "⛅")
        )
        a_temp_1 = hourly["temperature_2m"][39]
        a_desc_1, a_icon_1 = WMO_WEATHER_CODES.get(
            hourly["weathercode"][39], ("Cloudy", "⛅")
        )
        high_1 = daily["temperature_2m_max"][1]
        low_1 = daily["temperature_2m_min"][1]

        return {
            "sunrise": sunrise_today,
            "sunset": sunset_today,
            "today_morning": f"{m_icon_0} {m_temp_0:.1f}°C — {m_desc_0}",
            "today_afternoon": f"{a_icon_0} {a_temp_0:.1f}°C — {a_desc_0}",
            "today_range": f"Low {low_0:.1f}°C / High {high_0:.1f}°C",
            "tom_morning": f"{m_icon_1} {m_temp_1:.1f}°C — {m_desc_1}",
            "tom_afternoon": f"{a_icon_1} {a_temp_1:.1f}°C — {a_desc_1}",
            "tom_range": f"Low {low_1:.1f}°C / High {high_1:.1f}°C",
        }
    except Exception:
        return {
            "sunrise": "N/A",
            "sunset": "N/A",
            "today_morning": "Unavailable",
            "today_afternoon": "Unavailable",
            "today_range": "N/A",
            "tom_morning": "Unavailable",
            "tom_afternoon": "Unavailable",
            "tom_range": "N/A",
        }


# ==========================================
# 3. EVENTS, HOLIDAYS & MOVEABLE DATES
# ==========================================
def calculate_easter(year):
    """Anonymous Gregorian Easter Algorithm (Meeus/Jones/Butcher)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def get_nth_weekday_of_month(year, month, target_weekday, n):
    """Finds the nth occurrence of a weekday in a given month (target_weekday: 0=Mon..6=Sun)."""
    first_day = date(year, month, 1)
    days_to_target = (target_weekday - first_day.weekday()) % 7
    first_occ = first_day + timedelta(days=days_to_target)
    return first_occ + timedelta(weeks=n - 1)


def get_last_sunday_of_month(year, month):
    """Finds the last Sunday of a month."""
    if month == 12:
        last_day = date(year, 12, 31)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    days_back = (last_day.weekday() - 6) % 7
    return last_day - timedelta(days=days_back)


# Multi-year exact calendar table for lunar/multi-faith observances
MULTI_FAITH_HOLIDAYS = {
    # 2024
    (2024, 2, 10): "Lunar New Year",
    (2024, 4, 10): "Eid al-Fitr",
    (2024, 6, 16): "Eid al-Adha",
    (2024, 11, 1): "Diwali",
    # 2025
    (2025, 1, 29): "Lunar New Year",
    (2025, 3, 31): "Eid al-Fitr",
    (2025, 6, 6): "Eid al-Adha",
    (2025, 10, 20): "Diwali",
    (2025, 10, 21): "Diwali",
    # 2026
    (2026, 2, 17): "Lunar New Year",
    (2026, 3, 20): "Eid al-Fitr",
    (2026, 5, 27): "Eid al-Adha",
    (2026, 11, 8): "Diwali",
    # 2027
    (2027, 2, 6): "Lunar New Year",
    (2027, 3, 10): "Eid al-Fitr",
    (2027, 5, 16): "Eid al-Adha",
    (2027, 10, 29): "Diwali",
    # 2028
    (2028, 1, 26): "Lunar New Year",
    (2028, 2, 26): "Eid al-Fitr",
    (2028, 5, 5): "Eid al-Adha",
    (2028, 10, 17): "Diwali",
    # 2029
    (2029, 2, 13): "Lunar New Year",
    (2029, 2, 14): "Eid al-Fitr",
    (2029, 4, 24): "Eid al-Adha",
    (2029, 11, 5): "Diwali",
    # 2030
    (2030, 2, 3): "Lunar New Year",
    (2030, 2, 4): "Eid al-Fitr",
    (2030, 4, 13): "Eid al-Adha",
    (2030, 10, 26): "Diwali",
    # 2031
    (2031, 1, 23): "Lunar New Year",
    (2031, 1, 24): "Eid al-Fitr",
    (2031, 4, 2): "Eid al-Adha",
    (2031, 11, 14): "Diwali",
    # 2032
    (2032, 2, 11): "Lunar New Year",
    (2032, 1, 14): "Eid al-Fitr",
    (2032, 3, 22): "Eid al-Adha",
    (2032, 11, 2): "Diwali",
    # 2033
    (2033, 1, 31): "Lunar New Year",
    (2033, 1, 2): "Eid al-Fitr",
    (2033, 12, 23): "Eid al-Fitr",
    (2033, 3, 11): "Eid al-Adha",
    (2033, 10, 22): "Diwali",
    # 2034
    (2034, 2, 19): "Lunar New Year",
    (2034, 12, 12): "Eid al-Fitr",
    (2034, 3, 1): "Eid al-Adha",
    (2034, 11, 10): "Diwali",
    # 2035
    (2035, 2, 8): "Lunar New Year",
    (2035, 12, 1): "Eid al-Fitr",
    (2035, 2, 18): "Eid al-Adha",
    (2035, 10, 30): "Diwali",
}


def get_events_and_holidays(now):
    events = []
    y = now.year
    today_date = date(y, now.month, now.day)

    # 1. Computed Moveable Christian & Secular Events
    easter = calculate_easter(y)
    thanksgiving_usa = get_nth_weekday_of_month(y, 11, target_weekday=3, n=4)

    moveable_events = {
        easter - timedelta(days=47): "Shrove Tuesday / Mardi Gras",
        easter - timedelta(days=46): "Ash Wednesday",
        easter - timedelta(days=21): "Mother’s Day [Ireland]",
        easter - timedelta(days=7): "Palm Sunday",
        easter - timedelta(days=2): "Good Friday",
        easter: "Easter Sunday",
        easter + timedelta(days=39): "Ascension Day",
        easter + timedelta(days=49): "Pentecost",
        get_nth_weekday_of_month(
            y, 6, target_weekday=6, n=3
        ): "Father’s Day [Ireland]",
        get_last_sunday_of_month(y, 3): "Daylight Savings – Start [Ireland]",
        get_last_sunday_of_month(y, 10): "Daylight Savings – End [Ireland]",
        thanksgiving_usa: "Thanksgiving [USA]",
        thanksgiving_usa + timedelta(days=1): "Black Friday [USA]",
    }

    if today_date in moveable_events:
        events.append(moveable_events[today_date])

    # 2. Multi-Faith Moveable Dates
    date_key_full = (y, now.month, now.day)
    if date_key_full in MULTI_FAITH_HOLIDAYS:
        events.append(MULTI_FAITH_HOLIDAYS[date_key_full])

    # 3. Fixed Cultural / International Dates
    fixed_calendar_events = {
        (1, 1): "New Year's Day",
        (1, 6): "Epiphany / Little Christmas",
        (2, 1): "St Brigid's Day (Imbolc)",
        (2, 14): "Valentine's Day",
        (3, 8): "International Women's Day",
        (3, 17): "St Patrick's Day",
        (4, 22): "Earth Day",
        (4, 23): "St George's Day",
        (5, 1): "May Day",
        (5, 5): "Cinco de Mayo",
        (6, 16): "Bloomsday",
        (6, 21): "Summer Solstice",
        (10, 31): "Halloween (Oíche Shamhna)",
        (11, 11): "Remembrance Day",
        (12, 21): "Winter Solstice",
        (12, 24): "Christmas Eve",
        (12, 25): "Christmas Day",
        (12, 26): "St Stephen's Day",
        (12, 31): "New Year's Eve",
    }
    date_key = (now.month, now.day)
    if date_key in fixed_calendar_events:
        evt = fixed_calendar_events[date_key]
        if evt not in events:
            events.append(evt)

    # 4. Official Irish Bank Holidays via Nager.Date API
    try:
        url = f"https://date.nager.at/api/v3/PublicHolidays/{y}/IE"
        holidays = requests.get(url, timeout=5).json()
        today_str = now.strftime("%Y-%m-%d")
        for h in holidays:
            if h.get("date") == today_str:
                h_name = f"🇮🇪 {h.get('localName') or h.get('name')}"
                if h_name not in events:
                    events.append(h_name)
    except Exception:
        pass

    return ", ".join(events) if events else "None"


# ==========================================
# 4. CATHOLIC SAINT & THOUGHT FOR THE DAY
# ==========================================
SAINTS_MAP = {
    (1, 1): (
        "Solemnity of Mary, Mother of God",
        "Honours the Blessed Virgin Mary's maternal role in the incarnation.",
    ),
    (1, 28): (
        "St. Thomas Aquinas",
        (
            "Dominican friar, philosopher, and Doctor of the Church; patron of"
            " students."
        ),
    ),
    (2, 1): (
        "St. Brigid of Kildare",
        "Patroness of Ireland, renowned for charity, hospitality, and healing.",
    ),
    (3, 17): (
        "St. Patrick",
        "Patron saint of Ireland who brought Christianity to the island.",
    ),
    (3, 19): (
        "St. Joseph",
        "Spouse of the Blessed Virgin Mary and patron of workers and families.",
    ),
    (4, 25): (
        "St. Mark the Evangelist",
        "Author of the Gospel of Mark and founder of the Church of Alexandria.",
    ),
    (5, 1): (
        "St. Joseph the Worker",
        "Fosters deep dignity and Christian sanctification of human labour.",
    ),
    (6, 9): (
        "St. Columba (Colmcille)",
        (
            "One of Ireland's three patron saints; missionary and founder of"
            " Iona Abbey."
        ),
    ),
    (6, 13): (
        "St. Anthony of Padua",
        "Doctor of the Church, renowned preacher, and patron of lost things.",
    ),
    (6, 24): (
        "Nativity of St. John the Baptist",
        (
            "Commemorates the birth of the prophet who prepared the way of the"
            " Lord."
        ),
    ),
    (6, 29): (
        "Sts. Peter and Paul",
        "Apostles and foundational pillars of the early Christian Church.",
    ),
    (7, 1): (
        "St. Oliver Plunkett",
        (
            "Archbishop of Armagh and Irish martyr who died for his faith in"
            " 1681."
        ),
    ),
    (7, 11): (
        "St. Benedict of Nursia",
        "Patron saint of Europe and father of Western monasticism.",
    ),
    (7, 22): (
        "St. Mary Magdalene",
        "Apostle to the Apostles and first witness of the Resurrection.",
    ),
    (7, 31): (
        "St. Ignatius of Loyola",
        "Founder of the Jesuits and author of the Spiritual Exercises.",
    ),
    (8, 8): (
        "St. Dominic",
        "Founder of the Order of Preachers (Dominicans) devoted to truth.",
    ),
    (8, 15): (
        "Assumption of the Blessed Virgin Mary",
        "Celebrates Mary's bodily assumption into heavenly glory.",
    ),
    (8, 28): (
        "St. Augustine of Hippo",
        "Bishop, philosopher, and Doctor of the Church known for Confessions.",
    ),
    (9, 21): (
        "St. Matthew",
        "Apostle and evangelist called from his tax booth to follow Christ.",
    ),
    (9, 29): (
        "Sts. Michael, Gabriel & Raphael",
        (
            "Archangels who lead heavenly worship, announce salvation, and"
            " guide the faithful."
        ),
    ),
    (10, 1): (
        "St. Thérèse of Lisieux",
        (
            "Doctor of the Church known for her 'Little Way' of spiritual"
            " childhood."
        ),
    ),
    (10, 4): (
        "St. Francis of Assisi",
        (
            "Patron saint of ecology and animals, celebrated for humility and"
            " peace."
        ),
    ),
    (10, 15): (
        "St. Teresa of Ávila",
        "Doctor of the Church and mystic reformer of the Carmelite Order.",
    ),
    (10, 28): (
        "Sts. Simon and Jude",
        "Apostles of Christ; Jude is widely venerated as patron of lost causes.",
    ),
    (11, 1): (
        "All Saints' Day",
        "Solemnity honouring all canonised and unheralded holy souls in heaven.",
    ),
    (11, 2): (
        "All Souls' Day",
        "Commemoration and prayer for all the faithful departed.",
    ),
    (11, 17): (
        "St. Elizabeth of Hungary",
        (
            "Princess revered for her deep devotion to nursing the sick and"
            " poor."
        ),
    ),
    (12, 6): (
        "St. Nicholas",
        "Bishop of Myra remembered for generosity and kindness to children.",
    ),
    (12, 13): (
        "St. Lucy",
        "Virgin and martyr whose name signifies light; patroness of sight.",
    ),
    (12, 26): (
        "St. Stephen",
        "The first Christian martyr, known for his faith and forgiving spirit.",
    ),
    (12, 27): (
        "St. John the Apostle",
        (
            "The beloved disciple who authored the Fourth Gospel and letters of"
            " love."
        ),
    ),
}

CATHOLIC_THOUGHTS = [
    (
        "St. Teresa of Ávila",
        (
            "Let nothing perturb you, nothing frighten you. All things pass;"
            " God does not change. Patience achieves everything."
        ),
    ),
    (
        "St. Francis of Assisi",
        (
            "Start by doing what's necessary; then do what's possible; and"
            " suddenly you are doing the impossible."
        ),
    ),
    (
        "St. Padre Pio",
        (
            "Pray, hope, and don't worry. Worry is useless. God is merciful and"
            " will hear your prayer."
        ),
    ),
    (
        "St. Catherine of Siena",
        "Be who God meant you to be and you will set the world on fire.",
    ),
    (
        "St. Francis de Sales",
        (
            "Have patience with all things, but first of all with yourself. Do"
            " not lose courage in considering your own imperfections."
        ),
    ),
    (
        "St. Thérèse of Lisieux",
        (
            "Miss no single opportunity of making some small sacrifice, here by"
            " a smiling look, there by a kindly word; always doing the"
            " smallest right and doing it all for love."
        ),
    ),
    (
        "St. Augustine",
        "Our hearts are restless until they rest in You, O Lord.",
    ),
    (
        "St. John Henry Newman",
        (
            "God has created me to do Him some definite service; He has"
            " committed some work to me which He has not committed to another."
        ),
    ),
    (
        "St. Thomas Aquinas",
        (
            "To one who has faith, no explanation is necessary. To one without"
            " faith, no explanation is possible."
        ),
    ),
    (
        "St. Ignatius of Loyola",
        (
            "Teach us to give and not to count the cost, to fight and not to"
            " heed the wounds, to labor and not to ask for any reward save that"
            " of knowing that we do Your will."
        ),
    ),
    (
        "St. Teresa of Calcutta",
        (
            "Spread love everywhere you go. Let no one ever come to you without"
            " leaving happier."
        ),
    ),
    (
        "St. Gianna Beretta Molla",
        (
            "The secret of happiness is to live moment by moment and to thank"
            " God for all that He, in His goodness, sends to us day after day."
        ),
    ),
    (
        "St. John Paul II",
        "Do not be afraid. Open wide the doors to Christ.",
    ),
]


def get_catholic_saint_or_thought(now):
    date_key = (now.month, now.day)
    if date_key in SAINTS_MAP:
        name, desc = SAINTS_MAP[date_key]
        return f"<b>{name}</b>: {desc}"

    author, quote = random.choice(CATHOLIC_THOUGHTS)
    return f'<i>"{quote}"</i>\n— <b>{author}</b>'


# ==========================================
# 5. DAILY SMILE
# ==========================================
def get_joke():
    try:
        response = requests.get(
            "https://official-joke-api.appspot.com/jokes/general/random",
            timeout=5,
        )
        data = response.json()
        joke_dict = data[0] if isinstance(data, list) and data else data
        if isinstance(joke_dict, dict):
            setup = joke_dict.get("setup", "").strip()
            punchline = joke_dict.get("punchline", "").strip()
            if setup and punchline:
                return f'<i>"{setup}"</i>\n👉 <b>{punchline}</b>'
    except Exception:
        pass

    fallbacks = [
        ("Why do we tell actors to 'break a leg'?", "Because every play has a cast!"),
        (
            "Why don't scientists trust atoms?",
            "Because they make up everything!",
        ),
        (
            "How does a penguin build its house?",
            "Igloos it together!",
        ),
    ]
    q, a = random.choice(fallbacks)
    return f'<i>"{q}"</i>\n👉 <b>{a}</b>'


# ==========================================
# 6. FINANCIAL MARKETS
# ==========================================
def format_pct(val):
    if val is None:
        return "N/A"
    icon = "🟢 ▲" if val >= 0 else "🔴 ▼"
    sign = "+" if val > 0 else ""
    return f"{icon} {sign}{val:.2f}%"


def get_financial_data(include_futures=True):
    results = {}
    try:
        eurusd = yf.Ticker("EURUSD=X")
        fx_hist = eurusd.history(period="5d")
        if len(fx_hist) >= 2:
            latest = fx_hist["Close"].iloc[-1]
            prev = fx_hist["Close"].iloc[-2]
            pct = ((latest - prev) / prev) * 100
            results["fx"] = f"{latest:.4f} ({format_pct(pct)})"
        else:
            latest = fx_hist["Close"].iloc[-1]
            results["fx"] = f"{latest:.4f}"
    except Exception:
        results["fx"] = "Data unavailable"

    indices = {
        "S&P 500": "^GSPC",
        "Nasdaq 100": "^NDX",
        "Nasdaq Composite": "^IXIC",
    }
    index_results = []
    for label, ticker in indices.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5d")
            if len(hist) >= 2:
                close = hist["Close"].iloc[-1]
                prev = hist["Close"].iloc[-2]
                pct = ((close - prev) / prev) * 100
                index_results.append(f"• {label}: {format_pct(pct)}")
            else:
                index_results.append(f"• {label}: N/A")
        except Exception:
            index_results.append(f"• {label}: Unavailable")
    results["indices"] = index_results

    if include_futures:
        futures = {
            "S&P 500 Futures (ES)": "ES=F",
            "Nasdaq 100 Futures (NQ)": "NQ=F",
        }
        futures_results = []
        for label, ticker in futures.items():
            try:
                t = yf.Ticker(ticker)
                hist = t.history(period="2d")
                if len(hist) >= 2:
                    cur = hist["Close"].iloc[-1]
                    prev = hist["Close"].iloc[-2]
                    pct = ((cur - prev) / prev) * 100
                    futures_results.append(f"• {label}: {format_pct(pct)}")
                elif len(hist) == 1:
                    cur = hist["Close"].iloc[-1]
                    prev = hist["Open"].iloc[-1]
                    pct = ((cur - prev) / prev) * 100
                    futures_results.append(f"• {label}: {format_pct(pct)}")
                else:
                    futures_results.append(f"• {label}: Market Closed")
            except Exception:
                futures_results.append(f"• {label}: Unavailable")
        results["futures"] = futures_results
    else:
        results["futures"] = []

    return results


def build_financial_section(now):
    weekday = now.weekday()  # Mon=0, ..., Fri=4, Sat=5, Sun=6

    # Sunday: Don't show financial markets at all
    if weekday == 6:
        return ""

    # Saturday: FX and prior session closes only (no futures)
    if weekday == 5:
        data = get_financial_data(include_futures=False)
        indices_str = "\n".join(data["indices"])
        return f"""<b>Financial Markets 📈</b>
• <b>EUR / USD:</b> <code>{data['fx']}</code>

<b>Prior Session Index Closes:</b>
{indices_str}"""

    # Monday - Friday: Full section
    data = get_financial_data(include_futures=True)
    indices_str = "\n".join(data["indices"])
    futures_str = "\n".join(data["futures"])
    return f"""<b>Financial Markets 📈</b>
• <b>EUR / USD:</b> <code>{data['fx']}</code>

<b>Prior Session Index Closes:</b>
{indices_str}

<b>Today's Futures:</b>
{futures_str}"""


# ==========================================
# 7. ASSEMBLE FULL DIGEST MESSAGE
# ==========================================
def build_daily_digest():
    dublin_tz = pytz.timezone(TIMEZONE)
    now = datetime.now(dublin_tz)

    # Date formatting: e.g. "Saturday 10.10.26"
    date_str = f"{now.strftime('%A')} {now.strftime('%d.%m.%y')}"

    salutation = get_salutation()
    weather = get_weather_and_sun()
    events = get_events_and_holidays(now)
    saint_or_thought = get_catholic_saint_or_thought(now)
    joke = get_joke()
    finance_section = build_financial_section(now)
    closing_section = get_closing_section(now)

    # Core Message Parts
    parts = [
        f"""
<b>My Morning Brief</b>
<i>{date_str}</i>
----------------------------------------

{salutation}

<b>Sun & Daylight (Clonsilla) 🌄</b>
• <b>Sunrise:</b> {weather['sunrise']}
• <b>Sunset:</b> {weather['sunset']}

<b>Weather Forecast 🌦</b>
<b>Today:</b>
• <b>Morning:</b> {weather['today_morning']}
• <b>Afternoon:</b> {weather['today_afternoon']}
• <b>Day Bounds:</b> {weather['today_range']}

<b>Tomorrow:</b>
• <b>Morning:</b> {weather['tom_morning']}
• <b>Afternoon:</b> {weather['tom_afternoon']}
• <b>Day Bounds:</b> {weather['tom_range']}

<b>Events & Observances 🎉</b>
{events}

<b>Catholic Saint of the Day ⛪</b>
{saint_or_thought}

<b>Daily Smile 😄</b>
{joke}"""
    ]

    # Add financial markets section if not Sunday
    if finance_section:
        parts.append(finance_section)

    # Append closing & Cubby sign-off
    parts.append(closing_section)

    return "\n\n".join(parts)


def send_telegram(chat_id, text):
    if not TELEGRAM_BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    requests.post(url, json=payload, timeout=15)


# ==========================================
# 8. WEB SERVER ROUTES
# ==========================================
@app.route("/", methods=["GET"])
def health_check():
    return "Bot server is healthy and running!"


@app.route(f"/trigger/{CRON_SECRET}", methods=["GET", "POST"])
def manual_cron_trigger():
    if not TELEGRAM_CHAT_ID:
        return jsonify({"error": "TELEGRAM_CHAT_ID not set"}), 500

    digest = build_daily_digest()
    send_telegram(TELEGRAM_CHAT_ID, digest)
    return (
        jsonify({"status": "dispatched", "recipient": TELEGRAM_CHAT_ID}),
        200,
    )


@app.route(f"/webhook/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.get_json(silent=True)
    if not data or "message" not in data:
        return jsonify({"status": "ignored"}), 200

    msg = data["message"]
    incoming_chat_id = str(msg.get("chat", {}).get("id"))
    text = msg.get("text", "").strip().lower()

    if TELEGRAM_CHAT_ID and incoming_chat_id != str(TELEGRAM_CHAT_ID):
        return jsonify({"status": "unauthorized"}), 200

    if text.startswith("/today") or text.startswith("/start") or "morning" in text:
        send_telegram(
            incoming_chat_id, "⏳ <i>Gathering your morning briefing...</i>"
        )
        digest = build_daily_digest()
        send_telegram(incoming_chat_id, digest)

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)