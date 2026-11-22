# Impact des Jeux Olympiques de Paris 2024 sur la pratique sportive en France : le cas des frères Lebrun

Projet de data science visant à mesurer l'effet des Jeux Olympiques de Paris 2024 et de la médiatisation de Félix et Alexis Lebrun sur l'évolution des licences sportives en France, en particulier au sein de la Fédération Française de Tennis de Table (FFTT).

## Architecture du dépôt

```text
Projet-Python-2AS1/
├── data/
│   ├── raw/                 # Fichiers bruts téléchargés automatiquement (ignorés par Git)
│   └── processed/           # Tables nettoyées au format Parquet (ignorées par Git)
├── notebooks/
│   ├── explo_licences.ipynb # Exploration des données INJEP (national, départemental, âge, genre)
│   ├── explo_trends.ipynb   # Exploration de l'attention médiatique
│   └── explo_viz.ipynb      # Prototypage des visualisations
├── src/
│   ├── collect_licences.py  # Téléchargement et nettoyage des bases INJEP (2002-2025)
│   ├── collect_jo.py        # Récupération des athlètes et médailles JO (Paris 2024, Londres 2012)
│   ├── collect_trends.py    # Collecte des indicateurs d'audience médiatique
│   ├── processing.py        # Calculs d'indices, croisement médailles/licences et agrégations
│   └── viz.py               # Fonctions de visualisation interactive (Plotly)
├── rapport.ipynb            # Notebook principal présentant la synthèse et les résultats
├── requirements.txt         # Dépendances Python du projet
└── README.md

