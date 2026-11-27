from pathlib import Path
import re
import pandas as pd
import requests

DATASET_SLUG = (
    "donnees-geocodees-issues-du-recensement-des-licences-et-clubs-"
    "aupres-des-federations-sportives-agreees-par-le-ministere-charge-des-sports"
)
API_URL = f"https://www.data.gouv.fr/api/1/datasets/{DATASET_SLUG}/"
SPORTS_API = "https://data.sports.gouv.fr/api/explore/v2.1/catalog/datasets"

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


def _clean_code(serie):
    return serie.astype(str).str.strip('" ').str.replace(r"\.0$", "", regex=True)


def _extraire_departement(serie_commune):
    codes = serie_commune.astype(str).str.strip().str.zfill(5)
    return codes.str[:3].where(codes.str.startswith(("97", "98")), codes.str[:2])


def _detecter_csv(fichier):
    for enc in ("utf-8", "latin1"):
        for sep in (";", ","):
            try:
                test = pd.read_csv(fichier, sep=sep, encoding=enc, nrows=2, quoting=3)
                if test.shape[1] > 1:
                    return enc, sep, [c.strip('" ') for c in test.columns]
            except UnicodeDecodeError:
                continue
    raise ValueError(f"Impossible de lire {fichier.name}")


def _detecter_colonnes(cols, annee):
    cols_lower = {c.lower().strip(): c for c in cols}

    def trouver(noms):
        for nom in noms:
            if nom in cols_lower:
                return cols_lower[nom]
        return None

    col_commune = trouver(["code_commune", "code commune", "newcog2", "newcog", "codgeo", "cog", "code_insee"])
    col_nom_fed = trouver(["nom_fed", "fédération", "federation", "lib_fed"])
    col_code_fed = trouver([f"fed_{annee}", "code", "fed_code", "code_fede"])
    if col_code_fed is None:
        for k, orig in cols_lower.items():
            if re.fullmatch(r"fed_\d{4}", k):
                col_code_fed = orig
                break

    col_lic = trouver([f"l_{annee}", "total", "l_tot", "licences"])
    col_lic_f = trouver([f"l_f_{annee}", f"lic_f_{annee}", "l_f"])
    col_lic_h = trouver([f"l_h_{annee}", f"lic_h_{annee}", "l_h"])

    if not col_commune or not (col_nom_fed or col_code_fed) or not col_lic:
        raise KeyError(f"Colonnes manquantes pour {annee} : {cols}")

    return {
        "commune": col_commune,
        "nom_fed": col_nom_fed,
        "code_fed": col_code_fed,
        "lic": col_lic,
        "lic_f": col_lic_f,
        "lic_h": col_lic_h,
        "ages_f": [c for c in cols if c.startswith("F - ")],
        "ages_h": [c for c in cols if c.startswith("H - ")],
    }


def get_licences_resources():
    """Liste les fichiers CSV de licences disponibles sur data.gouv.fr."""
    resp = requests.get(API_URL, timeout=30)
    resp.raise_for_status()

    rows = []
    for res in resp.json()["resources"]:
        title = res.get("title", "")
        if ("lic-data-" in title.lower() or "licences_" in title.lower()) and res.get("format", "").lower() == "csv":
            rows.append({
                "title": title,
                "url": res["url"],
                "size_mb": round((res.get("filesize") or 0) / 1e6, 1),
                "last_modified": res.get("last_modified"),
            })
    return pd.DataFrame(rows).sort_values("title", ascending=False)


def download_file(url, dest_path):
    """Télécharge un fichier en streaming s'il n'est pas déjà présent."""
    if dest_path.exists():
        return dest_path

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    return dest_path


