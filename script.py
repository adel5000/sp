from flask import Flask
import requests
import json

app = Flask(__name__)

@app.route('/')
def run_script():
    # إعدادات API و Telegram
    api_url = "https://sp-today.com/app_api/cur_damascus.json"  # رابط API لجلب الأسعار
    telegram_token = "7924669675:AAGLWCdlVRnsRg6yF01-u7PFxwTgJ4ZvBtc"  # رمز التوكن الخاص بالتلغرام
    chat_id = "-1002474033832"  # معرف الدردشة في التلغرام
    last_price_file = 'last_price.json'  # مسار تخزين آخر سعر

    # قائمة العملات التي تريد تتبعها
    currencies_to_track = ["USD", "SAR", "TRY", "AED", "JOD", "EGP", "KWD"]

    # جلب البيانات من API
    response = requests.get(api_url)
    data = response.json()

    messages = []
    send = False  # متغير لتحديد ما إذا كان سيتم الإرسال أم لا

    if data:
        current_prices = {}

        # قراءة آخر الأسعار من الملف
        try:
            with open(last_price_file, 'r') as file:
                last_prices = json.load(file)
        except FileNotFoundError:
            last_prices = {}

        # تخزين الأسعار الحالية
        for currency in data:
            if currency['name'] in currencies_to_track:
                currency_name = currency['ar_name']
                ask_price = currency['ask']
                bid_price = currency['bid']
                change = currency['change']
                arrow_emoji = ""

                # تحديد العلم
                flags = {
                    "USD": "🇺🇸", "SAR": "🇸🇦", "EUR": "🇪🇺", "TRY": "🇹🇷",
                    "AED": "🇦🇪", "JOD": "🇯🇴", "EGP": "🇪🇬", "KWD": "🇰🇼"
                }
                flag = flags.get(currency['name'], "🏳️")

                # مقارنة سعر الدولار الحالي بالسابق قبل التحديث
                if currency['name'] == "USD":
                    last_usd_price = last_prices.get("USD")
                    if last_usd_price and last_usd_price != ask_price:
                        if int(change) > 0:
                            arrow_emoji = "\n💰 تحسن في سعر الليرة مقابل الدولار"
                        elif int(change) < 0:
                            arrow_emoji = "\n💸 انخفاض في سعر الليرة مقابل الدولار"
                        send = True  # الإرسال سيتم فقط عند تغير سعر الدولار

                # تكوين الرسالة لكل العملات
                message = f"""{flag} {currency_name}  
🔹 سعر المبيع : {bid_price} ل.س  
🔹 سعر الشراء : {ask_price} ل.س  
🔹 التغيير : {change}
"""
                messages.append(message)

                # تحديث القاموس بالأسعار الحالية
                current_prices[currency['name']] = ask_price

        # إرسال جميع العملات عند تغير سعر الدولار
        if send and messages:
            message_text = "\n🔹 تحديث أسعار الصرف :\n\n" + "\n\n".join(messages) + arrow_emoji

            # إرسال الرسالة إلى Telegram
            telegram_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage?chat_id={chat_id}&text={requests.utils.quote(message_text)}"
            try:
                response = requests.get(telegram_url)
                response.raise_for_status()  # التحقق من نجاح الإرسال
                print("Message sent successfully!")

                # تحديث آخر الأسعار في الملف بعد التأكد من الإرسال
                with open(last_price_file, 'w') as file:
                    json.dump(current_prices, file)
            except requests.exceptions.RequestException as e:
                print(f"Error sending message: {e}")

    return "Code Executed!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
