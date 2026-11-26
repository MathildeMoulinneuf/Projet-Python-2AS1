import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

GEOJSON_DEPS_URL = (
    "https://raw.githubusercontent.com/gregoiredavid/france-geojson/"
    "master/departements-version-simplifiee.geojson"
)


def plot_effet_local_base100(
    df_base100: pd.DataFrame,
    nom_sport: str,
    nom_star: str,
    annee_ref: int = 2023,
    annee_evenement: int = 2024,
    evenement_label: str = "JO-Paris 2024",
    annee_evenement2: int = None,
    evenement_label2: str = None,
) -> go.Figure:
    """Trace les courbes comparatives Base 100 entre le fief de la star et le reste de la France."""
    fig = px.line(
        df_base100,
        x="annee",
        y="indice_base_100",
        color="zone",
        markers=True,
        title=f"{nom_sport} ({nom_star}) : évolution des licences en base {annee_ref} = 100",
        labels={
            "annee": "Année",
            "indice_base_100": f"Indice des licences (Base 100 en {annee_ref})",
            "zone": "Territoire",
        },
        template="plotly_white",
    )

    # Ligne horizontale de référence (100) et repère vertical de l'événement
    fig.add_hline(y=100, line_dash="dot", line_color="gray")
    fig.add_vline(
        x=annee_evenement,
        line_dash="dash",
        line_color="#d62728",
        annotation_text=evenement_label,
        annotation_position="top left",
    )
    if annee_evenement2 is not None and evenement_label2 is not None:
        fig.add_vline(
                x=annee_evenement2,
                line_dash="dash",
                line_color="#d62728",
                annotation_text=evenement_label2,
                annotation_position="top left",
            )
    fig.update_traces(line=dict(width=3))
    return fig


def plot_carte_croissance_dep(
    df_croissance: pd.DataFrame,
    nom_sport: str,
    annee_debut: int = 2023,
    annee_fin: int = 2025,
) -> go.Figure:
    """Affiche une carte choroplèthe départementale du taux de variation des licences."""
    # Borne l'échelle de couleur sur les quantiles 5% et 95% pour éviter qu'un petit département sature la carte
    q_min = df_croissance["taux_croissance"].quantile(0.05)
    q_max = df_croissance["taux_croissance"].quantile(0.95)
    borne = max(abs(q_min), abs(q_max))

    fig = px.choropleth(
        df_croissance,
        geojson=GEOJSON_DEPS_URL,
        locations="departement",
        featureidkey="properties.code",
        color="taux_croissance",
        color_continuous_scale="RdBu",
        color_continuous_midpoint=0,
        range_color=(-borne, borne),
        hover_data={
            "departement": True,
            "taux_croissance": ":.1f",
            "variation_nette": ":+,.0f",
        },
        labels={
            "departement": "Département",
            "taux_croissance": "Variation (%)",
            "variation_nette": "Gain net de licences",
        },
        title=f"{nom_sport} : évolution des licences par département ({annee_debut}–{annee_fin})",
    )

    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(margin=dict(l=0, r=0, t=50, b=0))
    return fig



    #### GENRE


def plot_effet_genre(
    df_genre: pd.DataFrame,
    nom_sport: str,
    nom_star: str,
    annee_ref: int = 2019,
) -> go.Figure:
    """Compare l'évolution base 100 des licenciées femmes et licenciés hommes."""
    df_long = df_genre.melt(
        id_vars=["annee", "taux_feminisation"],
        value_vars=["indice_f", "indice_h"],
        var_name="sexe",
        value_name="indice",
    )
    df_long["sexe"] = df_long["sexe"].map({"indice_f": "Femmes", "indice_h": "Hommes"})

    fig = px.line(
        df_long,
        x="annee",
        y="indice",
        color="sexe",
        markers=True,
        color_discrete_map={"Femmes": "#e377c2", "Hommes": "#1f77b4"},
        title=f"{nom_sport} ({nom_star}) : dynamique Femmes vs Hommes (Base {annee_ref} = 100)",
        labels={
            "annee": "Année",
            "indice": f"Indice des licences (Base 100 en {annee_ref})",
            "sexe": "Genre",
        },
        template="plotly_white",
    )
    fig.add_hline(y=100, line_dash="dot", line_color="gray")
    fig.add_vline(
        x=2024,
        line_dash="dash",
        line_color="#d62728",
        annotation_text="JO Paris 2024",
        annotation_position="top left",
    )
    fig.update_traces(line=dict(width=3))
    return fig


    ##################################
    ### AGE
    #############################3

