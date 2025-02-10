import requests
import json

# إعدادات API و Telegram
api_url = "https://sp-today.com/app_api/cur_damascus.json"
telegram_token = "YOUR_TELEGRAM_BOT_TOKEN"
chat_id = "YOUR_CHAT_ID"
last_price_file = 'last_price.txt'

# قائمة العملات التي تريد تتبعها
currencies_to_track = ["USD", "EUR", "SAR"]

# جلب البيانات من API
response = requests.get(api_url)
data = response.json()

messages = []

if data:
    for currency in data:
        if currency['name'] in currencies_to_track:
            currency_name = currency['ar_name']
            ask_price = currency['bid']
            change = currency['change']
            arrow = currency['arrow']

            # تحديد رمز السهم بناءً على التغيير
            if change > 0:
                arrow_emoji = "↗️ \n🐇   قفز الارنب"
            elif change < 0:
                arrow_emoji = "↙️ \n🐇   تزحلط الارنب"
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
            messages.append(f"\n{flag}{currency_name}: {ask_price} ل.س\nالتغيير: {change} {arrow_emoji}")

    if messages:
        message_text = "\n🔹 تحديث أسعار الصرف :\n" + "\n\n".join(messages)

        # فحص آخر رسالة تم إرسالها لمنع التكرار
        try:
            with open(last_price_file, 'r') as file:
                last_price = file.read().strip()
        except FileNotFoundError:
            last_price = ""

        if message_text != last_price:
            # إرسال الرسالة إلى Telegram
            telegram_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage?chat_id={chat_id}&text={requests.utils.quote(message_text)}"
            requests.get(telegram_url)

            # تحديث آخر سعر مخزن
            with open(last_price_file, 'w') as file:
                file.write(message_text)
