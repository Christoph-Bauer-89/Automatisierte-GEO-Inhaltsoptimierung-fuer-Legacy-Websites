import base64
import json
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

# --- KONFIGURATION DER ARTIKELART ---
# Wähle hier, worum es in dem Artikel primär geht:
# Optionen: "groundhopping" (Stadion/Verein) oder "travel" (Stadt/Land/Sehenswürdigkeit)
ARTICLE_TYPE = "travel"  # Bei Bedarf auf "groundhopping" stellen

# Deine Zugangsdaten und Konfiguration
WP_SITE_URL = "https://www.globushopper.de"
WP_USER = "----"
WP_APP_PASSWORD = "----"
client = OpenAI(api_key="----")

# Test-URL und Post-ID
TARGET_URL = "https://www.globushopper.de/highlands-reisebericht/"
POST_ID = 1389

def get_wp_auth_header():
  """Erstellt den Auth Header inkl. Browser-User-Agent gegen Firewall-Sperren"""
  credentials = f"{WP_USER}:{WP_APP_PASSWORD}"
  token = base64.b64encode(credentials.encode()).decode("utf-8")
  return {
      "Authorization": f"Basic {token}",
      "Content-Type": "application/json",
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      ),
  }


def scrape_article_content(url):
  """Scrapt den Haupttext des Ziel-Artikels"""
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
  content_div = (
      soup.find("div", class_="entry-content")
      or soup.find("article")
      or soup.find("main")
  )

  if not content_div:
    raw_text = soup.get_text()
  else:
    for tag in content_div(["script", "style", "iframe", "noscript"]):
      tag.decompose()
    raw_text = content_div.get_text(separator="\n")

  clean_lines = [
      line.strip() for line in raw_text.split("\n") if len(line.strip()) > 30
  ]
  return "\n\n".join(clean_lines[:40])


def generate_pro_geo_enhancements(article_text, url, article_type):
  """Generiert das passende GEO-Paket (mit Anti-Halluzinations-Schutz & TOC-Schutz) via OpenAI"""
  print(
      f"Generiere GEO-Optimierungen für Artikel-Typ: [{article_type}] strikt"
      " faktenbasiert..."
  )

  if article_type == "groundhopping":
    focus_instruction = """
        Du bist Experte für GEO und Groundhopping. 
        - Fokus auf: Stadion-Atmosphäre, Vereinshistorie, Liga und Ticket-Infos.
        - Quick Facts: Highlight, Beste Reisezeit, Kosten-Richtung, Anreise-Tipp.
        - Insider-Tipp: Stadionwurst, Fanszene oder Ticket-Geheimtipp.
        - Tabelle: Stadionname, Kapazität, Liga, Besonderheiten.
        """
  else:
    focus_instruction = """
        Du bist Experte für GEO und Reise-Blogger. 
        - Fokus auf: Kulturelle Highlights, Sehenswürdigkeiten, authentisches Lokalkolorit und praktische Reisetipps.
        - Quick Facts: Top-Sehenswürdigkeit, Beste Reisezeit, Budget-Tipp, Fortbewegung.
        - Insider-Tipp: Ein echter Geheimtipp abseits der Touristenpfade (Café, Aussichtspunkt, Kultur).
        - Tabelle: Erstelle eine ausführliche, mehrzeilige Tabelle (mindestens 5-6 Zeilen) mit den wichtigsten Highlights, Stadtteilen oder Top-Spots aus dem Text. 
          Spaltenstruktur der Tabelle: ['Spot / Highlight', 'Kategorie', 'Beschreibung / Details', 'Praxis-Tipp']. Nutze ausschließlich reale Fakten aus dem Text!
        """

  prompt = f"""
    Du bist ein erfahrener Reise-Blogger auf Globushopper.de. 
    Schreibe absolut authentisch im persönlichen **"Du"**, nahbar, lebendig und direkt aus der Praxis.
    {focus_instruction}

    WICHTIGE REGELN & SCHUTZMASNAHMEN:
    1. ANTI-HALLUZINATIONS-SCHUTZ: Nutze AUSSCHLIESSLICH Fakten, Daten und Informationen, die direkt im untenstehenden ARTIKEL-TEXT stehen. Erfinde KEINE Zahlen, Namen oder Fakten. Wenn eine Angabe fehlt, lasse sie weg.
    2. INHALTSVERZEICHNIS-SCHUTZ: Verwende in der "quick_facts_box_html" und der "insider_tip_box_html" KEINE echten HTML-Überschriften (wie <h3>, <h4>, <h5>). Verwende stattdessen fetten Text (<strong>) für Titel innerhalb dieser Boxen, damit Inhaltsverzeichnis-Plugins sie ignorieren!

    ARTIKEL-URL: {url}
    ARTIKEL-TEXT:
    {article_text[:4000]}

    Erstelle im sauberen JSON-Format folgende 7 Felder:
    1. "meta_title": Ein klickstarker SEO-Title für Yoast (max. 60 Zeichen).
    2. "meta_description": Eine neugierig machende Meta-Description für Yoast (max. 155 Zeichen).
    3. "executive_summary_html": Ein knackiger Einleitungs-Absatz (als <p>-Tag im Du-Stil).
    4. "quick_facts_box_html": Eine formschöne HTML-Infobox mit grünem Akzent für den Überblick (ohne h3/h4 Überschriften!).
    5. "insider_tip_box_html": Eine zweite Infobox mit grünem Akzent für den ultimativen Geheimtipp (ohne h3/h4 Überschriften!).
    6. "comparison_table_html": Eine ausführliche HTML-Tabelle im sauberen Design (Tabellenkopf mit Globushopper-Grün #00a624 als Hintergrund und weißer Schrift, dunkler Text für gute Lesbarkeit, klare Ränder).
    7. "faq_schema_json": Ein valides JSON-LD Schema.org "FAQPage" Skript mit 3–4 passenden Fragen & Antworten basierend auf dem Text.

    Antworte AUSSCHLIESSLICH mit einem gültigen JSON-Objekt.
    """

  response = client.chat.completions.create(
      model="gpt-4o",
      messages=[{"role": "user", "content": prompt}],
      response_format={"type": "json_object"},
      temperature=0.3,
  )

  return json.loads(response.choices[0].message.content)