def construire_base_departementale():
    """Agrège les CSV bruts par année, département et fédération en Parquet."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    chemin_sortie = PROCESSED_DIR / "licences_dep.parquet"

    fichiers = sorted(RAW_DIR.glob("lic-data-*.csv"))
    if not fichiers:
        for _, row in get_licences_resources().iterrows():
            match = re.search(r"(20\d{2})", str(row["title"]))
            nom = f"lic-data-{match.group(1)}.csv" if match else str(row["title"])
            if not nom.endswith(".csv"):
                nom += ".csv"
            download_file(row["url"], RAW_DIR / nom)
        fichiers = sorted(RAW_DIR.glob("lic-data-*.csv"))

    tables = []
    for fichier in fichiers:
        match = re.search(r"(20\d{2})", fichier.name)
        if not match:
            continue
        annee = int(match.group(1))

        enc, sep, cols_propres = _detecter_csv(fichier)
        m = _detecter_colonnes(cols_propres, annee)

        cols_fed = [c for c in (m["code_fed"], m["nom_fed"]) if c]
        cols_sexe = [c for c in (m["lic_f"], m["lic_h"]) if c]
        cols_num = [m["lic"]] + cols_sexe + m["ages_f"] + m["ages_h"]
        usecols = {m["commune"]} | set(cols_fed) | set(cols_num)

        morceaux = []
        for chunk in pd.read_csv(
            fichier,
            sep=sep,
            encoding=enc,
            usecols=lambda c: c.strip('" ') in usecols,
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

            morceaux.append(
                chunk.groupby(["departement"] + cols_fed, as_index=False)[
                    ["licences", "licences_f", "licences_h"]
                ].sum()
            )

        df_annee = (
            pd.concat(morceaux, ignore_index=True)
            .groupby(["departement"] + cols_fed, as_index=False)[
                ["licences", "licences_f", "licences_h"]
            ]
            .sum()
        )

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

        tables.append(
            df_annee[["annee", "departement", "code_fed", "nom_fed", "licences", "licences_f", "licences_h"]]
        )

    df_complet = pd.concat(tables, ignore_index=True)
    df_complet.to_parquet(chemin_sortie, index=False)
    return df_complet


def enrichir_avec_2025(df_historique):
    """Télécharge le millésime 2025 et le fusionne à la base 2016-2023."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df_2025 = pd.read_csv(
        f"{SPORTS_API}/lics_dep_age_sexe/exports/csv?delimiter=%3B",
        sep=";",
        dtype={"dep": str, "code_fede_ref": str},
        low_memory=False,
    )
    df_noms = pd.read_csv(
        f"{SPORTS_API}/lics_dep/exports/csv?delimiter=%3B",
        sep=";",
        usecols=["code_fede_ref", "federations_sportives"],
        dtype=str,
    ).drop_duplicates("code_fede_ref")

    df_2025["departement"] = df_2025["dep"].str.strip().str.zfill(2)
    df_2025["code_fed"] = _clean_code(df_2025["code_fede_ref"])
    df_2025["lics"] = pd.to_numeric(df_2025["lics"], errors="coerce").fillna(0)
    df_2025["sexe"] = df_2025["sexe"].astype(str).str.upper().str.strip()

    totaux = (
        df_2025.groupby(["departement", "code_fed"], as_index=False)["lics"]
        .sum()
        .rename(columns={"lics": "licences"})
    )
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

    df_noms["code_fed"] = _clean_code(df_noms["code_fede_ref"])
    df_2025_clean = (
        totaux.merge(
            piv_sexe[["departement", "code_fed", "licences_f", "licences_h"]],
            on=["departement", "code_fed"],
            how="left",
        )
        .merge(
            df_noms[["code_fed", "federations_sportives"]].rename(columns={"federations_sportives": "nom_fed"}),
            on="code_fed",
            how="left",
        )
    )
    df_2025_clean["nom_fed"] = df_2025_clean["nom_fed"].fillna(df_2025_clean["code_fed"])
    df_2025_clean["annee"] = 2025

    cols = ["annee", "departement", "code_fed", "nom_fed", "licences", "licences_f", "licences_h"]
    df_hist = df_historique[df_historique["annee"] != 2025].copy()
    df_hist["code_fed"] = _clean_code(df_hist["code_fed"])

    df_complet = (
        pd.concat([df_hist[cols], df_2025_clean[cols]], ignore_index=True)
        .sort_values(["annee", "departement", "code_fed"])
        .reset_index(drop=True)
    )
    df_complet.to_parquet(PROCESSED_DIR / "licences_dep_2016_2025.parquet", index=False)
    return df_complet


