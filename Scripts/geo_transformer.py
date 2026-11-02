import json
import os
from bs4 import BeautifulSoup
from openai import OpenAI
import requests

# OPENAI API KEY SETUP (setze deinen API Key hier ein oder via Umweltvariable)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "----")
client = OpenAI(api_key=OPENAI_API_KEY)

# Test-Ziel-URL (Unser Platz 1 Quick-Win)
TARGET_URL = "https://www.globushopper.de/christusstatue-rio-tipps-reisebericht-anreise/"


def scrape_article_content(url):
  """Scrapt den Haupttext des Artikels von der Website"""
  print(f"Lade Artikelinhalte von: {url} ...")
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      )
  }
  response = requests.get(url, headers=headers)

  if response.status_code != 200:
    raise Exception(f"Fehler beim Laden der Seite: {response.status_code}")

  soup = BeautifulSoup(response.text, "html.parser")

  # Versucht den Haupt-Content-Bereich von WordPress zu finden
  content_div = (
      soup.find("div", class_="entry-content")
      or soup.find("article")
      or soup.find("main")
  )

  if not content_div:
    raw_text = soup.get_text()
  else:
    # Entferne unötige Skripte / Styles
    for tag in content_div(["script", "style", "iframe", "noscript"]):
      tag.decompose()
    raw_text = content_div.get_text(separator="\n")

  # Bereinigung
  clean_lines = [
      line.strip() for line in raw_text.split("\n") if len(line.strip()) > 30
  ]
  return "\n\n".join(clean_lines[:40])  # Konzentriert auf die Kernabschnitte


def generate_geo_enhancements(article_text, url):
  """Nutzt ein LLM, um GEO-Elemente und optimierte Snippets zu generieren"""
  print("Generiere GEO-Optimierungen via LLM...")

  prompt = f"""
    Du bist ein Experte für Generative Engine Optimization (GEO) und Reise-Content.
    Deine Aufgabe ist es, einen bestehenden Reiseblog-Artikel so aufzubereiten, dass er von KI-Suchmaschinen (ChatGPT, Perplexity, Google AI Overviews) optimal zitiert wird und eine viel höhere Click-Through-Rate (CTR) erzielt.

    ARTIKEL-URL: {url}
    ARTIKEL-TEXT:
    {article_text[:4000]}

    Bitte erstelle im sauberen JSON-Format folgende Elemente:
    1. "meta_title": Ein hochattraktiver, klickstarker Title-Tag (max. 60 Zeichen).
    2. "meta_description": Eine neugierig machende Meta-Description mit klarem Call-to-Action (max. 155 Zeichen).
    3. "quick_facts_box_html": Eine prägnante, visuell ansprechende HTML-Infobox (für den Artikelanfang) mit den wichtigsten Fakten (z.B. Highlight, Beste Reisezeit, Anreise-Tipp, Kosten/Tickets).
    4. "faq_schema_json": Ein valides JSON-LD Schema.org "FAQPage" Skript mit 3–4 den am häufigsten gestellten Fragen & präzisen Antworten basierend auf dem Text.
    5. "geo_summary_paragraph": Ein perfekt geschriebener 3-Sätze-Absatz für Sprachmodelle, der die Kernbotschaft des Artikels direkt auf den Punkt bringt.

    Antworte AUSSCHLIESSLICH mit einem gültigen JSON-Objekt.
    """

  response = client.chat.completions.create(
      model="gpt-4o",
      messages=[{"role": "user", "content": prompt}],
      response_format={"type": "json_object"},
      temperature=0.3,
  )

  return json.loads(response.choices[0].message.content)


def save_human_in_the_loop_preview(geo_data, original_url):
  """Speichert das Ergebnis in einer lokalen HTML-Datei zur manuellen Überprüfung"""
  filename = "geo_preview_christusstatue.html"

  html_content = f"""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <title>GEO Preview - {original_url}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f9f9f9; color: #333; }}
            .container {{ max-width: 800px; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ color: #1a365d; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }}
            h2 {{ color: #2b6cb0; margin-top: 25px; }}
            .meta-box {{ background: #ebf8ff; border-left: 4px solid #3182ce; padding: 15px; margin-bottom: 20px; }}
            .quick-facts {{ background: #f7fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 20px; margin: 20px 0; }}
            pre {{ background: #2d3748; color: #f7fafc; padding: 15px; border-radius: 6px; overflow-x: auto; }}
            .label {{ font-weight: bold; color: #4a5568; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>GEO Transformation Preview (Human-in-the-Loop)</h1>
            <p><span class="label">Original URL:</span> <a href="{original_url}" target="_blank">{original_url}</a></p>

            <div class="meta-box">
                <h2>1. Optimierte Snippets (CTR-Boost)</h2>
                <p><span class="label">Meta Title:</span> {geo_data.get('meta_title')}</p>
                <p><span class="label">Meta Description:</span> {geo_data.get('meta_description')}</p>
            </div>

            <h2>2. Quick-Facts Box (Header-Element für den Artikel)</h2>
            <div class="quick-facts">
                {geo_data.get('quick_facts_box_html')}
            </div>

            <h2>3. AI Overview Summary Paragraph</h2>
            <p><em>{geo_data.get('geo_summary_paragraph')}</em></p>

            <h2>4. Generiertes FAQ JSON-LD Schema (für Head/WordPress)</h2>
            <pre><code>{json.dumps(geo_data.get('faq_schema_json'), indent=2, ensure_ascii=False)}</code></pre>
        </div>
    </body>
    </html>
    """

  with open(filename, "w", encoding="utf-8") as f:
    f.write(html_content)

  print(
      f"\n--> FERTIG! Vorschau-Datei wurde erstellt: '{filename}'"
  )
  print(
      "Öffne diese HTML-Datei im Browser, um die KI-Vorschau zu prüfen!"
  )


if __name__ == "__main__":
  try:
    content = scrape_article_content(TARGET_URL)
    geo_results = generate_geo_enhancements(content, TARGET_URL)
    save_human_in_the_loop_preview(geo_results, TARGET_URL)
  except Exception as e:
    print(f"Fehler bei der Ausführung: {e}")