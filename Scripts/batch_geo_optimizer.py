import base64
import json
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

# --- KONFIGURATION ---
WP_SITE_URL = "https://www.globushopper.de"
WP_USER = "----"
WP_APP_PASSWORD = "----"
client = OpenAI(api_key="----")
CSV_FILE = "gsc_quick_wins.csv"

def get_wp_auth_header():
  credentials = f"{WP_USER}:{WP_APP_PASSWORD}"
  token = base64.b64encode(credentials.encode()).decode("utf-8")
  return {
      "Authorization": f"Basic {token}",
      "Content-Type": "application/json",
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      ),
  }


def get_post_id_by_url(url):
  """Ermittelt die WordPress Post-ID dynamisch über den URL-Slug"""
  slug = url.strip("/").split("/")[-1]
  api_url = f"{WP_SITE_URL}/wp-json/wp/v2/posts?slug={slug}"
  response = requests.get(api_url, headers=get_wp_auth_header())

  if response.status_code == 200 and response.json():
    return response.json()[0]["id"]
  return None


def scrape_article_content(url):
  """Scrapt den Haupttext des Ziel-Artikels"""
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
  """Generiert das passende GEO-Paket via OpenAI mit Sicherheits-Check gegen None-Antworten"""
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
          Spaltenstruktur: ['Spot / Highlight', 'Kategorie', 'Beschreibung / Details', 'Praxis-Tipp']. Nutze ausschließlich reale Fakten aus dem Text!
        """

  prompt = f"""
    Du bist ein erfahrener Reise-Blogger auf Globushopper.de. 
    Schreibe absolut authentisch im persönlichen **"Du"**, nahbar, lebendig und direkt aus der Praxis.
    {focus_instruction}

    WICHTIGE REGELN & SCHUTZMASNAHMEN:
    1. ANTI-HALLUZINATIONS-SCHUTZ: Nutze AUSSCHLIESSLICH Fakten, Daten und Informationen, die direkt im untenstehenden ARTIKEL-TEXT stehen. Erfinde KEINE Zahlen, Namen oder Fakten.
    2. INHALTSVERZEICHNIS-SCHUTZ: Verwende in der "quick_facts_box_html" und der "insider_tip_box_html" KEINE echten HTML-Überschriften (wie <h3>, <h4>). Nutze fetten Text (<strong>) für Titel innerhalb der Boxen!

    ARTIKEL-URL: {url}
    ARTIKEL-TEXT:
    {article_text[:4000]}

    Erstelle im sauberen JSON-Format folgende 7 Felder:
    1. "meta_title": SEO-Title für Yoast (max. 60 Zeichen).
    2. "meta_description": Meta-Description für Yoast (max. 155 Zeichen).
    3. "executive_summary_html": Einleitung als <p>-Tag im Du-Stil.
    4. "quick_facts_box_html": HTML-Infobox mit grünem Akzent (ohne h3/h4!).
    5. "insider_tip_box_html": Zweite Infobox für den Geheimtipp (ohne h3/h4!).
    6. "comparison_table_html": Ausführliche HTML-Tabelle im sauberen Design.
    7. "faq_schema_json": Valides JSON-LD Schema.org "FAQPage" Skript mit 3–4 Fragen.

    Antworte AUSSCHLIESSLICH mit einem gültigen JSON-Objekt.
    """

  response = client.chat.completions.create(
      model="gpt-4o",
      messages=[{"role": "user", "content": prompt}],
      response_format={"type": "json_object"},
      temperature=0.3,
  )

  content = response.choices[0].message.content
  if not content:
    raise Exception(
        "OpenAI hat eine leere Antwort (None) zurückgegeben. Überspringe"
        " diesen Artikel."
    )

  return json.loads(content)


def process_single_article(url):
  """Steuert die komplette Optimierung für eine URL"""
  print(f"\n--- Starte Verarbeitung für: {url} ---")

  post_id = get_post_id_by_url(url)
  if not post_id:
    print(
        f"❌ Konnte keine WordPress Post-ID für {url} finden. Überspringe..."
    )
    return

  article_type = (
      "groundhopping" if "groundhopping" in url.lower() else "travel"
  )
  print(f"-> Erkannte Post-ID: {post_id} | Artikel-Typ: {article_type}")

  wp_url = f"{WP_SITE_URL}/wp-json/wp/v2/posts/{post_id}?context=edit"
  response = requests.get(wp_url, headers=get_wp_auth_header())
  if response.status_code != 200:
    print(f"❌ Fehler beim Abrufen des Posts von WP: {response.status_code}")
    return

  post_data = response.json()
  current_content = post_data["content"]["raw"]

  marker_phrase = "📊 Fakten & Übersicht"
  if marker_phrase in current_content:
    print(
        f"⚠️ Post ID {post_id} wurde bereits optimiert. Aktualisiere nur"
        " Meta-Daten."
    )
    geo_data = generate_pro_geo_enhancements(
        scrape_article_content(url), url, article_type
    )
    payload = {
        "status": "publish",
        "title": post_data["title"]["raw"],
        "meta": {
            "_yoast_wpseo_title": geo_data.get("meta_title"),
            "_yoast_wpseo_desc": geo_data.get("meta_description"),
        },
    }
    requests.post(wp_url, headers=get_wp_auth_header(), json=payload)
    return

  article_text = scrape_article_content(url)
  geo_data = generate_pro_geo_enhancements(article_text, url, article_type)

  summary_html = f"<!-- wp:html -->\n<div style='clear: both; display: block; width: 100%; margin: 20px 0;'>{geo_data.get('executive_summary_html', '')}</div>\n<!-- /wp:html -->"
  quick_facts_html = f"<!-- wp:html -->\n<div style='clear: both; display: block; width: 100%; margin: 20px 0;'>{geo_data.get('quick_facts_box_html', '')}</div>\n<!-- /wp:html -->"
  insider_tip_html = f"<!-- wp:html -->\n<div style='clear: both; display: block; width: 100%; margin: 20px 0;'>{geo_data.get('insider_tip_box_html', '')}</div>\n<!-- /wp:html -->"

  raw_table = geo_data.get("comparison_table_html", "").replace("\n", " ")
  styled_table = raw_table.replace("<table", '<table class="globus-table"')

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
    faq_schema_str = (
        json.dumps(faq_schema, ensure_ascii=False)
        if isinstance(faq_schema, dict)
        else faq_schema
    )
    faq_html_block = f"""<!-- wp:html -->
