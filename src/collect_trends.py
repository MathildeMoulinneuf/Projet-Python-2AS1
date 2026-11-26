from pathlib import Path
import pandas as pd
import requests

PROCESSED_DIR = Path("data/processed")


def recuperer_vues_wikipedia(
    pages: dict[str, str],
    debut: str = "20230101",
    fin: str = "20250301",
    forcer: bool = False,
) -> pd.DataFrame:
    """Récupère les vues mensuelles Wikipédia (fr.wikipedia.org) pour une liste de personnalités."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    chemin_parquet = PROCESSED_DIR / "vues_wikipedia_jo.parquet"

    if chemin_parquet.exists() and not forcer:
        return pd.read_parquet(chemin_parquet)

    headers = {"User-Agent": "ProjetDataScienceENSAE"}
    lignes = []

    for label, slug_wiki in pages.items():
        url = (
            f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
            f"fr.wikipedia/all-access/user/{slug_wiki}/monthly/{debut}/{fin}"
        )
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()

        for item in resp.json().get("items", []):
            ts = item["timestamp"]  # Format YYYYMMDD00
            lignes.append({
                "personnalite": label,
                "date": pd.to_datetime(ts[:6], format="%Y%m"),
                "vues": item["views"],
            })

    df_vues = pd.DataFrame(lignes).sort_values(["personnalite", "date"]).reset_index(drop=True)
    df_vues.to_parquet(chemin_parquet, index=False)
    return df_vues



####D AILY


from pathlib import Path
import pandas as pd
import requests

PROCESSED_DIR = Path("data/processed")


def recuperer_vues_wikipedia(
    pages: dict[str, str],
    debut: str = "20230101",
    fin: str = "20250301",
    granularite: str = "monthly",
    forcer: bool = False,
) -> pd.DataFrame:
    """Récupère les vues Wikipédia (monthly ou daily) pour une liste de personnalités."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    chemin_parquet = PROCESSED_DIR / f"vues_wikipedia_{granularite}.parquet"

    if chemin_parquet.exists() and not forcer:
        return pd.read_parquet(chemin_parquet)

    headers = {"User-Agent": "ProjetDataScienceENSAE/1.0 (contact@ensae.fr)"}
    lignes = []
    fmt_date = "%Y%m" if granularite == "monthly" else "%Y%m%d"
    longueur_ts = 6 if granularite == "monthly" else 8

    for label, slug_wiki in pages.items():
        url = (
            f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
            f"fr.wikipedia/all-access/user/{slug_wiki}/{granularite}/{debut}/{fin}"
        )
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            print(f"Page introuvable ou indisponible : {slug_wiki}")
            continue

        for item in resp.json().get("items", []):
            ts = item["timestamp"]
            lignes.append({
                "personnalite": label,
                "date": pd.to_datetime(ts[:longueur_ts], format=fmt_date),
                "vues": item["views"],
            })

    df_vues = pd.DataFrame(lignes).sort_values(["personnalite", "date"]).reset_index(drop=True)
    df_vues.to_parquet(chemin_parquet, index=False)
    return df_vues