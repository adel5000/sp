@app.route('/')
def run_script():
    response = requests.get(api_url)
    data = response.json()

    messages = []
    send_update = False  # متغير لتحديد ما إذا كان يجب إرسال التحديث
    before = 0
    after  = 0
    if data:
        current_prices = {}

        # قراءة آخر الأسعار من الملف
        try:
            with open(last_price_file, 'r') as file:
                last_prices = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            last_prices = {}

        # إرجاع محتويات ملف last_price.json لمراجعتها
        return jsonify({"last_prices": last_prices}), 200

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
                # تحديد العلم
                flags = {
                    "USD": "🇺🇸", "SAR": "🇸🇦", "EUR": "🇪🇺", "TRY": "🇹🇷",
                    "AED": "🇦🇪", "JOD": "🇯🇴", "EGP": "🇪🇬", "KWD": "🇰🇼"
                }
                flag = flags.get(currency['name'], "🏳️")

                # إضافة ملاحظة لسعر الدولار
                usd_message = ""
                if currency['name'] == "USD" and last_usd_price is not None:
                    if ask_price > last_usd_price:
                        usd_message = "📉 انخفاض في قيمة الليرة السورية أمام الدولار"
                        send_update = True
                    elif ask_price < last_usd_price:
                        usd_message = "📈 تحسن في قيمة الليرة السورية أمام الدولار"
                        send_update = True
                    # إذا تغير سعر الدولار، نقوم بتحديد الإرسال
                    if ask_price != last_usd_price:
                        send_update = True  

                # تكوين الرسالة
                message = f"""{flag} {currency_name}
{usd_message}
🔹 سعر المبيع : {bid_price} ل.س  
🔹 سعر الشراء : {ask_price} ل.س  
🔹 التغيير : {change}
"""
                messages.append(message)

                # تخزين السعر في القاموس
                current_prices[currency['name']] = ask_price

        # إرسال التحديث فقط إذا تغير سعر الدولار
        if send_update and messages:
            message_text = "\n🔹 تحديث أسعار الصرف :\n\n" + "\n\n".join(messages[:])

            # إرسال الرسالة إلى Telegram
            telegram_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage?chat_id={chat_id}&text={requests.utils.quote(message_text)}"
            try:
                # تفعيل السطر التالي إذا كنت تريد إرسال الرسالة فعليًا
                response = requests.get(telegram_url)
                response.raise_for_status()
                print("✅ Message ready to be sent:\n", message_text)

                # تحديث آخر الأسعار في الملف
                with open(last_price_file, 'w') as file:
                    json.dump(current_prices, file)

                return jsonify({"status": "success", "message": "تم إرسال التحديث إلى Telegram ✅"}), 200
            except requests.exceptions.RequestException as e:
                return jsonify({"status": "error", "message": str(e)}), 500
        else:
            return jsonify({"status": "no_update", "message": "لم يتغير سعر الدولار، لا حاجة للتحديث." , "before" : before, "after" : after}), 200
