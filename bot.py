import os
import random
from datetime import datetime
from flask import Flask, jsonify, request
import pytz
import requests
import yfinance as yf

app = Flask(__name__)

# --- Environment Secrets ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

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


# --- Your Existing Data Functions ---
def get_salutation():
    greetings = [
        "Good morning",
        "Hi",
        "Hello",
        "Buongiorno",
        "Dia dhuit",
        "Bonjour",
        "Top of the morning to you",
    ]
    return f"{random.choice(greetings)}, Michael!"


def get_valediction():
    valedictions = [
        "Slán go fóill",
        "Bye for now",
        "Au Revoir",
        "Take care",
        "Have a wonderful day ahead",
        "Have a great day",
        "Cheers",
    ]
    return f"{random.choice(valedictions)} — wishing you a productive and enjoyable day ahead!"


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

        sunrise = daily["sunrise"][0].split("T")[1]
        sunset = daily["sunset"][0].split("T")[1]

        morning_temp = hourly["temperature_2m"][10]
        morning_code = hourly["weathercode"][10]
        morning_desc, morning_icon = WMO_WEATHER_CODES.get(
            morning_code, ("Cloudy", "⛅")
        )

        afternoon_temp = hourly["temperature_2m"][15]
        afternoon_code = hourly["weathercode"][15]
        afternoon_desc, afternoon_icon = WMO_WEATHER_CODES.get(
            afternoon_code, ("Cloudy", "⛅")
        )

        high = daily["temperature_2m_max"][0]
        low = daily["temperature_2m_min"][0]

        return {
            "sunrise": sunrise,
            "sunset": sunset,
            "morning": f"{morning_icon} {morning_temp:.1f}°C — {morning_desc}",
            "afternoon": f"{afternoon_icon} {afternoon_temp:.1f}°C — {afternoon_desc}",
            "range": f"Low {low:.1f}°C / High {high:.1f}°C",
        }
    except Exception:
        return {
            "sunrise": "N/A",
            "sunset": "N/A",
            "morning": "Forecast temporarily unavailable",
            "afternoon": "Forecast temporarily unavailable",
            "range": "N/A",
        }