def plot_effet_age(df_ages: pd.DataFrame, nom_sport: str, nom_star: str, annee_ref: int = 2019) -> go.Figure:
    """Trace l'évolution base 100 des licences par tranche d'âge."""
    df = df_ages.sort_values(["tranche_age", "annee"]).copy()
    ref = df[df["annee"] == annee_ref].set_index("tranche_age")["licences"]
    df["indice_base_100"] = df.apply(lambda r: (r["licences"] / ref[r["tranche_age"]]) * 100, axis=1)

    ordre_ages = ["Moins de 10 ans", "10 à 14 ans", "15 à 19 ans", "20 ans et plus"]
    fig = px.line(
        df,
        x="annee",
        y="indice_base_100",
        color="tranche_age",
        category_orders={"tranche_age": ordre_ages},
        markers=True,
        title=f"{nom_sport} ({nom_star}) : évolution par tranche d'âge (Base {annee_ref} = 100)",
        labels={
            "annee": "Année",
            "indice_base_100": f"Indice des licences (Base 100 en {annee_ref})",
            "tranche_age": "Tranche d'âge",
        },
        template="plotly_white",
    )
    fig.add_hline(y=100, line_dash="dot", line_color="gray")
    fig.add_vline(x=2024, line_dash="dash", line_color="#d62728", annotation_text="JO Paris 2024")
    fig.update_traces(line=dict(width=3))
    return fig


    #  MEDAILLES JO

def plot_medailles_vs_croissance(df_croise: pd.DataFrame) -> go.Figure:
    """Nuage de points propre : médailles françaises vs croissance des licences (2023-2025)."""
    df = df_croise.copy()

    # Raccourcit les noms de fédérations pour éviter les chevauchements sur le graphique
    df["label_court"] = (
        df["nom_fed"]
        .str.replace("Fédération Française de ", "", regex=False)
        .str.replace("Fédération Française d'", "", regex=False)
        .str.replace("Fédération Française des ", "", regex=False)
        .str.replace(", Jujitsu, Kendo et Disciplines Associées", "", regex=False)
        .str.replace(" et Disciplines Enchainées", "", regex=False)
        .str.replace(" et Disciplines Associées", "", regex=False)
        .str.replace(" et Sports de Pagaie", "", regex=False)
    )

    # Met en évidence le Tennis de table par rapport aux autres sports
    df["categorie"] = df["code_fed"].apply(
        lambda c: "Tennis de table (Frères Lebrun)" if str(c) == "124" else "Autres fédérations olympiques"
    )

    croissance_moyenne = df["croissance_pct"].mean()

    fig = px.scatter(
        df,
        x="total_medailles",
        y="croissance_pct",
        size="nb_athletes",
        color="categorie",
        color_discrete_map={
            "Tennis de table (Frères Lebrun)": "#d62728",
            "Autres fédérations olympiques": "#1f77b4",
        },
        text="label_court",
        hover_name="nom_fed",
        hover_data={
            "disciplines_jo": True,
            "gain_net": ":+,.0f",
            "medailles_or": True,
            "categorie": False,
            "label_court": False,
        },
        title="Effet Paris 2024 : médailles françaises vs croissance des licences (2023–2025)",
        labels={
            "total_medailles": "Nombre de médailles françaises (cumul athlètes)",
            "croissance_pct": "Croissance des licences 2023–2025 (%)",
            "nb_athletes": "Athlètes engagés",
            "categorie": "",
        },
        template="plotly_white",
    )

    fig.update_traces(textposition="top center", textfont=dict(size=10), marker=dict(opacity=0.85))
    fig.add_hline(y=0, line_dash="solid", line_color="lightgray")
    fig.add_hline(
        y=croissance_moyenne,
        line_dash="dot",
        line_color="gray",
        annotation_text=f"Moyenne des sports ({croissance_moyenne:.1f} %)",
        annotation_position="bottom right",
    )
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig



