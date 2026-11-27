from pathlib import Path
import pandas as pd
import requests

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

DATASETS_JO = {
    "athletes_paris_2024": "les-athletes-des-jeux-olympiques-de-paris-2024",
}


def telecharger_ressource_datagouv(slug, nom_fichier_local):
    """Télécharge le fichier CSV ou Excel principal d'un jeu data.gouv.fr."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    resp = requests.get(f"https://www.data.gouv.fr/api/1/datasets/{slug}/", timeout=30)
    resp.raise_for_status()
    ressources = resp.json().get("resources", [])

    cible = None
    for fmt in ("csv", "xlsx", "xls"):
        for r in ressources:
            if str(r.get("format", "")).lower() == fmt:
                cible = r
                break
        if cible:
            break

    if cible is None:
        raise ValueError(f"Aucune ressource CSV/Excel trouvée pour {slug}")

    ext = str(cible["format"]).lower()
    chemin = RAW_DIR / f"{nom_fichier_local}.{ext}"
    contenu = requests.get(cible["url"], timeout=60)
    contenu.raise_for_status()
    chemin.write_bytes(contenu.content)
    return chemin


def _lire_table_brute(chemin):
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
    raise ValueError(f"Impossible de lire {chemin}")


def charger_donnees_jo(forcer_telechargement=False):
    """Charge et met en cache au format Parquet les données olympiques."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    resultats = {}

    for cle, slug in DATASETS_JO.items():
        parquet = PROCESSED_DIR / f"{cle}.parquet"
        if parquet.exists() and not forcer_telechargement:
            resultats[cle] = pd.read_parquet(parquet)
            continue

        fichiers = list(RAW_DIR.glob(f"{cle}.*"))
        if fichiers and not forcer_telechargement:
            chemin_brut = fichiers[0]
        else:
            chemin_brut = telecharger_ressource_datagouv(slug, cle)

        df = _lire_table_brute(chemin_brut)
        df.columns = [c.strip() for c in df.columns]
        df.to_parquet(parquet, index=False)
        resultats[cle] = df

    return resultats