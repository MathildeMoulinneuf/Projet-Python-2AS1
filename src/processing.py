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