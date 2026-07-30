#!/usr/bin/env python3
"""
Surveille la page d'actualités de l'Élysée et envoie une notification push
(via ntfy.sh) dès qu'un nouvel article mentionnant les Journées du Patrimoine
apparaît.

Utilisation locale :
    pip install requests beautifulsoup4
    python3 surveille_elysee.py

Utilisation recommandée : via GitHub Actions (voir le fichier .github/workflows/
surveille.yml fourni séparément) pour que ça tourne dans le cloud, gratuitement,
même ordinateur éteint.
"""

import json
import os
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://www.elysee.fr/toutes-les-actualites"

# Mots-clés qui indiquent que l'article concerne les JEP / la billetterie
KEYWORDS = ["patrimoine", "billetterie", "inscri", "creneau", "créneau"]

# Le topic ntfy.sh est lu depuis la variable d'environnement NTFY_TOPIC
# (définie comme secret GitHub, voir le workflow .yml). En local, vous pouvez
# faire : export NTFY_TOPIC="elysee-jep-xk92hd" avant de lancer le script.
NTFY_TOPIC = os.environ.get("NTFY_TOPIC")
if not NTFY_TOPIC:
    sys.exit("Erreur : la variable d'environnement NTFY_TOPIC n'est pas définie.")

STATE_FILE = Path("seen_links.json")


def get_articles():
    """Récupère la liste des liens d'articles actuellement sur la page."""
    resp = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r"/emmanuel-macron/\d{4}/\d{2}/\d{2}/", href):
            links.add(href)
    return links


def load_seen():
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text()))
    return set()


def save_seen(links):
    STATE_FILE.write_text(json.dumps(sorted(links)))


def notify(title, message):
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={"Title": title.encode("utf-8"), "Priority": "urgent"},
        timeout=10,
    )


def main():
    seen = load_seen()
    current = get_articles()
    new_links = current - seen

    if not seen:
        # Premier lancement : on mémorise l'état sans notifier (sinon vous
        # recevrez une notif pour TOUS les articles existants).
        save_seen(current)
        print("Premier lancement : état initial enregistré, pas de notif envoyée.")
        return

    for link in new_links:
        low = link.lower()
        if any(k in low for k in KEYWORDS):
            notify(
                "Billetterie JEP Élysée ?",
                f"Nouvel article détecté : https://www.elysee.fr{link}",
            )
            print(f"Notification envoyée pour : {link}")

    save_seen(current | seen)


if __name__ == "__main__":
    sys.exit(main())