def get_events_and_holidays(now):
    events = []
    try:
        url = f"https://date.nager.at/api/v3/PublicHolidays/{now.year}/IE"
        holidays = requests.get(url, timeout=5).json()
        today_str = now.strftime("%Y-%m-%d")
        for h in holidays:
            if h.get("date") == today_str:
                events.append(f"🇮🇪 {h.get('localName') or h.get('name')}")
    except Exception:
        pass

    fixed_calendar_events = {
        (1, 1): "New Year's Day",
        (2, 1): "St Brigid's Day (Imbolc)",
        (2, 14): "Valentine's Day",
        (3, 17): "St Patrick's Day",
        (4, 23): "St George's Day",
        (5, 5): "Cinco de Mayo",
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

    return ", ".join(events) if events else "None"


def get_catholic_saint(now):
    saints_map = {
        (1, 1): (
            "Solemnity of Mary, Mother of God",
            "Honours the Blessed Virgin Mary's maternal role in the incarnation.",
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
            "Spouse of the Blessed Virgin Mary and patron of universal church and workers.",
        ),
        (4, 25): (
            "St. Mark the Evangelist",
            "Author of the Gospel of Mark and traditional founder of the Church of Alexandria.",
        ),
        (5, 1): (
            "St. Joseph the Worker",
            "Fosters deep dignity and Christian sanctification of human labour.",
        ),
        (6, 13): (
            "St. Anthony of Padua",
            "Doctor of the Church, renowned preacher, and patron of lost things.",
        ),
        (6, 24): (
            "Nativity of St. John the Baptist",
            "Commemorates the birth of the prophet who prepared the way of the Lord.",
        ),
        (6, 29): (
            "Sts. Peter and Paul",
            "Apostles and foundational pillars of the early Christian Church.",
        ),
        (7, 11): (
            "St. Benedict of Nursia",
            "Patron saint of Europe and father of Western monasticism.",
        ),
        (7, 22): (
            "St. Mary Magdalene",
            "Apostle to the Apostles and first witness of the Resurrection.",
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
            "Bishop, theologian, and Doctor of the Church known for his Confessions.",
        ),
        (9, 21): (
            "St. Matthew",
            "Apostle and evangelist called from his tax booth to follow Christ.",
        ),
        (9, 29): (
            "Sts. Michael, Gabriel & Raphael",
            "Archangels who lead heavenly worship, announce salvation, and guide the faithful.",
        ),
        (10, 4): (
            "St. Francis of Assisi",
            "Patron saint of ecology, animals, and peace, celebrated for humility and Gospel poverty.",
        ),
        (10, 15): (
            "St. Teresa of Ávila",
            "Doctor of the Church and reformer of the Carmelite Order.",
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
            "Princess revered for her deep devotion to nursing the sick and feeding the poor.",
        ),
        (12, 6): (
            "St. Nicholas",
            "Bishop of Myra remembered for his quiet generosity and kindness to children.",
        ),
        (12, 13): (
            "St. Lucy",
            "Virgin and martyr whose name signifies light, patroness of sight.",
        ),
        (12, 26): (
            "St. Stephen",
            "The first Christian martyr, known for his faith and forgiving spirit.",
        ),
        (12, 27): (
            "St. John the Apostle",
            "The beloved disciple who authored the Fourth Gospel and letters of love.",
        ),
    }
    date_key = (now.month, now.day)
    if date_key in saints_map:
        name, desc = saints_map[date_key]
        return f"<b>{name}</b>: {desc}"

    return (
        f"<b>Saint of the Day</b>: Today is {now.strftime('%B %d')}. "
        "We remember the holy men and women whose quiet lives of faith, prayer, and service inspire our daily journey."
    )


def get_joke():
    try:
        res = requests.get(
            "https://official-joke-api.appspot.com/jokes/general/random",
            timeout=5,
        )
        data = res.json()
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


def format_pct(val):
    if val is None:
        return "N/A"
    icon = "🟢 ▲" if val >= 0 else "🔴 ▼"
    sign = "+" if val > 0 else ""
    return f"{icon} {sign}{val:.2f}%"


def get_financial_data():
    results = {}
    try:
        eurusd = yf.Ticker("EURUSD=X")
        fx_hist = eurusd.history(period="5d")
        if len(fx_hist) >= 2:
            latest_rate = fx_hist["Close"].iloc[-1]
            prev_rate = fx_hist["Close"].iloc[-2]
            fx_pct = ((latest_rate - prev_rate) / prev_rate) * 100
            results["fx"] = f"{latest_rate:.4f} ({format_pct(fx_pct)})"
        else:
            latest_rate = fx_hist["Close"].iloc[-1]
            results["fx"] = f"{latest_rate:.4f}"
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

    return results


def build_daily_digest():
    dublin_tz = pytz.timezone(TIMEZONE)
    now = datetime.now(dublin_tz)

    salutation = get_salutation()
    valediction = get_valediction()
    weather = get_weather_and_sun()
    events = get_events_and_holidays(now)
    saint = get_catholic_saint(now)
    joke = get_joke()
    finance = get_financial_data()

    indices_str = "\n".join(finance["indices"])
    futures_str = "\n".join(finance["futures"])

    return f"""<b>{salutation}</b>
<i>{now.strftime('%A, %d %B %Y')} — Dublin</i>
━━━━━━━━━━━━━━━━━━━━━

🌅 <b>Sun & Daylight (Clonsilla)</b>
• <b>Sunrise:</b> {weather['sunrise']}
• <b>Sunset:</b> {weather['sunset']}

🌦 <b>Weather Forecast</b>
• <b>Morning:</b> {weather['morning']}
• <b>Afternoon:</b> {weather['afternoon']}
• <b>Day Bounds:</b> {weather['range']}

🎉 <b>Events & Observances</b>
{events}

⛪ <b>Catholic Saint of the Day</b>
{saint}

😄 <b>Daily Smile</b>
{joke}

📈 <b>Financial Markets</b>
• <b>EUR / USD:</b> <code>{finance['fx']}</code>

<b>Prior Session Index Closes:</b>
{indices_str}

<b>Today's Futures:</b>
{futures_str}
━━━━━━━━━━━━━━━━━━━━━

{valediction}"""


def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    requests.post(url, json=payload, timeout=15)


# --- Webhook Endpoint ---
@app.route("/", methods=["GET"])
def health_check():
    return "Bot server is healthy and running!"


@app.route(f"/webhook/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.get_json(silent=True)
    if not data or "message" not in data:
        return jsonify({"status": "ignored"}), 200

    msg = data["message"]
    incoming_chat_id = str(msg.get("chat", {}).get("id"))
    text = msg.get("text", "").strip().lower()

    # Security check: only respond if the request comes from YOUR chat ID
    if TELEGRAM_CHAT_ID and incoming_chat_id != str(TELEGRAM_CHAT_ID):
        return jsonify({"status": "unauthorized"}), 200

    # Respond to /today, /start, or "morning"
    if text.startswith("/today") or text.startswith("/start") or "morning" in text:
        # Send an immediate acknowledgement
        send_telegram(
            incoming_chat_id, "⏳ <i>Gathering your morning briefing...</i>"
        )
        digest = build_daily_digest()
        send_telegram(incoming_chat_id, digest)

    return jsonify({"status": "ok"}), 200

# Secret key to prevent random internet crawlers from triggering your message
CRON_SECRET = os.environ.get("CRON_SECRET", "clonsilla-dispatch-secure-key")


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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)