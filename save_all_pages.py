import requests
from bs4 import BeautifulSoup

# Liste der Seiten, die du speichern willst
PAGES = [
    "https://www.liquid-aesthetik.de/",
    "https://www.liquid-aesthetik.de/impressum/",
]


def scrape_page(url):
    """Lädt eine einzelne Seite und extrahiert Text."""
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        # Entferne überflüssige Skripte, Menüs etc.
        for tag in soup(["script", "style", "noscript", "svg", "footer", "nav"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        print(f"✅ {url} geladen ({len(text)} Zeichen)")
        return f"\n\n### Quelle: {url}\n{text}\n"
    except Exception as e:
        print(f"❌ Fehler bei {url}: {e}")
        return f"\n\n### Quelle: {url}\nFehler beim Laden: {e}\n"

if __name__ == "__main__":
    full_text = ""
    for url in PAGES:
        full_text += scrape_page(url)
    
    # Alles in eine Datei schreiben
    with open("website_data.txt", "w", encoding="utf-8") as f:
        f.write(full_text)
    
    print("\n💾 Alle Seiten wurden in website_data.txt gespeichert!")
