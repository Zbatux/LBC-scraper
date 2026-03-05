# LBC Scraper

## Description
Ce projet est un scraper conçu pour extraire des données depuis le site Leboncoin (LBC). Il utilise Python pour envoyer des requêtes HTTP, analyser les réponses, et extraire les informations pertinentes des annonces publiées sur le site.

## Fonctionnalités principales
- Envoi de requêtes HTTP pour récupérer les pages web.
- Analyse du contenu HTML pour extraire les données des annonces.
- Gestion des dépendances via un fichier `requirements.txt`.

## Structure du projet
- `scraper.py` :
  - Contient le code principal pour effectuer le scraping.
  - Utilise des bibliothèques comme `requests` pour les requêtes HTTP et `BeautifulSoup` pour l'analyse HTML.
  - Implémente une logique pour parcourir les pages, extraire les données des annonces (titre, prix, localisation, etc.) et les sauvegarder dans un format structuré (par exemple, JSON ou CSV).
- `requirements.txt` :
  - Liste les bibliothèques Python nécessaires pour exécuter le projet, telles que `requests` et `beautifulsoup4`.

## Prérequis
- Python 3.8 ou une version ultérieure.
- Les bibliothèques listées dans `requirements.txt` doivent être installées. Vous pouvez les installer avec la commande suivante :

```bash
pip install -r requirements.txt
```

## Utilisation
1. Assurez-vous que toutes les dépendances sont installées.
2. Exécutez le fichier `scraper.py` pour démarrer le scraping :

```bash
python scraper.py
```
3. Les données extraites seront sauvegardées dans un fichier de sortie (par exemple, `output.json` ou `output.csv`) dans le répertoire du projet.

## Arguments disponibles

Le script `scraper.py` accepte les arguments suivants :

- `--scrape` : Lance le processus de scraping et sauvegarde les nouvelles annonces dans la base SQLite.
- `--export-csv` : Exporte les données de la base SQLite vers un fichier CSV.

## Détails techniques
- **Requêtes HTTP** :
  - Le module `requests` est utilisé pour envoyer des requêtes GET aux pages du site.
  - Les en-têtes HTTP peuvent être personnalisés pour imiter un navigateur web.
- **Analyse HTML** :
  - Le module `BeautifulSoup` de la bibliothèque `beautifulsoup4` est utilisé pour analyser le contenu HTML des pages récupérées.
  - Les sélecteurs CSS ou XPath sont utilisés pour localiser les éléments pertinents dans le DOM (Document Object Model).
- **Gestion des erreurs** :
  - Le code inclut des mécanismes pour gérer les erreurs réseau (par exemple, les délais d'attente ou les codes d'erreur HTTP).
  - Une logique de réessai peut être implémentée pour les requêtes échouées.
- **Sauvegarde des données** :
  - Les données extraites sont formatées et sauvegardées dans des fichiers JSON ou CSV pour une utilisation ultérieure.

## Avertissement
L'utilisation de ce scraper doit respecter les conditions d'utilisation du site Leboncoin. Assurez-vous d'avoir l'autorisation avant de scraper des données.