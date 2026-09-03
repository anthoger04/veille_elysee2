#!/usr/bin/env python3
"""
Surveille la page d'actualités de l'Élysée et envoie une notification
(ntfy + email) dès qu'un nouvel article mentionnant les Journées du
Patrimoine apparaît.
"""
import json
import os
import re
import smtplib
import sys
from email.mime.text import MIMEText
from pathlib import Path
import requests
from bs4 import BeautifulSoup

URL = "https://www.elysee.fr/toutes-les-actualites"

# Mots-clés qui indiquent que l'article concerne les JEP / la billetterie
# (mot "gironde" ajouté TEMPORAIREMENT pour tester la notification)
KEYWORDS = ["patrimoine", "billetterie", "inscri", "creneau", "créneau", "gironde"]

NTFY_TOPIC = os.environ.get("NTFY_TOPIC")
EMAIL_FROM = os.environ.get("EMAIL_FROM")
EMAIL_APP_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD")
EMAIL_TO = os.environ.get("EMAIL_TO")

STATE_FILE = Path("seen_links.json")


def get_articles():
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


def notify_ntfy(title, message):
    if not NTFY_TOPIC:
        return
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode("utf-8"),
            headers={"Title": title.encode("utf-8"), "Priority": "urgent"},
            timeout=10,
        )
    except Exception as e:
        print(f"Erreur envoi ntfy : {e}")


def notify_email(title, message):
    if not (EMAIL_FROM and EMAIL_APP_PASSWORD and EMAIL_TO):
        return
    recipients = [addr.strip() for addr in EMAIL_TO.split(",") if addr.strip()]
    try:
        msg = MIMEText(message)
        msg["Subject"] = title
        msg["From"] = EMAIL_FROM
        msg["To"] = ", ".join(recipients)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_FROM, EMAIL_APP_PASSWORD)
            server.sendmail(EMAIL_FROM, recipients, msg.as_string())
    except Exception as e:
        print(f"Erreur envoi email : {e}")


def notify(title, message):
    notify_ntfy(title, message)
    notify_email(title, message)


def main():
    seen = load_seen()
    current = get_articles()
    new_links = current - seen

    if not seen:
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
