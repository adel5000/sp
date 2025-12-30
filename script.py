import os
import json
from datetime import datetime, timedelta, timezone
from flask import Flask, jsonify
from bs4 import BeautifulSoup
import cloudscraper

app = Flask(__name__)

# إعدادات API و Telegram
api_url = "https://sp-today.com/app_api/cur_damascus.json"
url = "https://sp-today.com/en"
telegram_token = "7924669675:AAGLWCdlVRnsRg6yF01-u7PFxwTgJ4ZvBtc"
chat_id = "-1002474033832"
last_price_file = 'last_price.json'
market_status_file = 'market_status.json'
#currencies_to_track = ["USD", "SAR", "TRY", "AED", "JOD", "EGP", "KWD"]
currencies_to_track = ["USD", "SAR", "TRY"]

# قاموس الأعلام
flags = {
    "USD": "🇺🇸", "SAR": "🇸🇦", "TRY": "🇹🇷", "AED": "🇦🇪",
    "JOD": "🇯🇴", "EGP": "🇪🇬", "KWD": "🇰🇼"
}

@app.route('/')
def run_script():
    logs = []  # قائمة لتجميع جميع الرسائل المطبوعة

    scraper = cloudscraper.create_scraper()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    response = scraper.get(api_url, headers=headers)
    data = response.json()

    messages = []
    gold_messages = []
    send_update = False


    # قراءة حالة السوق من الملف
    if os.path.exists(market_status_file):
        try:
            with open(market_status_file, 'r') as file:
                market_status = json.load(file)
        except (json.JSONDecodeError, ValueError):
            market_status = {"opened": False, "closed": False}
            with open(market_status_file, 'w') as file:
                json.dump(market_status, file, indent=4)
    else:
        market_status = {"opened": False, "closed": False}
        with open(market_status_file, 'w') as file:
            json.dump(market_status, file, indent=4)

    logs.append({"market_status": market_status})  # حفظ حالة السوق في الـ logs

    # ضبط التوقيت ليكون UTC+3
    utc_now = datetime.now(timezone.utc)  
    local_time = utc_now + timedelta(hours=3)
    current_time = local_time.strftime("%Y-%m-%d | %I:%M %p").replace("AM", "ص").replace("PM", "م")
    current_hour = local_time.hour
    logs.append({"current_time": current_time})  # تسجيل التوقيت الحالي

    # إرسال رسالة افتتاح السوق بعد الساعة 10 صباحًا
    if current_hour >= 10 and current_hour < 19 and not market_status["opened"]:
        market_status["opened"] = True
        market_status["closed"] = False
        with open(market_status_file, 'w') as file:
            json.dump(market_status, file, indent=4)
        send_update = True
        messages.append("🔓 افتتاح السوق - أسعار الصرف:\n")

    # إرسال رسالة إغلاق السوق الساعة 7 مساءً
    if current_hour >= 19 and current_hour < 23 and not market_status["closed"]:
        market_status["closed"] = True
        market_status["opened"] = False
        with open(market_status_file, 'w') as file:
            json.dump(market_status, file, indent=4)
        send_update = True
        messages.append("🔒 إغلاق السوق - أسعار الصرف:\n")

    if data:
        current_prices = {}

        # إنشاء الملف إذا لم يكن موجودًا
        if not os.path.exists(last_price_file):
            with open(last_price_file, 'w') as file:
                json.dump({}, file)

        # قراءة آخر الأسعار من الملف
        try:
            with open(last_price_file, 'r') as file:
                last_prices = json.load(file)
                if not isinstance(last_prices, dict):
                    last_prices = {}
        except (FileNotFoundError, json.JSONDecodeError):
            last_prices = {}

        logs.append({"last_price_start": last_prices})  # حفظ الأسعار القديمة

        # الحصول على السعر السابق للدولار وتحويله إلى float
        last_usd_price = float(last_prices.get("USD", {}).get("ask", 0)) if "USD" in last_prices else None

        for currency in data:
            if currency['name'] in currencies_to_track:
                currency_name = currency['ar_name']
                ask_price = float(currency['ask'])  
                bid_price = float(currency['bid'])  

                flag = flags.get(currency['name'], "🏳️")

                old_data = last_prices.get(currency['name'], {})
                old_ask_price = float(old_data.get("ask", 0)) if "ask" in old_data else None
                old_bid_price = float(old_data.get("bid", 0)) if "bid" in old_data else None

                ask_difference = ask_price - old_ask_price if old_ask_price is not None else 0
                bid_difference = bid_price - old_bid_price if old_bid_price is not None else 0

                ask_diff_text = f"({ask_difference:+} ل.س)" if old_ask_price is not None else "(لا يوجد بيانات سابقة)"
                bid_diff_text = f"({bid_difference:+} ل.س)" if old_bid_price is not None else "(لا يوجد بيانات سابقة)"

                usd_message = ""
                if currency['name'] == "USD" and last_usd_price is not None:
                    if ask_price > last_usd_price:
                        usd_message = "📉 انخفاض في قيمة الليرة السورية أمام الدولار"
                        send_update = True
                    elif ask_price < last_usd_price:
                        usd_message = "📈 تحسن في قيمة الليرة السورية أمام الدولار"
                        send_update = True
                    if ask_price != last_usd_price:
                        send_update = True

                message = f"""{flag} {currency_name}
{usd_message}
🔹سعر المبيع : {bid_price} ل.س {bid_diff_text}  
🔹سعر الشراء : {ask_price} ل.س {ask_diff_text}
"""
                messages.append(message)

                current_prices[currency['name']] = {"ask": ask_price, "bid": bid_price}

        # **إرسال التحديث إلى Telegram فقط إذا كان هناك تغيير**
        if send_update:
            response_gold = scraper.get(url, headers=headers)
            gold_messages = []
            
                            # التحقق من نجاح الطلب
            if response_gold.status_code == 200:
                soup = BeautifulSoup(response_gold.text, "html.parser")
        
                # البحث عن جدول أسعار الذهب
                gold_table = soup.find("table", class_="table table-hover gold")
                gold_prices = {}
        
                if gold_table:
                    rows = gold_table.find_all("tr")[1:]  # تجاهل العنوان    
                    for row in rows:
                        columns = row.find_all("td")
                        if len(columns) >= 2:
                            gold_type = row.find("th").text.strip()
                            price = columns[1].find("strong").text.strip()
                            gold_prices[gold_type] = price
        
                    # طباعة الأسعار المستخرجة
                    for type_, price in gold_prices.items():
                        if(type_ == "18Karat Gold Gram"):
                            gold_messages.append(f"🔹سعر غرام الذهب (18 قيراط) : {price}ل.س")
                        elif(type_ == "21Karat Gold Gram"):
                            gold_messages.append(f"🔹سعر غرام الذهب (21 قيراط) : {price}ل.س")
                        elif(type_ == "24Karat Gold Gram"):
                            gold_messages.append(f"🔹سعر غرام الذهب (24 قيراط) : {price}ل.س")
                        else:
                            gold_messages.append(f"🔹سعر الاونصة الذهب  : {price}$")
                else:
                    print("لم يتم العثور على جدول الذهب.")
            else:
                print("فشل في تحميل الصفحة.")
            message_text = f"\n🔹 تحديث أسعار الصرف ({current_time}):\n\n" + "\n".join(messages)+"\n\nأسعار الذهب :\n\n"+ "\n".join(gold_messages) + """
            
🔷 Facebook : https://facebook.com/liraprice1  
🔷 Telegram : t.me/lira_price
"""

            telegram_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message_text,
                "parse_mode": "HTML"
            }
            telegram_response = scraper.post(telegram_url, json=payload)  # استخدام cloudscraper هنا أيضاً
            telegram_response.raise_for_status()
            logs.append({"telegram_message_sent": message_text})

            with open(last_price_file, 'w') as file:
                json.dump(current_prices, file, indent=4)


        else:
            logs.append({"status": "No update needed"})

    return jsonify({"message": "Script executed successfully!", "logs": logs})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
