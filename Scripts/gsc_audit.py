import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Konfiguration - Ausschließlich für Globushopper
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
SITE_URL = "https://www.globushopper.de/"
KEY_FILE = "client_secret.json"


def authenticate_gsc():
  """Authentifizierung über den Service Account"""
  creds = service_account.Credentials.from_service_account_file(
      KEY_FILE, scopes=SCOPES
  )
  return creds


def fetch_gsc_data(service, site_url):
  """Zieht Daten ausschließlich für die definierte site_url"""
  request = {
      "startDate": "2026-07-01",  # Zeitraum anpassbar
      "endDate": "2026-10-15",
      "dimensions": ["page"],
      "rowLimit": 1000,
  }

  # Korrigiert von 'site' auf 'siteUrl'
  response = service.searchanalytics().query(
      siteUrl=site_url, body=request
  ).execute()
  return response.get("rows", [])


def process_data(rows):
  """Verarbeitet die Daten zu Quick-Win-Kandidaten"""
  data = []
  for row in rows:
    url = row["keys"][0]
    clicks = row["clicks"]
    impressions = row["impressions"]
    ctr = row["ctr"]
    position = row["position"]
    data.append({
        "url": url,
        "clicks": clicks,
        "impressions": impressions,
        "ctr": ctr,
        "position": position,
    })

  df = pd.DataFrame(data)

  # Filter für Quick Wins: Hohe Impressions, niedrige CTR (< 2%), gute Rank-Position
  quick_wins = df[
      (df["impressions"] > 300) & (df["ctr"] < 0.02) & (df["position"] <= 20)
  ]
  quick_wins = quick_wins.sort_values(by="impressions", ascending=False)
  return quick_wins


if __name__ == "__main__":
  print("Authentifiziere mit Service Account...")
  creds = authenticate_gsc()
  service = build("webmasters", "v3", credentials=creds)

  print(f"Lese Daten exklusiv für {SITE_URL} aus...")
  raw_rows = fetch_gsc_data(service, SITE_URL)

  if raw_rows:
    df_results = process_data(raw_rows)
    print("\n--- GEFILTERTE QUICK-WINS FÜR GLOBUSHOPPER ---")
    print(df_results.head(15).to_string(index=False))

    df_results.to_csv("gsc_quick_wins.csv", index=False)
    print("\nDaten erfolgreich in 'gsc_quick_wins.csv' gespeichert!")
  else:
    print(
        f"Keine Daten für {SITE_URL} gefunden. Bitte prüfe die Schreibweise"
        " der Property."
    )