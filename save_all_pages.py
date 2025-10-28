import requests
from bs4 import BeautifulSoup

PAGES = [
    "https://www.liquid-aesthetik.de/",
    "https://www.liquid-aesthetik.de/impressum/",
    "https://www.liquid-aesthetik.de/kontakt/",
    "https://www.liquid-aesthetik.de/preisliste/",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
}


def scrape_page(url):
    """Extrahiert reinen Text einer Seite."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Unwichtige Elemente entfernen
        for tag in soup(["script", "style", "noscript", "svg", "footer", "nav", "form", "iframe"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        text = "\n".join(line for line in text.splitlines() if line.strip())
        print(f"✅ {url} geladen ({len(text)} Zeichen)")
        return f"\n\n### Quelle: {url}\n{text}\n"
    except Exception as e:
        print(f"❌ Fehler bei {url}: {e}")
        return f"\n\n### Quelle: {url}\nFehler beim Laden: {e}\n"


if __name__ == "__main__":
    full_text = ""
    for url in PAGES:
        full_text += scrape_page(url)

    with open("website_data.txt", "w", encoding="utf-8") as f:
        f.write(full_text)

    print("\n💾 Fertig! Alle Seiten wurden in website_data.txt gespeichert.")