<div style="clear: both; display: block; width: 100%; margin: 20px 0;">
<script type="application/ld+json">
{faq_schema_str}
</script>
</div>
<!-- /wp:html -->"""

  top_block = (
      summary_html
      + "\n\n"
      + quick_facts_html
      + "\n\n<hr style='margin: 40px 0; clear: both; display: block;'>\n\n"
  )

  if "</p>" in current_content:
    parts = current_content.split("</p>")
    parts.insert(min(1, len(parts) - 1), "</p>" + "\n\n" + table_html + "\n\n")
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

  update_response = requests.post(wp_url, headers=get_wp_auth_header(), json=payload)
  if update_response.status_code == 200:
    print(f"✅ Erfolg! Post ID {post_id} erfolgreich optimiert.")
  else:
    print(f"❌ Fehler beim Update von Post ID {post_id}: {update_response.text}")


if __name__ == "__main__":
  df = pd.read_csv(CSV_FILE)
  print(
      f"GSC Quick-Wins geladen. Starte Batch-Verarbeitung für {len(df)}"
      " Artikel..."
  )

  for index, row in df.iterrows():
    target_url = row["url"]
    try:
      process_single_article(target_url)
    except Exception as e:
      print(f"❌ Unerwarteter Fehler bei {target_url}: {e}")

    time.sleep(2)  # Kurze Pause gegen Rate-Limits