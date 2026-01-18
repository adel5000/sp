import os
import re
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from flask import Flask, jsonify
from bs4 import BeautifulSoup
import cloudscraper

app = Flask(__name__)

BASE_URL = "https://sp-today.com/en"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "PUT_YOUR_TOKEN_HERE")
CHAT_ID = os.getenv("CHAT_ID", "PUT_YOUR_CHAT_ID_HERE")

LAST_PRICE_FILE = "last_price.json"
MARKET_STATUS_FILE = "market_status.json"

CURRENCIES_TO_TRACK = ["USD", "SAR", "TRY"]  # عدّل مثل ما بدك

FLAGS = {
    "USD": "🇺🇸", "SAR": "🇸🇦", "TRY": "🇹🇷", "AED": "🇦🇪",
    "JOD": "🇯🇴", "EGP": "🇪🇬", "KWD": "🇰🇼", "EUR": "🇪🇺"
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
}


# -----------------------------
# Helpers: storage / time
# -----------------------------
def load_json_file(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        save_json_file(path, default)
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        save_json_file(path, default)
        return default


def save_json_file(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def now_damascus_str() -> Tuple[datetime, str, int]:
    utc_now = datetime.now(timezone.utc)
    local_time = utc_now + timedelta(hours=3)
    current_time_str = local_time.strftime("%Y-%m-%d | %I:%M %p").replace("AM", "ص").replace("PM", "م")
    return local_time, current_time_str, local_time.hour


def to_float_num(s: str) -> Optional[float]:
    if s is None:
        return None
    s = s.strip().replace(",", "")
    m = re.search(r"[-+]?\d+(\.\d+)?", s)
    return float(m.group(0)) if m else None


# -----------------------------
# Fetch HTML
# -----------------------------
def get_scraper():
    return cloudscraper.create_scraper()


def fetch_html(scraper, url: str) -> str:
    resp = scraper.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


# -----------------------------
# Strategy 1 (Best): Extract Next.js embedded JSON payload
# -----------------------------
def extract_nextjs_payload_objects(html: str) -> str:
    """
    Extract concatenated strings from `self.__next_f.push([1,"..."])` entries
    and return as one big decoded text.
    """
    # Capture JS string content inside push
    # Example pattern in the file: self.__next_f.push([1,"...."])
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, flags=re.DOTALL)
    if not chunks:
        return ""

    decoded_parts = []
    for ch in chunks:
        # Decode JS/JSON string escapes safely:
        # wrap into a JSON string then json.loads to unescape
        try:
            decoded_parts.append(json.loads('"' + ch.replace("\\", "\\\\").replace('"', '\\"') + '"'))
        except Exception:
            # fallback attempt (sometimes already valid JSON escapes)
            try:
                decoded_parts.append(json.loads('"' + ch + '"'))
            except Exception:
                continue

    return "\n".join(decoded_parts)


def extract_data_from_payload(decoded_text: str) -> Optional[Dict[str, Any]]:
    """
    From decoded payload text, locate the big JSON object that contains:
    "currencies":[...], "gold":{...}
    and parse it.
    """
    # We look for a JSON object that includes "currencies" and "gold".
    # This is robust enough as long as these keys exist in the payload.
    start = decoded_text.find('"currencies":')
    if start == -1:
        return None

    # Find nearest '{' before "currencies"
    brace_start = decoded_text.rfind("{", 0, start)
    if brace_start == -1:
        return None

    # Find a reasonable end after gold_updated_at (or just find the matching end by heuristic).
    # We'll try to cut until '"gold_updated_at"' then expand to the next '}'.
    anchor = decoded_text.find('"gold_updated_at"', start)
    if anchor == -1:
        anchor = decoded_text.find('"currencies_updated_at"', start)

    if anchor != -1:
        # take some tail after anchor
        tail = decoded_text[brace_start:anchor + 8000]
    else:
        tail = decoded_text[brace_start:brace_start + 200000]  # hard limit

    # Now we attempt to extract the first JSON object from tail by balancing braces.
    depth = 0
    end_idx = None
    for i, c in enumerate(tail):
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end_idx = i + 1
                break

    if not end_idx:
        return None

    obj_text = tail[:end_idx]

    try:
        return json.loads(obj_text)
    except Exception:
        return None


def parse_currencies_from_data(data: Dict[str, Any], city: str, wanted: list) -> Dict[str, Dict[str, Any]]:
    out = {}
    for cur in data.get("currencies", []):
        code = cur.get("code")
        if code not in wanted:
            continue
        name_ar = cur.get("name_ar") or cur.get("name") or code
        flag = cur.get("flag") or FLAGS.get(code, "🏳️")

        city_obj = (cur.get("cities") or {}).get(city) or {}
        buy = city_obj.get("buy")   # غالبًا buy = سعر الشراء
        sell = city_obj.get("sell") # غالبًا sell = سعر المبيع

        # نحول لـ float (بعضها int)
        buy_f = float(buy) if buy is not None else None
        sell_f = float(sell) if sell is not None else None

        if buy_f is None or sell_f is None:
            continue

        out[code] = {
            "code": code,
            "name_ar": name_ar,
            "flag": flag,
            "ask": buy_f,   # ask = شراء (حسب تسميتك)
            "bid": sell_f,  # bid = مبيع (حسب تسميتك)
            "updated_at": cur.get("updated_at"),
            "change_pct": city_obj.get("change"),
        }
    return out


def parse_gold_from_data(data: Dict[str, Any], city: str) -> Dict[str, Any]:
    gold = (data.get("gold") or {})
    karats = gold.get("karats") or []
    out_karats = {}

    for k in karats:
        karat = k.get("karat")
        city_obj = (k.get("cities") or {}).get(city) or {}
        buy = city_obj.get("buy")
        sell = city_obj.get("sell")
        if karat and buy is not None and sell is not None:
            out_karats[karat] = {
                "buy": float(buy),
                "sell": float(sell),
                "change_pct": city_obj.get("change"),
                "updated_at": k.get("updated_at"),
            }

    ounce = gold.get("ounce") or {}
    ounce_usd = ounce.get("price_usd")

    return {
        "karats": out_karats,
        "ounce_usd": float(ounce_usd) if ounce_usd is not None else None,
        "gold_updated_at": data.get("gold_updated_at") or gold.get("updated_at"),
        "ounce_updated_at": ounce.get("updated_at"),
    }


# -----------------------------
# Strategy 2 (Fallback): HTML scrape for `a.rate-row`
# -----------------------------
def scrape_currencies_from_html(html: str, wanted: list) -> Dict[str, Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    out = {}

    for a in soup.select("a.rate-row"):
        code_el = a.select_one("span.font-semibold")
        if not code_el:
            continue
        code = code_el.get_text(strip=True)
        if code not in wanted:
            continue

        name_el = a.select_one("span.text-sm")
        name = name_el.get_text(strip=True) if name_el else code

        # The page shows two numbers (buy/sell) in two right-aligned blocks
        nums = [to_float_num(s.get_text(" ", strip=True)) for s in a.select("div.text-end span")]
        nums = [n for n in nums if isinstance(n, float)]

        if len(nums) < 2:
            continue

        # From the sample, the first large number then second large number exist
        buy = nums[0]
        sell = nums[1]

        out[code] = {
            "code": code,
            "name_ar": name,
            "flag": FLAGS.get(code, "🏳️"),
            "ask": buy,
            "bid": sell,
        }

    return out


def scrape_gold_ounce_from_html(html: str) -> Optional[float]:
    soup = BeautifulSoup(html, "html.parser")
    # The home page shows a Gold Ounce card with "$4596.92" style
    card = soup.select_one('a[href*="/en/gold/ounce"]')
    if not card:
        return None
    val = to_float_num(card.get_text(" ", strip=True))
    return val


# -----------------------------
# Telegram formatting
# -----------------------------
def diff_text(new: float, old: Optional[float], unit: str = "ل.س") -> str:
    if old is None:
        return "(لا يوجد بيانات سابقة)"
    d = new - old
    return f"({d:+.0f} {unit})" if unit == "ل.س" else f"({d:+.2f} {unit})"


def build_message(
    current_time: str,
    currency_rows: Dict[str, Dict[str, Any]],
    gold: Dict[str, Any],
    last_prices: Dict[str, Any],
    market_prefix: str = "",
) -> Tuple[str, bool]:
    """
    returns: (text, send_update)
    """
    messages = []
    send_update = False

    if market_prefix:
        messages.append(market_prefix)

    # USD sentiment
    last_usd = None
    if "USD" in last_prices:
        try:
            last_usd = float(last_prices["USD"].get("ask"))
        except Exception:
            last_usd = None

    # Currencies
    for code in CURRENCIES_TO_TRACK:
        if code not in currency_rows:
            continue

        row = currency_rows[code]
        ask = float(row["ask"])
        bid = float(row["bid"])

        old = last_prices.get(code) or {}
        old_ask = float(old["ask"]) if "ask" in old else None
        old_bid = float(old["bid"]) if "bid" in old else None

        # if changed -> update
        if old_ask is None or old_bid is None or ask != old_ask or bid != old_bid:
            send_update = True

        usd_line = ""
        if code == "USD" and last_usd is not None and ask != last_usd:
            # ملاحظة: إذا ask ارتفع يعني الليرة أضعف (انخفاض قيمة الليرة أمام الدولار)
            usd_line = "📉 انخفاض في قيمة الليرة السورية أمام الدولار" if ask > last_usd else "📈 تحسن في قيمة الليرة السورية أمام الدولار"
            send_update = True

        messages.append(
            f"""{row.get('flag','🏳️')} {row.get('name_ar', code)}
{usd_line}
🔹سعر المبيع : {bid:,.0f} ل.س {diff_text(bid, old_bid)}
🔹سعر الشراء : {ask:,.0f} ل.س {diff_text(ask, old_ask)}
"""
        )

    # Gold
    gold_lines = []
    karats = (gold.get("karats") or {})
    # نعرض 18/21/24 (وإذا تحب غيرها زِد)
    for k in ["18K", "21K", "24K"]:
        if k in karats:
            sell = karats[k]["sell"]
            gold_lines.append(f"🔹سعر غرام الذهب ({k.replace('K',' قيراط')}) : {sell:,.0f} ل.س")

    if gold.get("ounce_usd") is not None:
        gold_lines.append(f"🔹سعر أونصة الذهب : ${gold['ounce_usd']:.2f}")

    text = (
        f"🔹 تحديث الأسعار ({current_time}):\n\n"
        + "\n".join(messages)
        + "\n\nأسعار الذهب:\n\n"
        + "\n".join(gold_lines)
        + "\n\n"
        + "🔷 Facebook : https://facebook.com/liraprice1\n"
        + "🔷 Telegram : t.me/lira_price\n"
    )

    return text, send_update


def send_telegram(scraper, text: str) -> None:
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": True,
    }
    resp = scraper.post(telegram_url, json=payload, timeout=30)
    resp.raise_for_status()


# -----------------------------
# Main route
# -----------------------------
@app.route("/")
def run_script():
    logs = []
    scraper = get_scraper()

    # Market status
    market_status = load_json_file(MARKET_STATUS_FILE, {"opened": False, "closed": False})
    logs.append({"market_status": market_status})

    local_dt, current_time, current_hour = now_damascus_str()
    logs.append({"current_time": current_time})

    market_prefix = ""
    if 10 <= current_hour < 19 and not market_status.get("opened"):
        market_status["opened"] = True
        market_status["closed"] = False
        save_json_file(MARKET_STATUS_FILE, market_status)
        market_prefix = "🔓 افتتاح السوق - أسعار الصرف:\n"

    if 19 <= current_hour < 23 and not market_status.get("closed"):
        market_status["closed"] = True
        market_status["opened"] = False
        save_json_file(MARKET_STATUS_FILE, market_status)
        market_prefix = "🔒 إغلاق السوق - أسعار الصرف:\n"

    # Last prices
    last_prices = load_json_file(LAST_PRICE_FILE, {})
    if not isinstance(last_prices, dict):
        last_prices = {}
    logs.append({"last_price_start": last_prices})

    # Fetch page
    html = fetch_html(scraper, BASE_URL)

    # Try best approach: Next.js payload -> full data
    decoded = extract_nextjs_payload_objects(html)
    data_obj = extract_data_from_payload(decoded) if decoded else None

    # Build current rows
    city = "damascus"  # غيرها إذا بدك
    if data_obj:
        currencies = parse_currencies_from_data(data_obj, city=city, wanted=CURRENCIES_TO_TRACK)
        gold = parse_gold_from_data(data_obj, city=city)
        logs.append({"source": "nextjs_payload", "city": city})
    else:
        # fallback HTML
        currencies = scrape_currencies_from_html(html, wanted=CURRENCIES_TO_TRACK)
        ounce_usd = scrape_gold_ounce_from_html(html)
        gold = {"karats": {}, "ounce_usd": ounce_usd}
        logs.append({"source": "html_fallback", "city": city})

    # If nothing found, return error
    if not currencies:
        return jsonify({"ok": False, "error": "No currency data parsed", "logs": logs}), 500

    # Build message + decide update
    msg_text, send_update = build_message(
        current_time=current_time,
        currency_rows=currencies,
        gold=gold,
        last_prices=last_prices,
        market_prefix=market_prefix,
    )

    # Send only if changed OR market open/close event triggered
    if send_update or bool(market_prefix):
        send_telegram(scraper, msg_text)
        logs.append({"telegram_message_sent": True})

        # Save new prices (only tracked currencies)
        new_last = {}
        for code, row in currencies.items():
            new_last[code] = {"ask": row["ask"], "bid": row["bid"]}
        save_json_file(LAST_PRICE_FILE, new_last)
    else:
        logs.append({"status": "No update needed"})

    return jsonify({"ok": True, "logs": logs})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
