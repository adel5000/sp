<?php
// config.php - ملف الإعدادات
include 'config.php';

// رابط API لجلب الأسعار
$api_url = "https://sp-today.com/app_api/cur_damascus.json";
$response = file_get_contents($api_url);
$data = json_decode($response, true);

$currencies_to_track = ["USD", "EUR", "SAR"];
$messages = [];

if ($data) {
    foreach ($data as $currency) {
        if (in_array($currency['name'], $currencies_to_track)) {
            $currency_name = $currency['ar_name'];
            $ask_price = $currency['bid'];
            $change = $currency['change'];
            $arrow = $currency['arrow'];

            // تحديد رمز السهم
            if ($change > 0) {
                $arrow_emoji = "↗️ \n🐇   قفز الارنب";
            } elseif ($change < 0) {
                $arrow_emoji = "↙️ \n🐇   تزحلط الارنب";
            } else {
                $arrow_emoji = "⏹️";
            }
            if ($currency['name'] == "SAR") {
                $flag = "🇸🇦";
            } else if ($currency['name'] == "EUR") {
                $flag = "🇪🇺";
            } else {
                $flag = "🇺🇸";
            }
            // تكوين الرسالة
            $messages[] = "\n" . $flag ."$currency_name: $ask_price ل.س\nالتغيير: $change $arrow_emoji";
        }
    }

    if (!empty($messages)) {
        $message_text = "\n🔹 تحديث أسعار الصرف :\n" . implode("\n\n", $messages);

        // فحص آخر رسالة تم إرسالها لمنع التكرار
        $last_price_file = 'last_price.txt';
        $last_price = file_exists($last_price_file) ? file_get_contents($last_price_file) : '';

        if ($message_text !== $last_price) {
            // إرسال الرسالة إلى التلغرام
            $telegram_url = "https://api.telegram.org/bot$telegram_token/sendMessage?chat_id=$chat_id&text=" . urlencode($message_text);
            file_get_contents($telegram_url);

            // تحديث آخر سعر مخزن
            file_put_contents($last_price_file, $message_text);
        }
    }
}
?>