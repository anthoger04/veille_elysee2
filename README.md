# Alerte d'ouverture de billetterie – Journées européennes du patrimoine

Un bot qui vérifie automatiquement le site de l'Élysée et envoie une notification (push sur téléphone et email) dès que la billetterie des Journées européennes du patrimoine (JEP) ouvre.

## Le problème

Les places pour visiter l'Élysée pendant les JEP partent en quelques minutes, et l'heure d'ouverture de la billetterie n'est pas annoncée précisément. Sans outil, il faut actualiser la page à la main pendant des jours.

## Comment ça marche

Le script combine deux vérifications complémentaires à chaque exécution.

**1. Page de l'annonce JEP (signal principal).** Tant que la billetterie n'est pas ouverte, la page de l'annonce contient un texte d'attente (« prochainement »). Le script vérifie si ce texte est présent et compare avec l'état du passage précédent. S'il vient de disparaître, c'est le signe que la billetterie a ouvert, et une alerte urgente est envoyée. Si le texte est déjà absent dès la première vérification, l'alerte part immédiatement.

**2. Liste des actualités (filet de sécurité).** Le script récupère tous les liens d'articles de la page « Toutes les actualités » et les compare à ceux déjà vus. Si un nouvel article contient un mot-clé dans son adresse (`patrimoine`, `billetterie`, `inscri`, `creneau`), une alerte est envoyée. Au premier lancement, les articles existants sont simplement enregistrés, sans notification.

**Mémoire entre les exécutions.** L'état est conservé dans deux fichiers, enregistrés dans le dépôt par un commit automatique :
- `seen_links.json` : les articles déjà vus ;
- `jep_page_state.json` : la présence ou non du texte d'attente lors du dernier passage.

Cela évite d'envoyer deux fois la même alerte.

**Notifications.** Chaque alerte est envoyée par deux canaux :
- une notification push via [ntfy](https://ntfy.sh), en priorité maximale pour qu'elle sonne même en mode silencieux ;
- un email via Gmail, avec possibilité de mettre plusieurs destinataires séparés par des virgules.

## Fréquence de vérification

| Période | Fréquence |
|---|---|
| Toute l'année | Toutes les 5 minutes (décalées de 3 minutes pour éviter les heures pleines de GitHub) |
| Du 1er au 15 septembre, de 17h55 à 18h10 (heure de Paris) | Toutes les minutes |

Les horaires `cron` sont en UTC : 15h55 UTC correspond à 17h55 à Paris en heure d'été.

Une exécution manuelle est aussi possible via le bouton « Run workflow » de l'onglet Actions.

## Installation

1. Forker ou cloner ce dépôt.
2. Installer l'application [ntfy](https://ntfy.sh) sur votre téléphone et s'abonner à un nom de sujet difficile à deviner. Les sujets ntfy sont publics : quiconque connaît le nom peut lire les notifications.
3. Créer un mot de passe d'application Gmail pour l'adresse d'envoi : Compte Google → Sécurité → Mots de passe des applications.
4. Dans le dépôt, aller dans Settings → Secrets and variables → Actions et ajouter les secrets suivants
