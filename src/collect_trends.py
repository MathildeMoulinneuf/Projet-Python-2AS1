from pathlib import Path
import pandas as pd
import requests

PROCESSED_DIR = Path("data/processed")
WIKI_API = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/fr.wikipedia/all-access/user"


def recuperer_vues_wikipedia(
    pages,
    debut="20230101",
    fin="20250301",
    granularite="monthly",
    forcer=False,
):
    """Récupère les vues Wikipédia (monthly ou daily) pour une liste de personnalités."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    chemin_parquet = PROCESSED_DIR / f"vues_wikipedia_{granularite}.parquet"

    if chemin_parquet.exists() and not forcer:
        return pd.read_parquet(chemin_parquet)

    headers = {"User-Agent": "ProjetDataScienceENSAE/1.0 (contact@ensae.fr)"}
    fmt_date = "%Y%m" if granularite == "monthly" else "%Y%m%d"
    longueur_ts = 6 if granularite == "monthly" else 8

    lignes = []
    for label, slug_wiki in pages.items():
        url = f"{WIKI_API}/{slug_wiki}/{granularite}/{debut}/{fin}"
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            continue

        for item in resp.json().get("items", []):
            lignes.append({
                "personnalite": label,
                "date": pd.to_datetime(item["timestamp"][:longueur_ts], format=fmt_date),
                "vues": item["views"],
            })

    df_vues = pd.DataFrame(lignes).sort_values(["personnalite", "date"]).reset_index(drop=True)
    df_vues.to_parquet(chemin_parquet, index=False)
    return df_vues