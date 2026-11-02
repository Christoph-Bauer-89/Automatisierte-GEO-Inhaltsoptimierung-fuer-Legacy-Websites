import base64
import json
import os
import requests

# WORDPRESS CONFIGURATION
WP_SITE_URL = (
    "https://www.globushopper.de"  # Ohne Slash am Ende für REST API
)
WP_USER = "----"  # Dein echter WP-Login-Name (keine E-Mail!)
WP_APP_PASSWORD = (
    "----"  # Das generierte Anwendungs-Passwort
)

# Beispiel: Post-ID für den Christusstatue-Artikel (hier deine getestete ID 2650)
POST_ID = 2650


def get_wp_auth_header():
  """Erstellt den Auth Header inkl. Browser-User-Agent gegen Firewall-Sperren"""
  credentials = f"{WP_USER}:{WP_APP_PASSWORD}"
  token = base64.b64encode(credentials.encode()).decode("utf-8")
  return {
      "Authorization": f"Basic {token}",
      "Content-Type": "application/json",
      # Verhindert Bot-Blockaden durch Webserver, Cloudflare oder Firewalls
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      ),
  }


def update_wordpress_post(
    post_id, meta_title, meta_desc, quick_facts_html, status="draft"
):
  """Aktualisiert den bestehenden Artikel in WordPress (als Entwurf oder Live)"""
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

  # GEO-Erweiterung: Quick-Facts-Box oben voranstellen
  enhanced_content = quick_facts_html + "\n\n" + current_content

  # Payload für das WordPress Update
  payload = {
      "content": enhanced_content,
      "status": status,  # "draft" = Nur im Backend als Entwurf, "publish" = direkt live
      "title": post_data["title"]["raw"],
  }

  print(f"Sende GEO-optimiertes Update an WordPress (Status: {status})...")
  update_response = requests.post(url, headers=get_wp_auth_header(), json=payload)

  if update_response.status_code == 200:
    print(
        f"Erfolgreich aktualisiert! Post ID {post_id} wurde auf Status '{status}'"
        " gesetzt."
    )
  else:
    print(f"Fehler beim Update: {update_response.status_code}")
    print(update_response.text)


if __name__ == "__main__":
  # Beispielhafter Testlauf mit den generierten GEO-Daten
  sample_quick_facts = """
    <div class="geo-quick-facts" style="background: #f7fafc; border: 1px solid #e2e8f0; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
        <h3>Quick Facts zur Christusstatue Rio</h3>
        <ul>
            <li><strong>Highlight:</strong> Weltwunder mit atemberaubender Aussicht</li>
            <li><strong>Beste Reisezeit:</strong> März</li>
            <li><strong>Anreise-Tipp:</strong> Zahnradbahn am Morgen</li>
            <li><strong>Kosten/Tickets:</strong> Online buchen für besten Preis</li>
        </ul>
    </div>
    """

  # Status bleibt auf "draft", damit es sicher als Entwurf im Backend landet
  update_wordpress_post(
      post_id=POST_ID,
      meta_title="Christusstatue Rio: Tipps & Anreise leicht gemacht",
      meta_desc="Entdecke die besten Tipps für deinen Besuch der Christusstatue in Rio. Erfahre alles über Anreise, beste Zeiten & mehr!",
      quick_facts_html=sample_quick_facts,
      status="draft",
  )