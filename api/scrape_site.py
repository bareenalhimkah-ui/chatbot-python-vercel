import requests
from bs4 import BeautifulSoup

URL = "https://www.liquid-aesthetik.de"
OUTPUT_FILE = "website_data.txt"

def scrape_website(url):
    print(f"🌐 Lade Website: {url}")
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Nur sichtbaren Text extrahieren
    for script in soup(["script", "style", "noscript"]):
        script.extract()

    text = soup.get_text(separator="\n")
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    return text

if __name__ == "__main__":
    try:
        text = scrape_website(URL)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"✅ Website erfolgreich gespeichert ({len(text)} Zeichen)")
    except Exception as e:
        print(f"❌ Fehler beim Scrapen: {e}")
