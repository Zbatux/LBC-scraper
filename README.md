# LBC Scraper

Scraper de terrains constructibles sur Leboncoin (rayon 100 km autour de Toulouse).
Utilise **Playwright** pour contourner la protection DataDome, calcule le temps de trajet
via **OSRM** (gratuit, sans clé API), stocke tout dans **SQLite**, enrichit les annonces
par analyse IA locale avec **Ollama** et propose une **interface web** (Flask) pour éditer,
filtrer et annoter les annonces.

## Prérequis

```bash
pip install -r requirements.txt
python -m playwright install chromium
ollama pull gemma3:12b   # uniquement pour --analyze
```

Python 3.10+ requis (annotations `X | Y`).

## Usage

```bash
# 1. Scraper les annonces et calculer les trajets
python main.py --scrape

# 2. Récupérer les descriptions complètes des annonces
python main.py --get-description

# 3. Analyser les descriptions avec le LLM local
python main.py --analyze

# 4. Exporter en CSV
python main.py --export-csv

# 5. Lancer l'interface web d'édition (http://localhost:5000)
python main.py --web
```

Les étapes 1 à 4 sont indépendantes et cumulatives. L'ordre recommandé est 1 → 2 → 3 → 4.
L'étape 5 peut être lancée à tout moment pour consulter et éditer la base.

## Arguments

| Argument            | Description                                                                 |
|---------------------|-----------------------------------------------------------------------------|
| `--scrape`          | Scrape Leboncoin et enregistre les nouvelles annonces dans `lbc_data.db`   |
| `--get-description` | Visite chaque annonce sans description et récupère son texte complet        |
| `--analyze`         | Analyse les descriptions via Ollama et remplit les champs IA (viabilisé…)  |
| `--export-csv`      | Exporte toutes les données de la base vers un fichier CSV horodaté         |
| `--web`             | Lance l'interface web d'édition sur `http://localhost:5000`                |

## Structure du projet

```
main.py            Point d'entrée CLI
config.py          Constantes (URL de recherche, coordonnées Toulouse…)
parsers.py         Extraction des champs depuis les objets JSON Leboncoin
routing.py         Calcul du temps de trajet Toulouse via OSRM
browser.py         Pilotage Playwright (scraping, anti-bot)
database.py        Persistance SQLite + déduplication
descriptions.py    Récupération des descriptions complètes
analyzer.py        Analyse IA locale (Ollama / gemma3:12b)
exporter.py        Export CSV
web.py             Serveur Flask — interface web d'édition
templates/
  index.html       Interface HTML/JS d'édition des annonces
lbc_data.db        Base SQLite générée à l'exécution
```

Pour une description détaillée de l'architecture, des dépendances entre modules et du
schéma de base de données, voir [ARCHITECTURE.md](ARCHITECTURE.md).

## Avertissement

L'utilisation de ce scraper doit respecter les conditions d'utilisation du site Leboncoin.