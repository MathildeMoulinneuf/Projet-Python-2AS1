from pathlib import Path
import requests
import pandas as pd

DATASET_SLUG = (
    "donnees-geocodees-issues-du-recensement-des-licences-et-clubs-"
    "aupres-des-federations-sportives-agreees-par-le-ministere-charge-des-sports"
)
API_URL = f"https://www.data.gouv.fr/api/1/datasets/{DATASET_SLUG}/"

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def get_licences_resources() -> pd.DataFrame:
    """Récupère la liste des fichiers CSV de licences disponibles sur data.gouv.fr."""
    resp = requests.get(API_URL, timeout=30)
    resp.raise_for_status()
    resources = resp.json()["resources"]

    rows = []
    for res in resources:
        title = res.get("title", "")
        if "lic-data-" in title.lower() and res.get("format", "").lower() == "csv":
            rows.append({
                "title": title,
                "url": res["url"],
                "size_mb": round((res.get("filesize") or 0) / 1e6, 1),
                "last_modified": res.get("last_modified"),
            })
    return pd.DataFrame(rows).sort_values("title", ascending=False)


def download_file(url: str, dest_path: Path) -> Path:
    """Télécharge un gros fichier en streaming s'il n'est pas déjà présent en local."""
    if dest_path.exists():
        print(f"Déjà présent : {dest_path.name}")
        return dest_path

    print(f"Téléchargement de {dest_path.name}...")
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):  # paquets de 1 Mo
                if chunk:
                    f.write(chunk)
    print(f"Terminé : {dest_path.name}")
    return dest_path

import re
from pathlib import Path
import pandas as pd

import re
from pathlib import Path
import pandas as pd

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


def _extraire_departement(serie_commune: pd.Series) -> pd.Series:
    """Extrait le code département (2 ou 3 caractères) depuis le code INSEE commune."""
    codes = serie_commune.astype(str).str.strip().str.zfill(5)
    return codes.str[:3].where(codes.str.startswith(("97", "98")), codes.str[:2])


def _detecter_colonnes(cols: list[str], annee: int) -> dict:
    """Identifie les colonnes utiles selon le schéma du millésime (avant ou après 2019)."""
    cols_lower = {c.lower().strip(): c for c in cols}

    col_commune = next(
        (cols_lower[k] for k in ["code_commune", "code commune"] if k in cols_lower),
        None,
    )
    col_nom_fed = next(
        (cols_lower[k] for k in ["nom_fed", "fédération", "federation", "lib_fed"] if k in cols_lower),
        None,
    )
    col_code_fed = next(
        (cols_lower[k] for k in [f"fed_{annee}", "code", "fed_code", "code_fede"] if k in cols_lower),
        None,
    )
    col_lic = next(
        (cols_lower[k] for k in [f"l_{annee}", "total", "l_tot", "licences"] if k in cols_lower),
        None,
    )

    # Colonnes sexe directes (avant 2019) ou par tranche d'âge (à partir de 2019)
    col_lic_f = next((cols_lower[k] for k in [f"l_f_{annee}", "l_f"] if k in cols_lower), None)
    col_lic_h = next((cols_lower[k] for k in [f"l_h_{annee}", "l_h"] if k in cols_lower), None)
    cols_ages_f = [c for c in cols if c.startswith("F - ")]
    cols_ages_h = [c for c in cols if c.startswith("H - ")]

    if not col_commune or not (col_nom_fed or col_code_fed) or not col_lic:
        raise KeyError(
            f"Colonnes manquantes pour {annee} parmi {cols}. "
            f"Détecté -> commune={col_commune}, nom_fed={col_nom_fed}, code_fed={col_code_fed}, lic={col_lic}"
        )

    return {
        "commune": col_commune,
        "nom_fed": col_nom_fed,
        "code_fed": col_code_fed,
        "lic": col_lic,
        "lic_f": col_lic_f,
        "lic_h": col_lic_h,
        "ages_f": cols_ages_f,
        "ages_h": cols_ages_h,
    }

