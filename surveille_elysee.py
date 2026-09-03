#!/usr/bin/env python3
"""
Surveille la page d'actualités de l'Élysée ET la page spécifique des JEP 2026
pour détecter l'ouverture de la billetterie, et envoie une notification
(ntfy + email) dès qu'un signal est détecté.
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

LISTING_URL = "https://www.elysee.fr/toutes-les-actualites"

# La page spécifique de l'annonce JEP 2026, publiée le 3 septembre 2026
JEP_PAGE_URL = "https://www.elysee.fr/emmanuel-macron/2026/09/03/les-journees-europeennes-du-patrimoine-2026-au-palais-de-lelysee"

# Mot qui indique que la billetterie N'EST PAS ENCORE ouverte
# ("prochainement" n'a pas d'accent, ça évite les soucis d'encodage de caractères)
PLACEHOLDER_PHRASE = "prochainement"

KEYWORDS = ["patrimoine", "billetterie", "inscri", "creneau", "créneau"]

NTFY_TOPIC = os.environ.get("NTFY_TOPIC")
EMAIL_FROM = os.environ.get("EMAIL_FROM")
EMAIL_APP_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD")
EMAIL_TO = os.environ.get("EMAIL_TO")

STATE_FILE = Path("seen_links.json")
JEP_STATE_FILE = Path("jep_page_state.json")


# --- Surveillance n°1 : nouveaux articles sur la page listing (filet de sécurité) ---

def get_articles():
    resp = requests.get(LISTING_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
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


def check_new_articles():
    seen = load_seen()
    current = get_articles()
    new_links = current - seen

    if not seen:
        save_seen(current)
        print("Premier lancement (listing) : état initial enregistré.")
        return

    for link in new_links:
        low = link.lower()
        if any(k in low for k in KEYWORDS):
            notify(
                "Billetterie JEP Élysée ? (nouvel article)",
                f"Nouvel article détecté : https://www.elysee.fr{link}",
            )
            print(f"[listing] Notification envoyée pour : {link}")

    save_seen(current | seen)


# --- Surveillance n°2 : la page JEP précise, détection de la disparition du placeholder ---

def load_jep_state():
    if JEP_STATE_FILE.exists():
        return json.loads(JEP_STATE_FILE.read_text())
    return None  # None = jamais vérifié encore


def save_jep_state(placeholder_present):
    JEP_STATE_FILE.write_text(json.dumps({"placeholder_present": placeholder_present}))


def check_jep_page():
    try:
        resp = requests.get(JEP_PAGE_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        resp.raise_for_status()
        resp.encoding = "utf-8"  # force l'encodage pour éviter les soucis d'accents
    except Exception as e:
        print(f"Erreur lors de la vérification de la page JEP : {e}")
        return

    page_text = resp.text.lower()
    placeholder_present = PLACEHOLDER_PHRASE in page_text

    previous_state = load_jep_state()

    if previous_state is None:
        # Premier passage sur cette page : on enregistre l'état sans notifier,
        # SAUF si le placeholder est déjà absent (billetterie déjà ouverte !).
        save_jep_state(placeholder_present)
        if not placeholder_present:
            notify(
                "🚨 Billetterie JEP Élysée OUVERTE (ou probablement) !",
                f"Le texte d'attente a disparu de la page dès la 1ère vérification : {JEP_PAGE_URL}",
            )
            print("[page JEP] ALERTE dès le premier passage : placeholder déjà absent.")
        else:
            print("[page JEP] Premier passage : placeholder présent, pas de notif.")
        return

    was_present = previous_state.get("placeholder_present", True)

    if was_present and not placeholder_present:
        # Le placeholder vient de disparaître : signal fort d'ouverture !
        notify(
            "🚨 Billetterie JEP Élysée OUVERTE !",
            f"Le texte d'attente a disparu de la page : {JEP_PAGE_URL}",
        )
        print("[page JEP] ALERTE : le placeholder a disparu, billetterie probablement ouverte.")

    save_jep_state(placeholder_present)


# --- Notifications ---

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
    check_new_articles()
    check_jep_page()


if __name__ == "__main__":
    sys.exit(main())