def _regrouper_tranche_age(libelle_age):
    s = str(libelle_age).lower()
    if any(k in s for k in ("1 à 4", "5 à 9", "moins de 5", "5-9", "0_4", "5_9")):
        return "Moins de 10 ans"
    if any(k in s for k in ("10 à 14", "10-14", "10_14")):
        return "10 à 14 ans"
    if any(k in s for k in ("15 à 19", "15-19", "15_19")):
        return "15 à 19 ans"
    if "nr" in s or "non renseign" in s:
        return "Non renseigné"
    return "20 ans et plus"


def construire_base_ages_2019_2025(code_fed_cible="123"):
    """Extrait l'évolution par grande tranche d'âge (2019-2025) pour une fédération."""
    lignes = []
    for annee in range(2019, 2024):
        fichier = RAW_DIR / f"lic-data-{annee}.csv"
        if not fichier.exists():
            continue

        enc, sep, cols_propres = _detecter_csv(fichier)
        cols_ages = [c for c in cols_propres if c.startswith(("F - ", "H - ", "NR - "))]
        usecols = {"Code", "Fédération"} | set(cols_ages)

        totaux = pd.Series(0.0, index=cols_ages)
        for chunk in pd.read_csv(
            fichier,
            sep=sep,
            encoding=enc,
            usecols=lambda c: c.strip('" ') in usecols,
            dtype=str,
            chunksize=100_000,
            quoting=3,
            on_bad_lines="warn",
        ):
            chunk.columns = [c.strip('" ') for c in chunk.columns]
            sub = chunk[_clean_code(chunk["Code"].fillna("")) == code_fed_cible]
            if not sub.empty:
                for c in cols_ages:
                    totaux[c] += pd.to_numeric(sub[c].str.strip('" '), errors="coerce").fillna(0).sum()

        for col_age, val in totaux.items():
            lignes.append({
                "annee": annee,
                "code_fed": code_fed_cible,
                "tranche_age": _regrouper_tranche_age(col_age),
                "licences": val,
            })

    df_2025 = pd.read_csv(
        f"{SPORTS_API}/lics_dep_age_sexe/exports/csv?delimiter=%3B",
        sep=";",
        usecols=["code_fede_ref", "trage", "lics"],
        dtype=str,
    )
    df_2025["code_fed"] = _clean_code(df_2025["code_fede_ref"])
    df_2025 = df_2025[df_2025["code_fed"] == code_fed_cible].copy()
    df_2025["licences"] = pd.to_numeric(df_2025["lics"], errors="coerce").fillna(0)
    df_2025["tranche_age"] = df_2025["trage"].apply(_regrouper_tranche_age)
    df_2025["annee"] = 2025

    df_res = pd.concat(
        [pd.DataFrame(lignes), df_2025[["annee", "code_fed", "tranche_age", "licences"]]],
        ignore_index=True,
    )
    df_res = df_res[df_res["tranche_age"] != "Non renseigné"]
    return df_res.groupby(["annee", "code_fed", "tranche_age"], as_index=False)["licences"].sum()

