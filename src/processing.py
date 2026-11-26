import pandas as pd


def preparer_serie_base_100(
    df: pd.DataFrame,
    federation: str,
    dep_cible: str,
    annee_ref: int = 2023,
    label_cible: str | None = None,
    col_fed: str = "nom_fed",
) -> pd.DataFrame:
    """Calcule l'évolution base 100 d'un département cible face au reste de la France."""
    df_sub = df[df[col_fed] == federation].copy()
    if df_sub.empty:
        raise ValueError(f"Aucune donnée trouvée pour '{federation}' dans la colonne '{col_fed}'.")

    df_sub["departement"] = df_sub["departement"].astype(str).str.zfill(2)

    nom_cible = label_cible or f"Département {dep_cible}"
    df_sub["zone"] = df_sub["departement"].apply(
        lambda d: nom_cible if d == dep_cible else "Reste de la France"
    )

    agg = df_sub.groupby(["annee", "zone"], as_index=False)["licences"].sum()

    ref = agg[agg["annee"] == annee_ref].set_index("zone")["licences"]
    if ref.empty:
        raise ValueError(f"Année de référence {annee_ref} absente des données ({sorted(agg['annee'].unique())}).")

    agg["indice_base_100"] = agg.apply(
        lambda r: (r["licences"] / ref[r["zone"]]) * 100, axis=1
    )
    return agg.sort_values(["zone", "annee"])


def calculer_ecart_double_difference(
    df_base100: pd.DataFrame,
    label_cible: str,
    annee_avant: int = 2023,
    annee_apres: int = 2025,
) -> float:
    """Mesure l'écart de progression (en points d'indice) entre la zone cible et le reste du pays."""
    piv = df_base100.pivot(index="annee", columns="zone", values="indice_base_100")
    diff_cible = piv.loc[annee_apres, label_cible] - piv.loc[annee_avant, label_cible]
    diff_reste = piv.loc[annee_apres, "Reste de la France"] - piv.loc[annee_avant, "Reste de la France"]
    return round(float(diff_cible - diff_reste), 2)


def calculer_croissance_departementale(
    df: pd.DataFrame,
    federation: str,
    annee_debut: int = 2023,
    annee_fin: int = 2025,
    col_fed: str = "nom_fed",
) -> pd.DataFrame:
    """Calcule le taux de croissance des licences par département entre deux années."""
    df_sub = df[
        (df[col_fed] == federation) & (df["annee"].isin([annee_debut, annee_fin]))
    ].copy()
    df_sub["departement"] = df_sub["departement"].astype(str).str.zfill(2)

    piv = (
        df_sub.groupby(["departement", "annee"])["licences"]
        .sum()
        .unstack("annee")
        .dropna()
    )
    piv = piv[piv[annee_debut] > 0].copy()
    piv["taux_croissance"] = ((piv[annee_fin] - piv[annee_debut]) / piv[annee_debut]) * 100
    piv["variation_nette"] = piv[annee_fin] - piv[annee_debut]

    return piv.reset_index()




    ### GENRE
def analyser_effet_genre(
    df: pd.DataFrame,
    federation: str,
    annee_ref: int = 2019,
    dep_cible: str | None = None,
    col_fed: str = "code_fed",
) -> pd.DataFrame:
    """Calcule l'évolution base 100 par sexe et le taux de féminisation d'une fédération."""
    df_sub = df[df[col_fed] == federation].copy()
    if dep_cible is not None:
        df_sub["departement"] = df_sub["departement"].astype(str).str.zfill(2)
        df_sub = df_sub[df_sub["departement"] == dep_cible]

    agg = df_sub.groupby("annee", as_index=False)[["licences", "licences_f", "licences_h"]].sum()
    agg = agg.sort_values("annee").reset_index(drop=True)

    # Taux de féminisation en pourcentage
    agg["taux_feminisation"] = (agg["licences_f"] / agg["licences"]) * 100

    # Indices Base 100 par sexe
    ref = agg[agg["annee"] == annee_ref].iloc[0]
    agg["indice_f"] = (agg["licences_f"] / ref["licences_f"]) * 100
    agg["indice_h"] = (agg["licences_h"] / ref["licences_h"]) * 100

    return agg


