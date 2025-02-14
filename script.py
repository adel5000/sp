import os
import requests
import json
from flask import Flask, jsonify

app = Flask(__name__)

# إعدادات API و Telegram
api_url = "https://sp-today.com/app_api/cur_damascus.json"  
telegram_token = "7924669675:AAGLWCdlVRnsRg6yF01-u7PFxwTgJ4ZvBtc"  
chat_id = "-1002474033832"  
last_price_file = 'last_price.json'
currencies_to_track = ["USD", "SAR", "TRY", "AED", "JOD", "EGP", "KWD"]

# قاموس الأعلام
flags = {
    "USD": "🇺🇸", "SAR": "🇸🇦", "TRY": "🇹🇷", "AED": "🇦🇪",
    "JOD": "🇯🇴", "EGP": "🇪🇬", "KWD": "🇰🇼"
}

@app.route('/')
def run_script():
    response = requests.get(api_url)
    data = response.json()

    messages = []
    send_update = False  
    before = 0
    after = 0

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

        print("🔍 محتوى last_price.json عند بدء التشغيل:", last_prices)

        # الحصول على السعر السابق للدولار
        last_usd_price = last_prices.get("USD", None)
        before = last_usd_price

        for currency in data:
            if currency['name'] in currencies_to_track:
                currency_name = currency['ar_name']
                ask_price = currency['ask']
                bid_price = currency['bid']
                change = currency['change']
                
                # تحديد العلم بناءً على العملة
                flag = flags.get(currency['name'], "🏳️")

                if currency['name'] == "USD":
                    after = ask_price

                # إضافة ملاحظة لسعر الدولار
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

                # تكوين الرسالة مع العلم
                message = f"""{flag} {currency_name}
{usd_message}
🔹 سعر المبيع : {bid_price} ل.س  
🔹 سعر الشراء : {ask_price} ل.س  
🔹 التغيير : {change}
"""
                messages.append(message)
                current_prices[currency['name']] = ask_price

        # **إرسال التحديث إلى Telegram فقط إذا كان هناك تغيير**
        if send_update:
            message_text = "\n🔹 تحديث أسعار الصرف :\n\n" + "\n\n".join(messages)

            # رابط API للإرسال إلى Telegram
            telegram_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message_text,
                "parse_mode": "HTML"
            }

            try:
                telegram_response = requests.post(telegram_url, json=payload)
                telegram_response.raise_for_status()
                print("✅ تم إرسال الرسالة إلى Telegram:", message_text)

                # تحديث الملف بعد الإرسال
                with open(last_price_file, 'w') as file:
                    json.dump(current_prices, file, indent=4)

                return jsonify({"status": "success", "message": "تم إرسال التحديث إلى Telegram ✅", "before": before, "after": after}), 200
            except requests.exceptions.RequestException as e:
                return jsonify({"status": "error", "message": str(e)}), 500

        else:
            return jsonify({"status": "no_update", "message": "لم يتغير سعر الدولار، لا حاجة للتحديث.", "before": before, "after": after}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