def publish_pro_geo_to_wordpress(post_id, geo_data):
  """Pusht die Daten fehlerfrei über Gutenberg-HTML-Blöcke in den WordPress-Live-Post 
     und verhindert doppeltes Einfügen sowie Block-Sprengungen."""
  url = f"{WP_SITE_URL}/wp-json/wp/v2/posts/{post_id}?context=edit"

  print(f"Hole aktuellen Inhalt von Post ID {post_id}...")
  response = requests.get(url, headers=get_wp_auth_header())
  if response.status_code != 200:
    raise Exception(
        f"Fehler beim Abrufen des Posts: {response.status_code} -"
        f" {response.text}"
    )

  post_data = response.json()
  current_content = post_data["content"]["raw"]

  # --- SICHERHEITSPRÜFUNG GEGEN DOPPELTES EINFÜGEN ---
  marker_phrase = "📊 Fakten & Übersicht"
  if marker_phrase in current_content:
    print(
        f"⚠️ Hinweis: Post ID {post_id} wurde bereits optimiert ('{marker_phrase}' gefunden)."
    )
    print("Überspringe das erneute Einfügen der Boxen, um Duplikate zu verhindern.")
    
    payload = {
        "status": "publish",
        "title": post_data["title"]["raw"],
        "meta": {
            "_yoast_wpseo_title": geo_data.get("meta_title"),
            "_yoast_wpseo_desc": geo_data.get("meta_description"),
        },
    }
    update_response = requests.post(url, headers=get_wp_auth_header(), json=payload)
    if update_response.status_code == 200:
      print(f"Erfolg! Meta-Daten für Post ID {post_id} wurden aktualisiert.")
    return

  # --- ELEMENTE FÜR DEN ERSTDURCHLAUF GENERIEREN ---
  summary_html = (
      f"<!-- wp:html -->\n<div style='clear: both; display: block; width: 100%; margin: 20px 0;'>"
      f"{geo_data.get('executive_summary_html', '')}</div>\n<!-- /wp:html -->"
  )
  quick_facts_html = (
      f"<!-- wp:html -->\n<div style='clear: both; display: block; width: 100%; margin: 20px 0;'>"
      f"{geo_data.get('quick_facts_box_html', '')}</div>\n<!-- /wp:html -->"
  )
  insider_tip_html = (
      f"<!-- wp:html -->\n<div style='clear: both; display: block; width: 100%; margin: 20px 0;'>"
      f"{geo_data.get('insider_tip_box_html', '')}</div>\n<!-- /wp:html -->"
  )
  
  # Tabelle bereinigen: Zeilenumbrüche entfernen, damit Gutenberg den Block nicht "sprengt"
  raw_table = geo_data.get('comparison_table_html', '').replace('\n', ' ')
  styled_table = raw_table.replace('<table', '<table class="globus-table"')
  
  table_html = f"""<!-- wp:html -->
<div style="clear: both; display: block; width: 100%; margin: 50px 0; overflow-x: auto;">
  <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); padding: 25px; color: #2d3748;">
    <h3 style="margin-top: 0; margin-bottom: 15px; font-size: 1.25rem; color: #1a202c; border-bottom: 2px solid #00a624; padding-bottom: 8px; display: inline-block;">{marker_phrase}</h3>
    <div style="width: 100%;">
      <style>
        .globus-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.95rem; text-align: left; }}
        .globus-table th {{ background-color: #00a624 !important; color: #ffffff !important; padding: 12px 15px; font-weight: bold; border: none; }}
        .globus-table td {{ padding: 12px 15px; border-bottom: 1px solid #edf2f7; color: #2d3748; }}
        .globus-table tr:nth-child(even) {{ background-color: #f8fafc; }}
      </style>
      {styled_table}
    </div>
  </div>
</div>
<!-- /wp:html -->"""

  faq_schema = geo_data.get("faq_schema_json", "")
  faq_html_block = ""
  if faq_schema:
    if isinstance(faq_schema, dict):
      faq_schema_str = json.dumps(faq_schema, ensure_ascii=False)
    else:
      faq_schema_str = faq_schema
    faq_html_block = f"""
<!-- wp:html -->
<div style="clear: both; display: block; width: 100%; margin: 20px 0;">
<script type="application/ld+json">
{faq_schema_str}
</script>
</div>
<!-- /wp:html -->
"""

  # --- PLATZIERUNG ---
  top_block = (
      summary_html
      + "\n\n"
      + quick_facts_html
      + "\n\n<hr style='margin: 40px 0; clear: both; display: block;'>\n\n"
  )

  if "</p>" in current_content:
    parts = current_content.split("</p>")
    split_index = min(1, len(parts) - 1)
    parts.insert(split_index, "</p>" + "\n\n" + table_html + "\n\n")
    middle_content = "</p>".join(parts)
  else:
    middle_content = table_html + "\n\n" + current_content

  bottom_block = (
      "\n\n"
      + insider_tip_html
      + "\n\n<hr style='margin: 40px 0; clear: both; display: block;'>\n\n"
      + faq_html_block
  )

  enhanced_content = top_block + middle_content + bottom_block

  payload = {
      "content": enhanced_content,
      "status": "publish",
      "title": post_data["title"]["raw"],
      "meta": {
          "_yoast_wpseo_title": geo_data.get("meta_title"),
          "_yoast_wpseo_desc": geo_data.get("meta_description"),
      },
  }

  print(
      f"Sende professionelles Pro-GEO-Paket an WordPress (Post ID {post_id})..."
  )
  update_response = requests.post(url, headers=get_wp_auth_header(), json=payload)

  if update_response.status_code == 200:
    print(
        f"Erfolg! Post ID {post_id} wurde fehlerfrei mit allen GEO-Komponenten"
        " aktualisiert."
    )
  else:
    print(f"Fehler beim Update: {update_response.status_code}")
    print(update_response.text)


if __name__ == "__main__":
  try:
    article_text = scrape_article_content(TARGET_URL)
    geo_results = generate_pro_geo_enhancements(
        article_text, TARGET_URL, ARTICLE_TYPE
    )
    publish_pro_geo_to_wordpress(POST_ID, geo_results)
  except Exception as e:
    print(f"Fehler bei der Ausführung: {e}")