#### MEDAILLES JO

MAPPING_DISCIPLINE_FED = {
    "Athlétisme": "101",
    "Aviron": "102",
    "Badminton": "103",
    "Basketball": "105",
    "Basketball 3x3": "105",
    "Boxe": "106",
    "Canoë-kayak slalom": "107",
    "Canoë-kayak sprint": "107",
    "Cyclisme sur route": "108",
    "Cyclisme sur piste": "108",
    "Cyclisme Mountain Bike": "108",
    "Cyclisme BMX Racing": "108",
    "Cyclisme BMX Freestyle": "108",
    "Sports équestres": "109",
    "Escrime": "110",
    "Football": "111",
    "Gymnastique artistique": "113",
    "Gymnastique rythmique": "113",
    "Trampoline": "113",
    "Handball": "114",
    "Haltérophilie": "115",
    "Hockey": "116",
    "Judo": "117",
    "Lutte": "118",
    "Natation": "119",
    "Natation, marathon": "119",
    "Natation artistique": "119",
    "Plongeon": "119",
    "Water-polo": "119",
    "Taekwondo": "122",
    "Tennis": "123",
    "Tennis de table": "124",
    "Tir": "125",
    "Tir à l'arc": "126",
    "Triathlon": "127",
    "Voile": "128",
    "Volleyball": "129",
    "Volleyball de plage": "129",
    "Rugby à sept": "133",
}


def synthetiser_paris_2024_france(df_athletes: pd.DataFrame) -> pd.DataFrame:
    """Agrège les athlètes et médailles de la délégation française à Paris 2024 par discipline."""
    df_fr = df_athletes[df_athletes["Pays"].str.strip() == "France"].copy()
    if "Fonction" in df_fr.columns:
        df_fr = df_fr[df_fr["Fonction"].str.strip() == "Athlète"]

    for col in ["Médailles d'or", "Médailles d'argent", "Médailles de bronze"]:
        df_fr[col] = pd.to_numeric(df_fr[col], errors="coerce").fillna(0).astype(int)

    df_fr["total_medailles_indiv"] = (
        df_fr["Médailles d'or"] + df_fr["Médailles d'argent"] + df_fr["Médailles de bronze"]
    )

    agg = (
        df_fr.groupby("Discipline", as_index=False)
        .agg(
            nb_athletes=("nom", "nunique"),
            medailles_or=("Médailles d'or", "sum"),
            medailles_argent=("Médailles d'argent", "sum"),
            medailles_bronze=("Médailles de bronze", "sum"),
            total_medailles=("total_medailles_indiv", "sum"),
        )
        .sort_values(["total_medailles", "nb_athletes"], ascending=False)
    )
    agg["code_fed"] = agg["Discipline"].map(MAPPING_DISCIPLINE_FED)
    return agg

def synthetiser_medailles_2012_2014(
    df_medailles: pd.DataFrame, annee_jo: int = 2012, type_jeux: str = "Olympique"
) -> pd.DataFrame:
    """Agrège les médailles françaises aux JO 2012 (ou 2014) par discipline."""
    df_sub = df_medailles[
        (pd.to_numeric(df_medailles["Année"], errors="coerce") == annee_jo)
        & (df_medailles["Olympique/paralympique"].str.strip() == type_jeux)
    ].copy()

    df_sub["athlete_id"] = (
        df_sub["NOM"].fillna("").str.strip() + " " + df_sub["Prénom"].fillna("").str.strip()
    )

    agg = (
        df_sub.groupby(["Fédération", "Discipline"], as_index=False)
        .agg(
            nb_athletes=("athlete_id", "nunique"),
            total_medailles=("MEDAILLE(S)", "count"),
            medailles_or=("MEDAILLE(S)", lambda s: (s.str.strip().str.lower() == "or").sum()),
        )
        .sort_values("total_medailles", ascending=False)
    )
    agg["code_fed"] = agg["Discipline"].map(MAPPING_DISCIPLINE_FED)
    return agg


