import requests
import json
import logging

# إعدادات API و Telegram
api_url = "https://sp-today.com/app_api/cur_damascus.json"
telegram_token = "7924669675:AAGLWCdlVRnsRg6yF01-u7PFxwTgJ4ZvBtc"
chat_id = "-1002474033832"
last_price_file = 'last_price.txt'

# قائمة العملات التي تريد تتبعها
currencies_to_track = ["USD", "EUR", "SAR"]

# إعدادات تسجيل السجلات
logging.basicConfig(filename='log.txt', level=logging.INFO, format='%(asctime)s - %(message)s')

# جلب البيانات من API
try:
    response = requests.get(api_url)
    response.raise_for_status()  # سيتسبب في رفع استثناء إذا كانت الاستجابة غير 200
    data = response.json()

    logging.info("API request successful.")
except requests.exceptions.RequestException as e:
    logging.error(f"Error fetching API data: {e}")
    data = None

messages = []

if data:
    for currency in data:
        if currency['name'] in currencies_to_track:
            currency_name = currency['ar_name']
            ask_price = currency['bid']
            change = currency['change']
            arrow = currency['arrow']

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

    if messages:
        message_text = "\n🔹 تحديث أسعار الصرف :\n" + "\n".join(messages[:3])  # إرسال فقط 3 رسائل أولية لتقليل الحجم

        # فحص آخر رسالة تم إرسالها لمنع التكرار
        try:
            with open(last_price_file, 'r') as file:
                last_price = file.read().strip()
        except FileNotFoundError:
            last_price = ""

        if message_text != last_price:
            # إرسال الرسالة إلى Telegram
            telegram_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage?chat_id={chat_id}&text={requests.utils.quote(message_text)}"
            try:
                telegram_response = requests.get(telegram_url)
                telegram_response.raise_for_status()  # سيتسبب في رفع استثناء إذا كانت الاستجابة غير 200
                logging.info("Message sent successfully to Telegram.")
            except requests.exceptions.RequestException as e:
                logging.error(f"Error sending message to Telegram: {e}")
            
            # تحديث آخر سعر تم تخزينه
            with open(last_price_file, 'w') as file:
                file.write(message_text)
                logging.info("Last price updated.")
        else:
            logging.info("No price change. Message not sent.")
    else:
        logging.info("No relevant currency data found.")
else:
    logging.error("No data fetched from the API.")