def charger_historique_national(forcer=False):
    """Charge la série historique nationale 2002-2025 depuis le CSV nettoyé."""
    chemin_csv = PROCESSED_DIR / "licences_histo_2002_2025.csv"
    if chemin_csv.exists() and not forcer:
        df = pd.read_csv(chemin_csv, sep=";", dtype={"code_fed": str})
        df["code_fed"] = df["code_fed"].str.strip().str.zfill(3)
        df["annee"] = df["annee"].astype(int)
        df["licences"] = pd.to_numeric(df["licences"], errors="coerce")
        return df

    df = pd.read_csv(f"{SPORTS_API}/lics_histo/exports/csv?delimiter=%3B", sep=";", dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]

    df_clean = pd.DataFrame({
        "code_fed": _clean_code(df["code_fede_2025"]).str.zfill(3),
        "federation": df["federation"].astype(str).str.strip(),
        "annee": pd.to_numeric(df["annee"].astype(str).str[:4], errors="coerce"),
        "licences": pd.to_numeric(
            df["lics"].astype(str).str.replace(r"\s+", "", regex=True).str.replace(",", ".", regex=False),
            errors="coerce",
        ),
        "categorie_fede": df["fede_gp"].astype(str).str.replace(r"^\d+\.\s*", "", regex=True).str.strip(),
    }).dropna(subset=["annee"])

    masque_totaux = (
        df_clean["code_fed"].str.startswith("0")
        | df_clean["code_fed"].str.upper().isin(["TOT", "TOTAL", "NAN"])
        | df_clean["federation"].str.contains("champ constant|toutes fédés", case=False, na=False)
    )
    df_clean = df_clean[~masque_totaux].copy()
    df_clean["annee"] = df_clean["annee"].astype(int)
    df_clean = df_clean.sort_values(["code_fed", "annee"]).reset_index(drop=True)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df_clean.to_csv(chemin_csv, sep=";", index=False)
    return df_clean


def extraire_serie_communale_dep(
    code_fed_cible,
    dep_cible,
    commune_cible,
    label_commune,
    label_reste_dep,
    annees=range(2016, 2024),
):
    """Compare une commune clé au reste de son département sur 2016-2023."""
    code_cible = str(code_fed_cible).strip().lstrip("0")
    dep_clean = str(dep_cible).zfill(2)
    lignes = []

    for annee in annees:
        fichier = RAW_DIR / f"lic-data-{annee}.csv"
        if not fichier.exists():
            continue

        enc, sep, cols_propres = _detecter_csv(fichier)
        m = _detecter_colonnes(cols_propres, annee)
        usecols = {m["commune"], m["lic"]} | ({m["code_fed"]} if m["code_fed"] else set())

        tot_commune, tot_reste = 0.0, 0.0
        for chunk in pd.read_csv(
            fichier,
            sep=sep,
            encoding=enc,
            usecols=lambda c: c.strip('" ') in usecols,
            dtype=str,
            chunksize=100_000,
            quoting=3,
            on_bad_lines="warn",
        ):
            chunk.columns = [c.strip('" ') for c in chunk.columns]
            for c in chunk.columns:
                chunk[c] = chunk[c].fillna("").str.strip('" ')

            codes = _clean_code(chunk[m["code_fed"]]).str.lstrip("0")
            communes = chunk[m["commune"]].str.zfill(5)
            deps = _extraire_departement(communes)

            masque = (codes == code_cible) & (deps == dep_clean)
            if not masque.any():
                continue

            lics = pd.to_numeric(chunk.loc[masque, m["lic"]], errors="coerce").fillna(0)
            est_com = communes.loc[masque] == commune_cible
            tot_commune += lics[est_com].sum()
            tot_reste += lics[~est_com].sum()

        lignes.append({"annee": annee, "territoire": label_commune, "licences": tot_commune})
        lignes.append({"annee": annee, "territoire": label_reste_dep, "licences": tot_reste})

    df_res = pd.DataFrame(lignes)
    if df_res.empty or 2019 not in df_res["annee"].values:
        return df_res

    refs = df_res[df_res["annee"] == 2019].set_index("territoire")["licences"]
    df_res["indice_2019"] = df_res["licences"] / df_res["territoire"].map(refs).replace(0, pd.NA) * 100
    df_res["indice_2019"] = df_res["indice_2019"].fillna(0)
    return df_res