def croiser_medailles_et_croissance(
    df_licences: pd.DataFrame,
    df_jo: pd.DataFrame,
    annee_debut: int = 2023,
    annee_fin: int = 2025,
) -> pd.DataFrame:
    """Relie les médailles/athlètes d'une édition JO à la croissance des licences par fédération."""
    agg_dict = {
        "disciplines_jo": ("Discipline", lambda s: ", ".join(sorted(set(s)))),
        "medailles_or": ("medailles_or", "sum"),
        "total_medailles": ("total_medailles", "sum"),
    }
    if "nb_athletes" in df_jo.columns:
        agg_dict["nb_athletes"] = ("nb_athletes", "sum")

    jo_fed = (
        df_jo.dropna(subset=["code_fed"])
        .groupby("code_fed", as_index=False)
        .agg(**agg_dict)
    )

    df_sub = df_licences[df_licences["annee"].isin([annee_debut, annee_fin])].copy()
    df_sub["code_fed"] = df_sub["code_fed"].astype(str).str.strip()

    noms_recents = (
        df_sub.sort_values("annee")
        .drop_duplicates("code_fed", keep="last")[["code_fed", "nom_fed"]]
    )

    lic_nat = df_sub.groupby(["code_fed", "annee"], as_index=False)["licences"].sum()
    piv = lic_nat.pivot(index="code_fed", columns="annee", values="licences").reset_index()
    piv = piv.merge(noms_recents, on="code_fed", how="left")

    piv["croissance_pct"] = ((piv[annee_fin] - piv[annee_debut]) / piv[annee_debut]) * 100
    piv["gain_net"] = piv[annee_fin] - piv[annee_debut]

    return piv.merge(jo_fed, on="code_fed", how="inner").sort_values("croissance_pct", ascending=False)


def comparer_deux_federations_base100(
    df_licences: pd.DataFrame,
    feds: dict[str, str],
    annee_ref: int = 2023,
) -> pd.DataFrame:
    """Compare l'évolution en base 100 (Total, Femmes, Hommes) de plusieurs fédérations."""
    df = df_licences.copy()
    df["code_fed"] = df["code_fed"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)

    resultats = []
    for label, code in feds.items():
        sub = (
            df[df["code_fed"] == str(code)]
            .groupby("annee", as_index=False)[["licences", "licences_f", "licences_h"]]
            .sum()
            .sort_values("annee")
        )
        if sub.empty or annee_ref not in sub["annee"].values:
            continue

        ref = sub.loc[sub["annee"] == annee_ref].iloc[0]
        sub["federation"] = label
        sub["indice_total"] = (sub["licences"] / ref["licences"]) * 100
        sub["indice_femmes"] = (sub["licences_f"] / ref["licences_f"]) * 100
        sub["indice_hommes"] = (sub["licences_h"] / ref["licences_h"]) * 100
        resultats.append(sub)

    return pd.concat(resultats, ignore_index=True)


def analyser_persistance_olympique(
    
    df_histo: pd.DataFrame,
    codes_feds: dict[str, str],
    annees_jo: list[int] = [2008, 2012, 2016, 2024],
) -> pd.DataFrame:
    """Calcule la variation des licences en t+1 et t+2 après chaque olympiade (Base 100 = année des JO)."""
    lignes = []
    for nom_sport, code in codes_feds.items():
        sub = df_histo[df_histo["code_fed"] == str(code)].set_index("annee")["licences"]
        for jo in annees_jo:
            if jo not in sub.index:
                continue
            val_jo = sub.loc[jo]
            lignes.append({
                "sport": nom_sport,
                "olympiade": jo,
                "licences_jo": val_jo,
                "evol_t1_pct": ((sub.loc[jo + 1] / val_jo) - 1) * 100 if (jo + 1) in sub.index else None,
                "evol_t2_pct": ((sub.loc[jo + 2] / val_jo) - 1) * 100 if (jo + 2) in sub.index else None,
            })
    return pd.DataFrame(lignes)
