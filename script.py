import cloudscraper
from bs4 import BeautifulSoup
from flask import Flask, jsonify

app = Flask(__name__)

# الرابط الأساسي
url = "https://sp-today.com/en"

def get_gold_prices():
    scraper = cloudscraper.create_scraper()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    response = scraper.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        gold_table = soup.find("table", class_="table-hover")

        if gold_table:
            rows = gold_table.find_all("tr")[1:]  # تجاهل العنوان
            gold_prices = {}

            for row in rows:
                columns = row.find_all("td")
                if len(columns) >= 2:
                    gold_type = row.find("th").text.strip()
                    price = columns[1].find("strong").text.strip()
                    gold_prices[gold_type] = price

            return {"success": True, "gold_prices": gold_prices}
        else:
            return {"success": False, "error": "Gold price table not found"}
    else:
        return {"success": False, "error": f"Failed to fetch page (status code: {response.status_code})"}

@app.route("/")
def home():
    return jsonify({"message": "Welcome to Gold Price Scraper API!"})

@app.route("/scrape_gold_prices")
def scrape_gold_prices():
    result = get_gold_prices()
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