#### CYLCLES OLYMP

def plot_historique_olympique(df_histo: pd.DataFrame, code_fed: str = "124", nom_sport: str = "Tennis de table") -> go.Figure:
    """Trace l'évolution nationale longue des licences avec les repères des Jeux Olympiques."""
    df_sub = df_histo[df_histo["code_fed"] == str(code_fed)].sort_values("annee").copy()

    fig = px.line(
        df_sub,
        x="annee",
        y="licences",
        markers=True,
        title=f"{nom_sport} : trajectoire historique des licences et cycles olympiques",
        labels={"annee": "Année (millésime)", "licences": "Nombre total de licenciés"},
        template="plotly_white",
    )
    fig.update_traces(line=dict(width=3, color="#1f77b4"))

    olympiades = [
        (2004, "Athènes"),
        (2008, "Pékin"),
        (2012, "Londres"),
        (2016, "Rio"),
        (2021, "Tokyo"),
        (2024, "Paris"),
    ]
    for annee_jo, ville in olympiades:
        if df_sub["annee"].min() <= annee_jo <= df_sub["annee"].max():
            couleur = "#d62728" if ville == "Paris" else "gray"
            fig.add_vline(
                x=annee_jo,
                line_dash="dash",
                line_color=couleur,
                annotation_text=ville,
                annotation_position="top left",
            )

    return fig


#IMPACT JO FR
def plot_historique_global_france(df_histo: pd.DataFrame, par_type: bool = True) -> go.Figure:
    """Trace l'évolution nationale longue des licences sportives en France (hors lignes de sous-totaux)."""
    df = df_histo.copy()

    # Exclusion des lignes de totaux agrégés présentes dans lics_histo à partir de 2016
    masque_total = (
        df["nom_fed"].str.contains("toutes|total|ensemble", case=False, na=False)
        | df["type_fed"].str.contains("toutes|total", case=False, na=False)
        | df["code_fed"].isin(["999", "000", "TOTAL", "nan", "None"])
    )
    df = df[~masque_total].copy()

    if par_type and "type_fed" in df.columns and df["type_fed"].nunique() > 1:
        df["categorie"] = (
            df["type_fed"]
            .astype(str)
            .str.replace(r"^\d+\.\s*", "", regex=True)
            .str.strip()
        )
        df_agg = df.groupby(["annee", "categorie"], as_index=False)["licences"].sum()

        fig = px.line(
            df_agg,
            x="annee",
            y="licences",
            color="categorie",
            markers=True,
            title="France entière : évolution des licences par type de fédération (2002–2025)",
            labels={
                "annee": "Année (millésime)",
                "licences": "Nombre total de licenciés",
                "categorie": "Catégorie de fédération",
            },
            template="plotly_white",
        )
    else:
        df_agg = df.groupby("annee", as_index=False)["licences"].sum()
        fig = px.line(
            df_agg,
            x="annee",
            y="licences",
            markers=True,
            title="France entière : évolution totale des licences sportives et cycles olympiques (2002–2025)",
            labels={"annee": "Année (millésime)", "licences": "Nombre total de licenciés"},
            template="plotly_white",
        )
        fig.update_traces(line=dict(width=3, color="#1f77b4"))

    fig.update_traces(line=dict(width=2.5))

    olympiades = [
        (2004, "Athènes"),
        (2008, "Pékin"),
        (2012, "Londres"),
        (2016, "Rio"),
        (2021, "Tokyo"),
        (2024, "Paris"),
    ]
    for annee_jo, ville in olympiades:
        if df_agg["annee"].min() <= annee_jo <= df_agg["annee"].max():
            couleur = "#d62728" if ville == "Paris" else "gray"
            fig.add_vline(
                x=annee_jo,
                line_dash="dash",
                line_color=couleur,
                annotation_text=ville,
                annotation_position="top left",
            )

    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig