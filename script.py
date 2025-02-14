from flask import Flask, jsonify
import requests
import json
import os


app = Flask(__name__)

# إعدادات API و Telegram
api_url = "https://sp-today.com/app_api/cur_damascus.json"  # رابط API لجلب الأسعار
telegram_token = "7924669675:AAGLWCdlVRnsRg6yF01-u7PFxwTgJ4ZvBtc"  # رمز التوكن الخاص بالتلغرام
chat_id = "-1002474033832"  # معرف الدردشة في التلغرام

# ملف لتخزين آخر سعر
last_price_file = 'last_price.json'

# قائمة العملات التي تريد تتبعها
currencies_to_track = ["USD", "SAR", "TRY", "AED", "JOD", "EGP", "KWD"]
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

        # التحقق مما إذا كان الملف موجودًا، وإذا لم يكن موجودًا يتم إنشاؤه بقيمة افتراضية
        if not os.path.exists(last_price_file):
            with open(last_price_file, 'w') as file:
                json.dump({}, file)  # إنشاء ملف يحتوي على قاموس فارغ

        # قراءة آخر الأسعار من الملف
        try:
            with open(last_price_file, 'r') as file:
                last_prices = json.load(file)
                if not isinstance(last_prices, dict):  # إذا لم يكن القاموس صحيحًا، إعادة تعيينه
                    last_prices = {}
        except (FileNotFoundError, json.JSONDecodeError):
            last_prices = {}

        # التحقق من محتويات last_price.json بعد القراءة
        print("🔍 محتوى last_price.json عند بدء التشغيل:", last_prices)

        # الحصول على السعر السابق للدولار
        last_usd_price = last_prices.get("USD", None)
        before = last_usd_price

        # تخزين الأسعار الحالية
        for currency in data:
            if currency['name'] in currencies_to_track:
                currency_name = currency['ar_name']
                ask_price = currency['ask']
                bid_price = currency['bid']
                change = currency['change']

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

                # تكوين الرسالة
                message = f"""{currency_name}
{usd_message}
🔹 سعر المبيع : {bid_price} ل.س  
🔹 سعر الشراء : {ask_price} ل.س  
🔹 التغيير : {change}
"""
                messages.append(message)
                current_prices[currency['name']] = ask_price

        # تحديث الملف فقط إذا كان هناك تغيير
        if send_update or before == None:
            with open(last_price_file, 'w') as file:
                json.dump(current_prices, file, indent=4)
                file.flush()  # لضمان الكتابة الفورية

            # التحقق من محتويات الملف بعد الكتابة
            with open(last_price_file, 'r') as file:
                saved_data = json.load(file)
                print("✅ تم تحديث last_price.json بالمحتوى:", saved_data)

            return jsonify({"status": "success", "message": "تم تحديث الأسعار وحفظها.", "before": before, "after": after}), 200
        else:
            return jsonify({"status": "no_update", "message": "لم يتغير سعر الدولار، لا حاجة للتحديث.", "before": before, "after": after}), 200
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
