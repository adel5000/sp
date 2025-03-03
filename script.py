import cloudscraper
from bs4 import BeautifulSoup
from flask import Flask, jsonify

app = Flask(__name__)

# الرابط الأساسي
url = "https://sp-today.com/en"

def get_prices():
    scraper = cloudscraper.create_scraper()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    response = scraper.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        # استخراج أسعار الذهب
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

        # استخراج أسعار العملات
        currency_table = soup.find("table", class_="table table-hover local-cur")
        currency_prices = {}

        if currency_table:
            rows = currency_table.find_all("tr")[1:]  # تجاهل العنوان
            for row in rows:
                columns = row.find_all("td")
                if len(columns) >= 3:
                    currency_name = columns[0].text.strip()
                    buy_price = columns[1].text.strip()
                    sell_price = columns[2].text.strip()
                    currency_prices[currency_name] = {
                        "buy_price": buy_price,
                        "sell_price": sell_price
                    }

        return {
            "success": True,
            "gold_prices": gold_prices,
            "currency_prices": currency_prices
        }
    else:
        return {"success": False, "error": f"Failed to fetch page (status code: {response.status_code})"}

@app.route("/")
def home():
    return jsonify({"message": "Welcome to Gold & Currency Prices Scraper API!"})

@app.route("/scrape_prices")
def scrape_prices():
    result = get_prices()
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
