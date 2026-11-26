from pathlib import Path
import re
import unicodedata
import pandas as pd
import requests

API_PASSSPORT_URL = "https://www.data.gouv.fr/api/1/datasets/pass-sport-activations-journalieres/"

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

# Table de correspondance vers les codes fédérations INJEP pour les sports clés du rapport
MOTIFS_FED_INJEP = [
    (r"tennis de table|fftt", "124", "Fédération Française de Tennis de Table"),
    (r"cyclisme|ffc\b", "108", "Fédération Française de Cyclisme"),
    (r"judo", "117", "Fédération Française de Judo"),
    (r"natation|ffn\b", "119", "Fédération Française de Natation"),
    (r"escrime|ffe\b", "111", "Fédération Française d'Escrime"),
    (r"badminton|ffbad", "103", "Fédération Française de Badminton"),
    (r"triathlon|fftri", "126", "Fédération Française de Triathlon"),
    (r"football|fff\b", "112", "Fédération Française de Football"),
    (r"basketball|basket|ffbb", "105", "Fédération Française de Basketball"),
    (r"tennis\b|fft\b", "123", "Fédération Française de Tennis"),
    (r"handball|ffhb", "114", "Fédération Française de Handball"),
    (r"athletisme|ffa\b", "101", "Fédération Française d'Athlétisme"),
]


def _normaliser_texte(texte: str) -> str:
    """Supprime les accents, la ponctuation et passe en minuscules."""
    if pd.isna(texte):
        return ""
    s = unicodedata.normalize("NFKD", str(texte)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _associer_code_fed(nom_fed: str) -> str | None:
    """Associe un libellé de fédération Pass'Sport au code fédération INJEP."""
    s = _normaliser_texte(nom_fed)
    for motif, code, _ in MOTIFS_FED_INJEP:
        if re.search(motif, s):
            return code
    return None


def _detecter_format_csv(chemin_csv: Path) -> tuple[str, str, list[str]]:
    """Détecte automatiquement l'encodage (utf-8 / latin1) et le séparateur (; ou ,)."""
    for enc in ("utf-8-sig", "utf-8", "latin1"):
        for sep in (";", ","):
            try:
                entete = pd.read_csv(chemin_csv, sep=sep, encoding=enc, nrows=5)
                if len(entete.columns) >= 3:
                    return enc, sep, list(entete.columns)
            except Exception:
                continue
    raise ValueError(f"Impossible de détecter le format du fichier {chemin_csv.name}")


def _identifier_colonnes(cols: list[str]) -> dict[str, str | None]:
    """Repère les colonnes utiles malgré les variations de noms selon les campagnes."""
    cols_norm = {_normaliser_texte(c): c for c in cols}

    def chercher(mots_cles: list[str]) -> str | None:
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
        "tranche_age": chercher(["tranche", "age"]),
    }


def _standardiser_departement(serie: pd.Series) -> pd.Series:
    """Normalise les codes départements (2 caractères, gestion Corse 2A/2B et DOM 971-976)."""
    s = serie.astype(str).str.strip().str.upper().str.replace(r"\.0$", "", regex=True)
    # Si code commune ou code postal sur 5 caractères, extraction des 2 ou 3 premiers chiffres
    est_5_car = s.str.len() == 5
    dep_depuis_5 = s.str[:3].where(s.str.startswith(("97", "98")), s.str[:2])
    s = dep_depuis_5.where(est_5_car, s)
    return s.str.zfill(2)


def _standardiser_genre(serie: pd.Series) -> pd.Series:
    """Harmonise le genre en F, H ou NR."""
    s = serie.astype(str).str.strip().str.upper()
    res = pd.Series("NR", index=serie.index)
    res = res.where(~s.str.startswith(("F", "2")), "F")
    res = res.where(~s.str.startswith(("H", "M", "1")), "H")
    return res


def lister_ressources_passsport() -> pd.DataFrame:
    """Interroge l'API data.gouv.fr pour lister les fichiers CSV annuels Pass'Sport."""
    resp = requests.get(API_PASSSPORT_URL, timeout=30)
    resp.raise_for_status()
    resources = resp.json().get("resources", [])

    lignes = []
    for res in resources:
        titre = res.get("title", "")
        fmt = res.get("format", "").lower()
        match_annee = re.search(r"(202[1-9])", titre)
        if fmt == "csv" and match_annee and "activation" in _normaliser_texte(titre):
            campagne = int(match_annee.group(1))
            lignes.append({
                "campagne": campagne,
                "saison": f"{campagne}/{campagne + 1}",
                "millesime_injep": campagne + 1,
                "titre": titre,
                "url": res["url"],
                "taille_mo": round((res.get("filesize") or 0) / 1e6, 1),
            })

    df_res = pd.DataFrame(lignes).drop_duplicates(subset=["campagne"]).sort_values("campagne")
    return df_res


