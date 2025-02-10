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
    last_price_file = 'last_price.json'  # مسار تخزين آخر سعر (تأكد من تعديل المسار)

    # قائمة العملات التي تريد تتبعها
    currencies_to_track = ["USD", "EUR", "SAR"]

    # جلب البيانات من API
    response = requests.get(api_url)
    data = response.json()

    messages = []

    if data:
        current_prices = {}

        # تخزين الأسعار الحالية
        for currency in data:
            if currency['name'] in currencies_to_track:
                currency_name = currency['ar_name']
                ask_price = currency['bid']
                change = currency['change']

                # تحديد رمز السهم بناءً على التغيير
                if int(change) > 0:
                    arrow_emoji = "↗️"
                elif int(change) < 0:
                    arrow_emoji = "↙️"
                else:
                    arrow_emoji = "⏹️"

                # تحديد العلم
                if currency['name'] == "SAR":
                    flag = "🇸🇦"
                elif currency['name'] == "EUR":
                    flag = "🇪🇺"
                else:
                    flag = "🇺🇸"

                # تكوين الرسالة
                message = f"{flag} {currency_name}: {ask_price} ل.س\nالتغيير: {change} {arrow_emoji}"
                messages.append(message)

                # تخزين السعر في القاموس
                current_prices[currency['name']] = ask_price

        if messages:
            message_text = "\n🔹 تحديث أسعار الصرف :\n" + "\n".join(messages[:3])  # إرسال فقط 3 رسائل أولية لتقليل الحجم

            # قراءة آخر الأسعار من الملف
            try:
                with open(last_price_file, 'r') as file:
                    last_prices = json.load(file)
            except FileNotFoundError:
                last_prices = {}

            # مقارنة الأسعار القديمة بالجديدة
            if current_prices != last_prices:
                # إرسال الرسالة إلى Telegram
                telegram_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage?chat_id={chat_id}&text={requests.utils.quote(message_text)}"
                try:
                    response = requests.get(telegram_url)
                    response.raise_for_status()  # سيتسبب في رفع استثناء إذا كانت الاستجابة غير 200
                    print("Message sent successfully!")

                    # تحديث آخر الأسعار في الملف
                    with open(last_price_file, 'w') as file:
                        json.dump(current_prices, file)
                except requests.exceptions.RequestException as e:
                    print(f"Error sending message: {e}")
            else:
                # إذا كانت الأسعار نفسها
                telegram_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage?chat_id={chat_id}&text={requests.utils.quote('أسعار العملات لم تتغير.')}"
                try:
                    response = requests.get(telegram_url)
                    response.raise_for_status()  # سيتسبب في رفع استثناء إذا كانت الاستجابة غير 200
                    print("No change in prices. Message sent.")
                except requests.exceptions.RequestException as e:
                    print(f"Error sending message: {e}")

    return "Code Executed!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