def construire_base_departementale() -> pd.DataFrame:
    """Agrège tous les CSV bruts par année, département et fédération, puis sauvegarde en Parquet."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    chemin_sortie = PROCESSED_DIR / "licences_dep.parquet"

    fichiers = sorted(RAW_DIR.glob("lic-data-*.csv"))
    if not fichiers:
        raise FileNotFoundError("Aucun fichier lic-data-*.csv trouvé dans data/raw/.")

    tables_annuelles = []

    for fichier in fichiers:
        match_annee = re.search(r"(20\d{2})", fichier.name)
        if not match_annee:
            continue
        annee = int(match_annee.group(1))

        encodage = "utf-8"
        for enc in ("utf-8", "latin1"):
            try:
                entete = pd.read_csv(fichier, sep=";", encoding=enc, nrows=2, quoting=3)
                encodage = enc
                break
            except UnicodeDecodeError:
                continue

        cols_propres = [c.strip('" ') for c in entete.columns]
        m = _detecter_colonnes(cols_propres, annee)

        cols_fed = [c for c in [m["code_fed"], m["nom_fed"]] if c is not None]
        cols_sexe_directes = [c for c in [m["lic_f"], m["lic_h"]] if c is not None]
        cols_num = [m["lic"]] + cols_sexe_directes + m["ages_f"] + m["ages_h"]
        usecols_set = set([m["commune"]] + cols_fed + cols_num)

        morceaux = []
        for chunk in pd.read_csv(
            fichier,
            sep=";",
            encoding=encodage,
            usecols=lambda c: c.strip('" ') in usecols_set,
            dtype=str,
            chunksize=100_000,
            quoting=3,
            on_bad_lines="warn",
        ):
            chunk.columns = [c.strip('" ') for c in chunk.columns]

            for col in chunk.columns:
                chunk[col] = chunk[col].fillna("").str.strip('" ')

            chunk["departement"] = _extraire_departement(chunk[m["commune"]])
            for c in cols_num:
                chunk[c] = pd.to_numeric(chunk[c], errors="coerce").fillna(0)

            chunk["licences"] = chunk[m["lic"]]
            if m["lic_f"]:
                chunk["licences_f"] = chunk[m["lic_f"]]
                chunk["licences_h"] = chunk[m["lic_h"]]
            elif m["ages_f"]:
                chunk["licences_f"] = chunk[m["ages_f"]].sum(axis=1)
                chunk["licences_h"] = chunk[m["ages_h"]].sum(axis=1)
            else:
                chunk["licences_f"] = 0.0
                chunk["licences_h"] = 0.0

            agg = chunk.groupby(["departement"] + cols_fed, as_index=False)[
                ["licences", "licences_f", "licences_h"]
            ].sum()
            morceaux.append(agg)

        df_annee = pd.concat(morceaux, ignore_index=True)
        df_annee = df_annee.groupby(["departement"] + cols_fed, as_index=False)[
            ["licences", "licences_f", "licences_h"]
        ].sum()

        renommage = {}
        if m["code_fed"]:
            renommage[m["code_fed"]] = "code_fed"
        if m["nom_fed"]:
            renommage[m["nom_fed"]] = "nom_fed"

        df_annee = df_annee.rename(columns=renommage)
        df_annee["annee"] = annee
        if "nom_fed" not in df_annee.columns:
            df_annee["nom_fed"] = df_annee["code_fed"]
        if "code_fed" not in df_annee.columns:
            df_annee["code_fed"] = pd.NA

        tables_annuelles.append(
            df_annee[["annee", "departement", "code_fed", "nom_fed", "licences", "licences_f", "licences_h"]]
        )
        print(f"Millésime {annee} agrégé ({len(df_annee)} lignes).")

    df_complet = pd.concat(tables_annuelles, ignore_index=True)
    df_complet.to_parquet(chemin_sortie, index=False)
    print(f"Base sauvegardée dans {chemin_sortie} ({len(df_complet)} lignes au total).")
    return df_complet



def enrichir_avec_2025(df_historique: pd.DataFrame) -> pd.DataFrame:
    """Télécharge le millésime 2025 (data.sports.gouv.fr) et le fusionne à la base 2016-2023."""
    url_2025 = (
        "https://data.sports.gouv.fr/api/explore/v2.1/catalog/datasets/"
        "lics_dep_age_sexe/exports/csv?delimiter=%3B"
    )
    url_noms = (
        "https://data.sports.gouv.fr/api/explore/v2.1/catalog/datasets/"
        "lics_dep/exports/csv?delimiter=%3B"
    )

    df_2025 = pd.read_csv(url_2025, sep=";", dtype={"dep": str, "code_fede_ref": str}, low_memory=False)
    df_noms = pd.read_csv(
        url_noms,
        sep=";",
        usecols=["code_fede_ref", "federations_sportives"],
        dtype=str,
    ).drop_duplicates("code_fede_ref")

    # Standardisation des colonnes
    df_2025["departement"] = df_2025["dep"].str.strip().str.zfill(2)
    df_2025["code_fed"] = df_2025["code_fede_ref"].str.strip().str.replace(r"\.0$", "", regex=True)
    df_2025["lics"] = pd.to_numeric(df_2025["lics"], errors="coerce").fillna(0)
    df_2025["sexe"] = df_2025["sexe"].astype(str).str.upper().str.strip()

    # Totaux globaux par département et fédération
    totaux = (
        df_2025.groupby(["departement", "code_fed"], as_index=False)["lics"]
        .sum()
        .rename(columns={"lics": "licences"})
    )

    # Totaux par sexe (F / H)
    piv_sexe = (
        df_2025.pivot_table(
            index=["departement", "code_fed"],
            columns="sexe",
            values="lics",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )
    piv_sexe["licences_f"] = piv_sexe.get("F", 0.0)
    piv_sexe["licences_h"] = piv_sexe.get("H", 0.0)

    df_2025_clean = totaux.merge(
        piv_sexe[["departement", "code_fed", "licences_f", "licences_h"]],
        on=["departement", "code_fed"],
        how="left",
    )

    # Ajout du libellé de fédération et de l'année 2025
    df_noms["code_fed"] = df_noms["code_fede_ref"].str.strip().str.replace(r"\.0$", "", regex=True)
    df_2025_clean = df_2025_clean.merge(
        df_noms[["code_fed", "federations_sportives"]].rename(columns={"federations_sportives": "nom_fed"}),
        on="code_fed",
        how="left",
    )
    df_2025_clean["nom_fed"] = df_2025_clean["nom_fed"].fillna(df_2025_clean["code_fed"])
    df_2025_clean["annee"] = 2025

    colonnes_cibles = ["annee", "departement", "code_fed", "nom_fed", "licences", "licences_f", "licences_h"]
    df_2025_clean = df_2025_clean[colonnes_cibles]

    # Harmonisation du code_fed dans l'historique avant fusion
    df_hist = df_historique.copy()
    df_hist["code_fed"] = df_hist["code_fed"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    df_hist = df_hist[df_hist["annee"] != 2025]

    df_complet = pd.concat([df_hist[colonnes_cibles], df_2025_clean], ignore_index=True)
    df_complet = df_complet.sort_values(["annee", "departement", "code_fed"]).reset_index(drop=True)

    chemin_sortie = PROCESSED_DIR / "licences_dep_2016_2025.parquet"
    df_complet.to_parquet(chemin_sortie, index=False)
    print(f"Base 2016-2025 sauvegardée dans {chemin_sortie} ({len(df_complet)} lignes).")
    return df_complet


def telecharger_serie_nationale_2002_2025() -> pd.DataFrame:
    """Télécharge et nettoie la série nationale annuelle 2002-2025 (lics_histo)."""
    url_histo = (
        "https://data.sports.gouv.fr/api/explore/v2.1/catalog/datasets/"
        "lics_histo/exports/csv?delimiter=%3B"
    )
    df_histo = pd.read_csv(url_histo, sep=";", dtype={"code_fede_ref": str, "code_fede_2025": str})
    df_histo["annee"] = df_histo["annee"].astype(str).str[:4].astype(int)
    df_histo["code_fed"] = df_histo["code_fede_ref"].str.strip().str.replace(r"\.0$", "", regex=True)
    df_histo["licences"] = pd.to_numeric(df_histo["lics"], errors="coerce").fillna(0)

    chemin_sortie = PROCESSED_DIR / "licences_national_2002_2025.parquet"
    df_histo.to_parquet(chemin_sortie, index=False)
    print(f"Série nationale 2002-2025 sauvegardée dans {chemin_sortie}.")
    return df_histo



    ####
    # AGE
    ####


def _regrouper_tranche_age(libelle_age: str) -> str:
    """Regroupe les tranches d'âge fines de l'INJEP en 4 grandes catégories."""
    s = str(libelle_age).lower()
    if any(k in s for k in ["1 à 4", "5 à 9", "moins de 5", "5-9", "0_4", "5_9"]):
        return "Moins de 10 ans"
    if any(k in s for k in ["10 à 14", "10-14", "10_14"]):
        return "10 à 14 ans"
    if any(k in s for k in ["15 à 19", "15-19", "15_19"]):
        return "15 à 19 ans"
    if "nr" in s or "non renseign" in s:
        return "Non renseigné"
    return "20 ans et plus"


def construire_base_ages_2019_2025(code_fed_cible: str = "123") -> pd.DataFrame:
    """Extrait l'évolution par grande tranche d'âge (2019-2025) pour une fédération donnée."""
    lignes = []

    # 1. Millésimes 2019 à 2023 depuis data/raw/
    for annee in range(2019, 2024):
        fichier = RAW_DIR / f"lic-data-{annee}.csv"
        if not fichier.exists():
            continue

        entete = pd.read_csv(fichier, sep=";", nrows=2, quoting=3)
        cols_propres = [c.strip('" ') for c in entete.columns]
        cols_ages = [c for c in cols_propres if c.startswith(("F - ", "H - ", "NR - "))]
        usecols_set = {"Code", "Fédération"} | set(cols_ages)

        totaux_cols = pd.Series(0.0, index=cols_ages)
        for chunk in pd.read_csv(
            fichier,
            sep=";",
            usecols=lambda c: c.strip('" ') in usecols_set,
            dtype=str,
            chunksize=100_000,
            quoting=3,
            on_bad_lines="warn",
        ):
            chunk.columns = [c.strip('" ') for c in chunk.columns]
            chunk["Code"] = chunk["Code"].fillna("").str.strip('" ').str.replace(r"\.0$", "", regex=True)
            sub = chunk[chunk["Code"] == code_fed_cible]
            if not sub.empty:
                for c in cols_ages:
                    totaux_cols[c] += pd.to_numeric(sub[c].str.strip('" '), errors="coerce").fillna(0).sum()

        for col_age, val in totaux_cols.items():
            lignes.append({
                "annee": annee,
                "code_fed": code_fed_cible,
                "tranche_age": _regrouper_tranche_age(col_age),
                "licences": val,
            })

    # 2. Millésime 2025 depuis data.sports.gouv.fr
    url_2025 = (
        "https://data.sports.gouv.fr/api/explore/v2.1/catalog/datasets/"
        "lics_dep_age_sexe/exports/csv?delimiter=%3B"
    )
    df_2025 = pd.read_csv(url_2025, sep=";", usecols=["code_fede_ref", "trage", "lics"], dtype=str)
    df_2025["code_fed"] = df_2025["code_fede_ref"].str.strip().str.replace(r"\.0$", "", regex=True)
    df_2025 = df_2025[df_2025["code_fed"] == code_fed_cible].copy()
    df_2025["licences"] = pd.to_numeric(df_2025["lics"], errors="coerce").fillna(0)
    df_2025["tranche_age"] = df_2025["trage"].apply(_regrouper_tranche_age)
    df_2025["annee"] = 2025

    lignes.append(df_2025[["annee", "code_fed", "tranche_age", "licences"]])

    df_res = pd.concat([pd.DataFrame(l) if isinstance(l, list) else l for l in [lignes[:-1], lignes[-1]]], ignore_index=True)
    df_res = df_res[df_res["tranche_age"] != "Non renseigné"]
    return df_res.groupby(["annee", "code_fed", "tranche_age"], as_index=False)["licences"].sum()


    ###LONDRES  
def charger_historique_national(forcer: bool = False) -> pd.DataFrame:
    """Télécharge et nettoie la série historique nationale des licences (2002-2025), hors lignes TOT."""
    chemin_parquet = PROCESSED_DIR / "licences_histo_national.parquet"
    if chemin_parquet.exists() and not forcer:
        df_cache = pd.read_parquet(chemin_parquet)
        if not df_cache.empty and "TOT" not in df_cache["code_fed"].values:
            return df_cache

    url_histo = (
        "https://data.sports.gouv.fr/api/explore/v2.1/catalog/datasets/"
        "lics_histo/exports/csv?delimiter=%3B"
    )
    df = pd.read_csv(url_histo, sep=";", dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]

    annees_num = pd.to_numeric(
        df["annee"].astype(str).str.extract(r"^(\d{4})")[0], errors="coerce"
    )
    lics_num = pd.to_numeric(
        df["lics"].astype(str).str.replace(r"\s+", "", regex=True).str.replace(",", ".", regex=False),
        errors="coerce",
    )

    df_clean = pd.DataFrame({
        "code_fed": df["code_fede_ref"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True),
        "nom_fed": df["federation"].astype(str).str.strip(),
        "type_fed": df["fede_gp"].astype(str).str.strip() if "fede_gp" in df.columns else "",
        "annee": annees_num,
        "licences": lics_num,
    }).dropna(subset=["annee", "licences"])

    # Exclusion des lignes agrégées (code_fed == "TOT" ou mention "champ constant")
    masque_agr = (
        df_clean["code_fed"].str.upper().isin(["TOT", "TOTAL", "NAN", "NONE", ""])
        | df_clean["nom_fed"].str.contains("champ constant|toutes fédés", case=False, na=False)
    )
    df_clean = df_clean[~masque_agr].copy()

    df_clean["annee"] = df_clean["annee"].astype(int)
    df_clean = df_clean.groupby(["code_fed", "annee"], as_index=False).agg(
        nom_fed=("nom_fed", "last"),
        type_fed=("type_fed", "last"),
        licences=("licences", "sum"),
    )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df_clean.to_parquet(chemin_parquet, index=False)
    return df_clean