def construire_bases_passsport(
    forcer: bool = False,
    supprimer_csv_bruts: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Télécharge et agrège toutes les campagnes Pass'Sport disponibles.
    Retourne deux DataFrames :
      1. df_passsport_dep : agrégation par campagne, département, fédération et genre.
      2. df_passsport_temps : agrégation hebdomadaire pour suivre la dynamique de rentrée.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    chemin_dep = PROCESSED_DIR / "passsport_dep_2021_2024.parquet"
    chemin_temps = PROCESSED_DIR / "passsport_hebdo_2021_2024.parquet"

    if chemin_dep.exists() and chemin_temps.exists() and not forcer:
        return pd.read_parquet(chemin_dep), pd.read_parquet(chemin_temps)

    df_res = lister_ressources_passsport()
    if df_res.empty:
        raise RuntimeError("Aucune ressource CSV trouvée sur l'API Pass'Sport.")

    aggs_dep = []
    aggs_temps = []

    for _, row in df_res.iterrows():
        campagne = int(row["campagne"])
        millesime_injep = int(row["millesime_injep"])
        chemin_csv = RAW_DIR / f"pass_sport_{campagne}_activations.csv"

        if not chemin_csv.exists():
            print(f"Téléchargement campagne {campagne} ({row['taille_mo']} Mo)...")
            with requests.get(row["url"], stream=True, timeout=180) as r:
                r.raise_for_status()
                with open(chemin_csv, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)

        enc, sep, cols = _detecter_format_csv(chemin_csv)
        mapping = _identifier_colonnes(cols)
        cols_a_lire = [c for c in mapping.values() if c is not None]

        morceaux_dep = []
        morceaux_temps = []

        for chunk in pd.read_csv(
            chemin_csv,
            sep=sep,
            encoding=enc,
            usecols=cols_a_lire,
            dtype=str,
            chunksize=250_000,
            low_memory=False,
        ):
            # 1. Fédération et correspondance code INJEP
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
                masque_vide = chunk["code_fed"] == ""
                chunk.loc[masque_vide, "code_fed"] = chunk.loc[masque_vide, "nom_fed_pass"].apply(_associer_code_fed)
            else:
                chunk["code_fed"] = chunk["nom_fed_pass"].apply(_associer_code_fed)

            # 2. Département
            if mapping["departement"]:
                chunk["departement"] = _standardiser_departement(chunk[mapping["departement"]])
            elif mapping["commune"]:
                chunk["departement"] = _standardiser_departement(chunk[mapping["commune"]])
            else:
                chunk["departement"] = "NR"

            # 3. Genre
            if mapping["genre"]:
                chunk["genre"] = _standardiser_genre(chunk[mapping["genre"]])
            else:
                chunk["genre"] = "NR"

            # Agrégation territoriale et démographique
            g_dep = (
                chunk.groupby(["departement", "code_fed", "nom_fed_pass", "genre"], dropna=False)
                .size()
                .reset_index(name="nb_passsport")
            )
            morceaux_dep.append(g_dep)

            # 4. Dynamique temporelle (semaine de l'année pour comparer les rentrées)
            if mapping["date"]:
                dates = pd.to_datetime(chunk[mapping["date"]], dayfirst=True, errors="coerce")
                chunk["semaine"] = dates.dt.isocalendar().week.astype("Int64")
                chunk["mois"] = dates.dt.month.astype("Int64")
                g_tps = (
                    chunk.dropna(subset=["semaine"])
                    .groupby(["code_fed", "nom_fed_pass", "mois", "semaine"], dropna=False)
                    .size()
                    .reset_index(name="nb_passsport")
                )
                morceaux_temps.append(g_tps)

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

        print(f"Campagne {campagne} (saison {campagne}/{campagne + 1}) agrégée : {df_camp_dep['nb_passsport'].sum():,.0f} activations.")

        if supprimer_csv_bruts and chemin_csv.exists():
            chemin_csv.unlink()

    df_passsport_dep = pd.concat(aggs_dep, ignore_index=True)
    df_passsport_temps = pd.concat(aggs_temps, ignore_index=True) if aggs_temps else pd.DataFrame()

    df_passsport_dep.to_parquet(chemin_dep, index=False)
    df_passsport_temps.to_parquet(chemin_temps, index=False)
    return df_passsport_dep, df_passsport_temps