import requests
from bs4 import BeautifulSoup

URL = "https://www.liquid-aesthetik.de"
OUTPUT_FILE = "website_data.txt"

# Website scrapen und Text extrahieren
def scrape_website(url):
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.extract()

    text = soup.get_text("\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)

if __name__ == "__main__":
    try:
        text = scrape_website(URL)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(text)
        print("Website erfolgreich gespeichert")
    except Exception as e:
        print("Fehler beim Scrapen:", e)
