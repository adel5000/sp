import requests
import json

# إعدادات API و Telegram
api_url = "https://sp-today.com/app_api/cur_damascus.json"
telegram_token = "YOUR_TELEGRAM_BOT_TOKEN"
chat_id = "YOUR_CHAT_ID"

# جلب البيانات من API
response = requests.get(api_url)
data = response.json()

# كلمة اختبار مؤقتة فقط
message_text = "Test message"

# إرسال الرسالة إلى Telegram
telegram_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage?chat_id={chat_id}&text={requests.utils.quote(message_text)}"
requests.get(telegram_url)
