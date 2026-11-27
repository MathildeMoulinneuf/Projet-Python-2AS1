import pandas as pd

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
    "Haltérophilie": "114",
    "Handball": "115",
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


def preparer_serie_base_100(
    df,
    federation,
    dep_cible,
    annee_ref=2023,
    label_cible=None,
    col_fed="nom_fed",
):
    """Évolution en base 100 d'un département cible face au reste de la France."""
    df_sub = df[df[col_fed] == federation].copy()
    deps = df_sub["departement"].astype(str).str.zfill(2)
    nom_cible = label_cible or f"Département {dep_cible}"

    df_sub["zone"] = "Reste de la France"
    df_sub.loc[deps == str(dep_cible).zfill(2), "zone"] = nom_cible

    agg = df_sub.groupby(["annee", "zone"], as_index=False)["licences"].sum()
    ref = agg[agg["annee"] == annee_ref].set_index("zone")["licences"]
    agg["indice_base_100"] = agg["licences"] / agg["zone"].map(ref) * 100
    return agg.sort_values(["zone", "annee"])


def calculer_ecart_double_difference(
    df_base100,
    label_cible,
    annee_avant=2023,
    annee_apres=2025,
):
    """Écart de progression en points d'indice entre la zone cible et le reste du pays."""
    piv = df_base100.pivot(index="annee", columns="zone", values="indice_base_100")
    diff_cible = piv.loc[annee_apres, label_cible] - piv.loc[annee_avant, label_cible]
    diff_reste = piv.loc[annee_apres, "Reste de la France"] - piv.loc[annee_avant, "Reste de la France"]
    return round(float(diff_cible - diff_reste), 2)


def calculer_croissance_departementale(
    df,
    federation,
    annee_debut=2023,
    annee_fin=2025,
    col_fed="nom_fed",
):
    """Taux de croissance et gain net des licences par département."""
    df_sub = df[(df[col_fed] == federation) & df["annee"].isin([annee_debut, annee_fin])].copy()
    df_sub["departement"] = df_sub["departement"].astype(str).str.zfill(2)

    piv = df_sub.groupby(["departement", "annee"])["licences"].sum().unstack("annee").dropna()
    piv = piv[piv[annee_debut] > 0].copy()
    piv["taux_croissance"] = (piv[annee_fin] / piv[annee_debut] - 1) * 100
    piv["variation_nette"] = piv[annee_fin] - piv[annee_debut]
    return piv.reset_index()


def analyser_effet_genre(
    df,
    federation,
    annee_ref=2019,
    dep_cible=None,
    col_fed="code_fed",
):
    """Évolution en base 100 par sexe et taux de féminisation d'une fédération."""
    df_sub = df[df[col_fed] == federation].copy()
    if dep_cible is not None:
        deps = df_sub["departement"].astype(str).str.zfill(2)
        df_sub = df_sub[deps == str(dep_cible).zfill(2)]

    agg = df_sub.groupby("annee", as_index=False)[["licences", "licences_f", "licences_h"]].sum()
    agg = agg.sort_values("annee").reset_index(drop=True)

    ref = agg[agg["annee"] == annee_ref].iloc[0]
    agg["taux_feminisation"] = agg["licences_f"] / agg["licences"] * 100
    agg["indice_f"] = agg["licences_f"] / ref["licences_f"] * 100
    agg["indice_h"] = agg["licences_h"] / ref["licences_h"] * 100
    return agg


def synthetiser_paris_2024_france(df_athletes):
    """Agrège les athlètes et médailles français à Paris 2024 par discipline."""
    df_fr = df_athletes[df_athletes["Pays"].str.strip() == "France"].copy()
    if "Fonction" in df_fr.columns:
        df_fr = df_fr[df_fr["Fonction"].str.strip() == "Athlète"]

    cols_med = ["Médailles d'or", "Médailles d'argent", "Médailles de bronze"]
    for col in cols_med:
        df_fr[col] = pd.to_numeric(df_fr[col], errors="coerce").fillna(0).astype(int)

    df_fr["total"] = df_fr[cols_med].sum(axis=1)

    agg = (
        df_fr.groupby("Discipline", as_index=False)
        .agg(
            nb_athletes=("nom", "nunique"),
            medailles_or=("Médailles d'or", "sum"),
            medailles_argent=("Médailles d'argent", "sum"),
            medailles_bronze=("Médailles de bronze", "sum"),
            total_medailles=("total", "sum"),
        )
        .sort_values(["total_medailles", "nb_athletes"], ascending=False)
    )
    agg["code_fed"] = agg["Discipline"].map(MAPPING_DISCIPLINE_FED)
    return agg


def croiser_medailles_et_croissance(df_licences, df_jo, annee_debut=2023, annee_fin=2025):
    """Croise le bilan olympique par fédération avec la croissance des licences."""
    agg_dict = {
        "disciplines_jo": ("Discipline", lambda s: ", ".join(sorted(set(s)))),
        "medailles_or": ("medailles_or", "sum"),
        "total_medailles": ("total_medailles", "sum"),
    }
    if "nb_athletes" in df_jo.columns:
        agg_dict["nb_athletes"] = ("nb_athletes", "sum")

    jo_fed = df_jo.dropna(subset=["code_fed"]).groupby("code_fed", as_index=False).agg(**agg_dict)

    df_sub = df_licences[df_licences["annee"].isin([annee_debut, annee_fin])].copy()
    df_sub["code_fed"] = df_sub["code_fed"].astype(str).str.strip()

    noms = df_sub.sort_values("annee").drop_duplicates("code_fed", keep="last")[["code_fed", "nom_fed"]]
    piv = (
        df_sub.groupby(["code_fed", "annee"])["licences"]
        .sum()
        .unstack("annee")
        .reset_index()
        .merge(noms, on="code_fed", how="left")
    )
    piv["croissance_pct"] = (piv[annee_fin] / piv[annee_debut] - 1) * 100
    piv["gain_net"] = piv[annee_fin] - piv[annee_debut]

    return piv.merge(jo_fed, on="code_fed", how="inner").sort_values("croissance_pct", ascending=False)


def comparer_deux_federations_base100(df_licences, feds, annee_ref=2023):
    """Compare l'évolution en base 100 (total, femmes, hommes) de plusieurs fédérations."""
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

        ref = sub[sub["annee"] == annee_ref].iloc[0]
        sub["federation"] = label
        sub["indice_total"] = sub["licences"] / ref["licences"] * 100
        sub["indice_femmes"] = sub["licences_f"] / ref["licences_f"] * 100
        sub["indice_hommes"] = sub["licences_h"] / ref["licences_h"] * 100
        resultats.append(sub)

    return pd.concat(resultats, ignore_index=True)


def analyser_persistance_olympique(df_histo, codes_feds, annees_jo=(2008, 2012, 2016, 2024)):
    """Variation des licences en t+1 et t+2 après chaque olympiade."""
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
                "evol_t1_pct": (sub.loc[jo + 1] / val_jo - 1) * 100 if (jo + 1) in sub.index else None,
                "evol_t2_pct": (sub.loc[jo + 2] / val_jo - 1) * 100 if (jo + 2) in sub.index else None,
            })
    return pd.DataFrame(lignes)