from pathlib import Path
import re
import unicodedata
import pandas as pd
import requests

API_PASSSPORT_URL = "https://www.data.gouv.fr/api/1/datasets/pass-sport-activations-journalieres/"
RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

MOTIFS_FED_INJEP = [
    (r"tennis de table|fftt", "124"),
    (r"cyclisme|ffc\b", "108"),
    (r"judo", "117"),
    (r"natation|ffn\b", "119"),
    (r"escrime|ffe\b", "110"),
    (r"badminton|ffbad", "103"),
    (r"triathlon|fftri", "127"),
    (r"football|fff\b", "111"),
    (r"basketball|basket|ffbb", "105"),
    (r"tennis\b|fft\b", "123"),
    (r"handball|ffhb", "115"),
    (r"athletisme|ffa\b", "101"),
]


def _normaliser_texte(texte):
    if pd.isna(texte):
        return ""
    s = unicodedata.normalize("NFKD", str(texte)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _associer_code_fed(nom_fed):
    s = _normaliser_texte(nom_fed)
    for motif, code in MOTIFS_FED_INJEP:
        if re.search(motif, s):
            return code
    return None


def _detecter_format_csv(chemin_csv):
    for enc in ("utf-8-sig", "utf-8", "latin1"):
        for sep in (";", ","):
            try:
                entete = pd.read_csv(chemin_csv, sep=sep, encoding=enc, nrows=5)
                if len(entete.columns) >= 3:
                    return enc, sep, list(entete.columns)
            except Exception:
                continue
    raise ValueError(f"Format CSV illisible : {chemin_csv.name}")


def _identifier_colonnes(cols):
    cols_norm = {_normaliser_texte(c): c for c in cols}

    def chercher(mots_cles):
        for kw in mots_cles:
            for norm, orig in cols_norm.items():
                if kw in norm:
                    return orig
        return None

    return {
        "federation": chercher(["nom federation", "federation", "fede"]),
        "code_fed": chercher(["code federation", "code fede"]),
        "departement": chercher(["code departement", "departement", "dep"]),
        "commune": chercher(["code commune", "commune", "code insee", "code postal"]),
        "genre": chercher(["genre", "sexe"]),
        "date": chercher(["date", "jour"]),
    }


def _standardiser_departement(serie):
    s = serie.astype(str).str.strip().str.upper().str.replace(r"\.0$", "", regex=True)
    dep_5 = s.str[:3].where(s.str.startswith(("97", "98")), s.str[:2])
    return dep_5.where(s.str.len() == 5, s).str.zfill(2)


def _standardiser_genre(serie):
    s = serie.astype(str).str.strip().str.upper()
    res = pd.Series("NR", index=serie.index)
    res.loc[s.str.startswith(("F", "2"))] = "F"
    res.loc[s.str.startswith(("H", "M", "1"))] = "H"
    return res


def lister_ressources_passsport():
    """Liste les fichiers CSV annuels d'activations Pass'Sport sur data.gouv.fr."""
    resp = requests.get(API_PASSSPORT_URL, timeout=30)
    resp.raise_for_status()

    lignes = []
    for res in resp.json().get("resources", []):
        titre = res.get("title", "")
        fmt = res.get("format", "").lower()
        match = re.search(r"(202[1-9])", titre)
        if fmt == "csv" and match and "activation" in _normaliser_texte(titre):
            campagne = int(match.group(1))
            lignes.append({
                "campagne": campagne,
                "saison": f"{campagne}/{campagne + 1}",
                "millesime_injep": campagne + 1,
                "titre": titre,
                "url": res["url"],
                "taille_mo": round((res.get("filesize") or 0) / 1e6, 1),
            })

    return pd.DataFrame(lignes).drop_duplicates(subset=["campagne"]).sort_values("campagne")


def construire_bases_passsport(forcer=False, supprimer_csv_bruts=False):
    """Télécharge et agrège les campagnes Pass'Sport par département et par semaine."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    chemin_dep = PROCESSED_DIR / "passsport_dep_2021_2024.parquet"
    chemin_temps = PROCESSED_DIR / "passsport_hebdo_2021_2024.parquet"

    if chemin_dep.exists() and chemin_temps.exists() and not forcer:
        return pd.read_parquet(chemin_dep), pd.read_parquet(chemin_temps)

    df_res = lister_ressources_passsport()
    if df_res.empty:
        raise RuntimeError("Aucune ressource CSV trouvée sur l'API Pass'Sport.")

    aggs_dep, aggs_temps = [], []

    for _, row in df_res.iterrows():
        campagne = int(row["campagne"])
        millesime_injep = int(row["millesime_injep"])
        chemin_csv = RAW_DIR / f"pass_sport_{campagne}_activations.csv"

        if not chemin_csv.exists():
            with requests.get(row["url"], stream=True, timeout=180) as r:
                r.raise_for_status()
                with open(chemin_csv, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)

        enc, sep, cols = _detecter_format_csv(chemin_csv)
        mapping = _identifier_colonnes(cols)
        cols_a_lire = [c for c in mapping.values() if c is not None]

        morceaux_dep, morceaux_temps = [], []
        for chunk in pd.read_csv(
            chemin_csv,
            sep=sep,
            encoding=enc,
            usecols=cols_a_lire,
            dtype=str,
            chunksize=250_000,
            low_memory=False,
        ):
            col_f = mapping["federation"]
            chunk["nom_fed_pass"] = chunk[col_f].fillna("Non renseigné").str.strip() if col_f else "Non renseigné"

            if mapping["code_fed"]:
                chunk["code_fed"] = (
                    chunk[mapping["code_fed"]]
                    .fillna("")
                    .str.strip()
                    .str.replace(r"\.0$", "", regex=True)
                    .str.lstrip("0")
                )
                vides = chunk["code_fed"] == ""
                chunk.loc[vides, "code_fed"] = chunk.loc[vides, "nom_fed_pass"].apply(_associer_code_fed)
            else:
                chunk["code_fed"] = chunk["nom_fed_pass"].apply(_associer_code_fed)

            col_geo = mapping["departement"] or mapping["commune"]
            chunk["departement"] = _standardiser_departement(chunk[col_geo]) if col_geo else "NR"
            chunk["genre"] = _standardiser_genre(chunk[mapping["genre"]]) if mapping["genre"] else "NR"

            morceaux_dep.append(
                chunk.groupby(["departement", "code_fed", "nom_fed_pass", "genre"], dropna=False)
                .size()
                .reset_index(name="nb_passsport")
            )

            if mapping["date"]:
                dates = pd.to_datetime(chunk[mapping["date"]], dayfirst=True, errors="coerce")
                chunk["semaine"] = dates.dt.isocalendar().week.astype("Int64")
                chunk["mois"] = dates.dt.month.astype("Int64")
                morceaux_temps.append(
                    chunk.dropna(subset=["semaine"])
                    .groupby(["code_fed", "nom_fed_pass", "mois", "semaine"], dropna=False)
                    .size()
                    .reset_index(name="nb_passsport")
                )

        df_camp_dep = (
            pd.concat(morceaux_dep, ignore_index=True)
            .groupby(["departement", "code_fed", "nom_fed_pass", "genre"], dropna=False, as_index=False)["nb_passsport"]
            .sum()
        )
        df_camp_dep["campagne"] = campagne
        df_camp_dep["millesime_injep"] = millesime_injep
        aggs_dep.append(df_camp_dep)

        if morceaux_temps:
            df_camp_tps = (
                pd.concat(morceaux_temps, ignore_index=True)
                .groupby(["code_fed", "nom_fed_pass", "mois", "semaine"], dropna=False, as_index=False)["nb_passsport"]
                .sum()
            )
            df_camp_tps["campagne"] = campagne
            df_camp_tps["millesime_injep"] = millesime_injep
            aggs_temps.append(df_camp_tps)

        if supprimer_csv_bruts and chemin_csv.exists():
            chemin_csv.unlink()

    df_passsport_dep = pd.concat(aggs_dep, ignore_index=True)
    df_passsport_temps = pd.concat(aggs_temps, ignore_index=True) if aggs_temps else pd.DataFrame()

    df_passsport_dep.to_parquet(chemin_dep, index=False)
    df_passsport_temps.to_parquet(chemin_temps, index=False)
    return df_passsport_dep, df_passsport_temps