# 🌍 GEO Content-Optimizer for Legacy Websites

Eine modulare Python-Automatisierungs-Pipeline zur datenbasierten Analyse und Modernisierung von Legacy-CMS-Inhalten (WordPress) für KI-Suchmaschinen (**Generative Engine Optimization / GEO** wie Perplexity, ChatGPT Search & Google AI Overviews).

---

## 🚀 Executive Summary

Ehemalige Erfolgs-Websites und Reiseblogs verzeichnen oft ein hohes Suchpotenzial, büßen aber mangels moderner Struktur und GEO-Signalen kontinuierlich Klickraten (CTR) ein. 

Dieses System schließt die Lücke zwischen klassischem CMS-Content und maschinenlesbaren KI-Formaten. Es analysiert Performance-Daten via Google Search Console API, reichert unterperformende Artikel autonom über ein LLM mit strukturierten Daten (FAQs, Quick Facts, Schema.org Markup) an und spielt die optimierten Inhalte vollautomatisch via **WordPress REST API** fehlerfrei in das Live-System zurück.

---

## 🛠️ Tech Stack & Architecture

* **Automation & Scripting:** Python 3 (`pandas`, `requests`, `BeautifulSoup4`)
* **AI & GEO Layer:** OpenAI API (`gpt-4o` mit maßgeschneiderten Prompts für strukturierte Ausgaben)
* **API Integration:** Google Search Console API, WordPress REST API
* **Data Storage & State:** Local CSV Tracking (`gsc_quick_wins.csv`) & In-Memory State Checking

---

## ⚙️ Architektur & Funktionsweise (Modularer Aufbau)

Die Pipeline besteht aus drei aufeinander aufgebauten Modulen, die über einen zentralen Batch-Runner gesteuert werden:

```text
[Google Search Console API] 
       │
       ▼
[Module A: gsc_audit.py] ──> Identifiziert Low-CTR / High-Impression URLs
       │
       ▼
[Module B: geo_transformer.py] ──> Scrapt Content & reichert mit GPT-4o an (FAQs, Tables, Schema.org)
       │
       ▼
[Module C: batch_geo_optimizer.py] ──> Prüft Idempotenz & injiziert Gutenberg-Blocks via WP REST API
