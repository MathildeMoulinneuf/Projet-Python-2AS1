from pathlib import Path
import requests
import pandas as pd

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

DATASETS_JO = {
    "athletes_paris_2024": "les-athletes-des-jeux-olympiques-de-paris-2024",
    "medailles_2012_2014": "liste-des-medailles-obtenues-par-des-sportifs-francais-aux-jeux-olympiques-et-paralympiques-de-2012-et-de-2014",
}


def telecharger_ressource_datagouv(slug: str, nom_fichier_local: str) -> Path:
    """Récupère l'URL de la ressource principale (CSV ou Excel) via l'API data.gouv.fr et la sauvegarde."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    url_api = f"https://www.data.gouv.fr/api/1/datasets/{slug}/"

    resp = requests.get(url_api, timeout=30)
    resp.raise_for_status()
    ressources = resp.json().get("resources", [])

    # Priorité aux fichiers CSV, sinon XLSX/XLS
    ressource_cible = next(
        (r for r in ressources if str(r.get("format", "")).lower() == "csv"),
        next(
            (r for r in ressources if str(r.get("format", "")).lower() in ("xlsx", "xls")),
            None,
        ),
    )

    if ressource_cible is None:
        formats_dispos = [r.get("format") for r in ressources]
        raise ValueError(f"Aucune ressource CSV/Excel trouvée pour {slug} (formats dispos : {formats_dispos}).")

    ext = str(ressource_cible["format"]).lower()
    chemin_local = RAW_DIR / f"{nom_fichier_local}.{ext}"

    contenu = requests.get(ressource_cible["url"], timeout=60)
    contenu.raise_for_status()
    chemin_local.write_bytes(contenu.content)

    print(f"Fichier téléchargé : {chemin_local} (source : {ressource_cible.get('title')})")
    return chemin_local


def _lire_table_brute(chemin: Path) -> pd.DataFrame:
    """Lit un fichier CSV (en détectant séparateur et encodage) ou Excel."""
    if chemin.suffix in (".xlsx", ".xls"):
        return pd.read_excel(chemin)

    for enc in ("utf-8", "latin1"):
        for sep in (";", ","):
            try:
                df = pd.read_csv(chemin, sep=sep, encoding=enc, low_memory=False)
                if df.shape[1] > 1:
                    return df
            except UnicodeDecodeError:
                continue
    raise ValueError(f"Impossible de parser le fichier {chemin}.")


def charger_donnees_jo(forcer_telechargement: bool = False) -> dict[str, pd.DataFrame]:
    """Télécharge, nettoie et sauvegarde les deux bases olympiques au format Parquet."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    resultats = {}

    for cle, slug in DATASETS_JO.items():
        chemin_parquet = PROCESSED_DIR / f"{cle}.parquet"

        if chemin_parquet.exists() and not forcer_telechargement:
            df = pd.read_parquet(chemin_parquet)
        else:
            fichiers_existants = list(RAW_DIR.glob(f"{cle}.*"))
            if fichiers_existants and not forcer_telechargement:
                chemin_brut = fichiers_existants[0]
            else:
                chemin_brut = telecharger_ressource_datagouv(slug, cle)

            df = _lire_table_brute(chemin_brut)
            # Standardisation légère des noms de colonnes
            df.columns = [c.strip() for c in df.columns]
            df.to_parquet(chemin_parquet, index=False)

        resultats[cle] = df
        print(f"\n--- {cle} ({len(df)} lignes) ---")
        print("Colonnes :", df.columns.tolist())

    return resultats