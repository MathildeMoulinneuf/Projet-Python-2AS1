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
        annotation_text="JO Paris 2024",
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



def plot_attention_mediatique(df_vues: pd.DataFrame) -> go.Figure:
    """Trace l'évolution mensuelle des consultations Wikipédia autour des JO de Paris 2024."""
    fig = px.line(
        df_vues,
        x="date",
        y="vues",
        color="personnalite",
        markers=True,
        title="Attention médiatique : vues mensuelles sur Wikipédia France (2023–2025)",
        labels={
            "date": "Mois",
            "vues": "Nombre de pages vues",
            "personnalite": "Athlète",
        },
        template="plotly_white",
    )
    fig.update_traces(line=dict(width=2.5))

    fig.add_vrect(
        x0="2024-07-26",
        x1="2024-08-11",
        fillcolor="red",
        opacity=0.12,
        line_width=0,
        annotation_text="JO Paris 2024",
        annotation_position="top left",
    )


    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig



def plot_attention_mediatique_zoom(df_vues_jour: pd.DataFrame) -> go.Figure:
    """Trace l'évolution journalière des consultations Wikipédia autour des JO (juillet-septembre 2024)."""
    fig = px.line(
        df_vues_jour,
        x="date",
        y="vues",
        color="personnalite",
        title="Zoom journalier : attention médiatique pendant Paris 2024 et à la rentrée (été 2024)",
        labels={
            "date": "Date",
            "vues": "Pages vues par jour",
            "personnalite": "Athlète",
        },
        template="plotly_white",
    )
    fig.update_traces(line=dict(width=2.2))

    # Fenêtre officielle des JO de Paris 2024
    fig.add_vrect(
        x0="2024-07-26",
        x1="2024-08-11",
        fillcolor="grey",
        opacity=0.10,
        line_width=0,
        annotation_text="JO Paris 2024 (26 juil. - 11 août)",
        annotation_position="top left",
    )



    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig


from plotly.subplots import make_subplots


def plot_comparaison_lebrun_ferrand_prevot(df_comp: pd.DataFrame, annee_ref: int = 2023) -> go.Figure:
    """Compare côte à côte l'évolution totale et féminine de deux fédérations en base 100."""
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(
            f"Total des licenciés (Base 100 en {annee_ref})",
            f"Licenciées femmes uniquement (Base 100 en {annee_ref})",
        ),
    )

    couleurs = {"Tennis de table (Frères Lebrun)": "#1f77b4", "Cyclisme (P. Ferrand-Prévot)": "#e377c2"}

    for fed, groupe in df_comp.groupby("federation"):
        couleur = couleurs.get(fed, None)
        fig.add_trace(
            go.Scatter(
                x=groupe["annee"],
                y=groupe["indice_total"],
                mode="lines+markers",
                name=fed,
                legendgroup=fed,
                line=dict(width=3, color=couleur),
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=groupe["annee"],
                y=groupe["indice_femmes"],
                mode="lines+markers",
                name=fed,
                legendgroup=fed,
                showlegend=False,
                line=dict(width=3, color=couleur),
            ),
            row=1,
            col=2,
        )

    for col in (1, 2):
        fig.add_hline(y=100, line_dash="dot", line_color="gray", row=1, col=col)
        fig.add_vline(x=2024, line_dash="dash", line_color="#d62728", row=1, col=col)

    fig.update_layout(
        title="Comparaison directe : effet Frères Lebrun (FFTT) vs effet Pauline Ferrand-Prévot (FFC)",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.08, xanchor="right", x=1),
    )
    fig.update_yaxes(title_text=f"Indice (Base 100 en {annee_ref})", row=1, col=1)
    return fig


def plot_effet_communal_compare(df_com_tt: pd.DataFrame, df_com_velo: pd.DataFrame) -> go.Figure:
    """Compare la diffusion communale (Montpellier vs Hérault et Reims vs Marne) en base 2019 = 100."""
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Tennis de table : Montpellier vs Hérault", "Cyclisme : Reims vs Marne"),
    )

    for col_idx, df_sub in [(1, df_com_tt), (2, df_com_velo)]:
        for i, (terr, grp) in enumerate(df_sub.groupby("territoire")):
            fig.add_trace(
                go.Scatter(
                    x=grp["annee"],
                    y=grp["indice_2019"],
                    mode="lines+markers",
                    name=terr,
                    line=dict(width=3, dash="solid" if i == 0 else "dash"),
                ),
                row=1,
                col=col_idx,
            )
        fig.add_hline(y=100, line_dash="dot", line_color="gray", row=1, col=col_idx)

    fig.update_layout(
        title="Diffusion infra-départementale : ville d'entraînement vs reste du département (Base 2019 = 100)",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.08, xanchor="right", x=1),
    )
    fig.update_yaxes(title_text="Indice (Base 100 en 2019)", row=1, col=1)
    return fig


def plot_comparaison_federations_base100(
    df_comp: pd.DataFrame,
    annee_ref: int = 2023,
    titre: str = "Comparaison de deux fédérations (Base 100)",
) -> go.Figure:
    """Compare côte à côte l'évolution totale et féminine de plusieurs fédérations en base 100."""
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(
            f"Total des licenciés (Base 100 en {annee_ref})",
            f"Licenciées femmes uniquement (Base 100 en {annee_ref})",
        ),
    )

    for fed, groupe in df_comp.groupby("federation"):
        fig.add_trace(
            go.Scatter(
                x=groupe["annee"],
                y=groupe["indice_total"],
                mode="lines+markers",
                name=fed,
                legendgroup=fed,
                line=dict(width=3),
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=groupe["annee"],
                y=groupe["indice_femmes"],
                mode="lines+markers",
                name=fed,
                legendgroup=fed,
                showlegend=False,
                line=dict(width=3),
            ),
            row=1,
            col=2,
        )

    for col in (1, 2):
        fig.add_hline(y=100, line_dash="dot", line_color="gray", row=1, col=col)
        fig.add_vline(x=2024, line_dash="dash", line_color="#d62728", row=1, col=col)

    fig.update_layout(
        title=titre,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.08, xanchor="right", x=1),
    )
    fig.update_yaxes(title_text=f"Indice (Base 100 en {annee_ref})", row=1, col=1)
    return fig


def plot_comparaison_longue_base100(
    df_histo: pd.DataFrame,
    feds: dict[str, str],
    annee_ref: int = 2008,
) -> go.Figure:
    """Compare l'évolution historique (2002-2025) de plusieurs fédérations en base 100."""
    lignes = []
    for label, code in feds.items():
        sub = df_histo[df_histo["code_fed"] == str(code)].sort_values("annee").copy()
        if sub.empty or annee_ref not in sub["annee"].values:
            continue
        val_ref = sub.loc[sub["annee"] == annee_ref, "licences"].iloc[0]
        sub["federation"] = label
        sub["indice"] = (sub["licences"] / val_ref) * 100
        lignes.append(sub)

    df_plot = pd.concat(lignes, ignore_index=True)

    fig = px.line(
        df_plot,
        x="annee",
        y="indice",
        color="federation",
        markers=True,
        title=f"Révélation vs icône installée : trajectoire historique (Base 100 en {annee_ref})",
        labels={"annee": "Année", "indice": f"Indice des licences (Base 100 en {annee_ref})", "federation": "Fédération"},
        template="plotly_white",
    )
    fig.update_traces(line=dict(width=2.8))
    fig.add_hline(y=100, line_dash="dot", line_color="gray")

    for annee_jo, ville in [(2008, "Pékin (1er podium Riner)"), (2012, "Londres"), (2016, "Rio"), (2021, "Tokyo"), (2024, "Paris")]:
        couleur = "#d62728" if annee_jo == 2024 else "gray"
        fig.add_vline(x=annee_jo, line_dash="dash", line_color=couleur, annotation_text=ville, annotation_position="top left")

    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig


def plot_superposition_genre_role_models(
    df_comp: pd.DataFrame,
    annee_ref: int = 2023,
) -> go.Figure:
    """Superpose sur un même graphique l'évolution Femmes (trait plein) et Hommes (pointillés) de deux sports."""
    fig = go.Figure()

    styles = {
        "Tennis de table (Frères Lebrun)": {"couleur": "#1f77b4", "label_court": "Tennis de table (Lebrun)"},
        "Cyclisme (P. Ferrand-Prévot)": {"couleur": "#e377c2", "label_court": "Cyclisme (Ferrand-Prévot)"},
    }

    for fed, groupe in df_comp.groupby("federation"):
        groupe = groupe.sort_values("annee")
        cfg = styles.get(fed, {"couleur": None, "label_court": fed})
        couleur = cfg["couleur"]
        nom = cfg["label_court"]

        # Courbe principale : Femmes (trait plein épais)
        fig.add_trace(
            go.Scatter(
                x=groupe["annee"],
                y=groupe["indice_femmes"],
                mode="lines+markers",
                name=f"{nom} — Femmes",
                line=dict(color=couleur, width=3.5, dash="solid"),
                marker=dict(size=7),
            )
        )

        # Courbe de référence : Hommes (pointillés plus fins)
        fig.add_trace(
            go.Scatter(
                x=groupe["annee"],
                y=groupe["indice_hommes"],
                mode="lines+markers",
                name=f"{nom} — Hommes",
                line=dict(color=couleur, width=2, dash="dash"),
                marker=dict(size=5, symbol="diamond"),
                opacity=0.65,
            )
        )

    fig.add_hline(y=100, line_dash="dot", line_color="gray")
    fig.add_vline(
        x=2024,
        line_dash="dash",
        line_color="#d62728",
        annotation_text="JO Paris 2024",
        annotation_position="top left",
    )

    fig.update_layout(
        title=f"Identification genrée : dynamique Femmes vs Hommes selon le rôle modèle (Base 100 en {annee_ref})",
        xaxis_title="Année",
        yaxis_title=f"Indice des licences (Base 100 en {annee_ref})",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def plot_evolution_passsport_sports(
    df_pass_dep: pd.DataFrame,
    feds: dict[str, str],
    campagne_ref: int = 2023,
) -> go.Figure:
    """Compare l'évolution des recours Pass'Sport en base 100 (référence 2023) sur plusieurs disciplines."""
    lignes = []
    for nom_sport, code in feds.items():
        sub = (
            df_pass_dep[df_pass_dep["code_fed"] == str(code)]
            .groupby("campagne", as_index=False)["nb_passsport"]
            .sum()
            .sort_values("campagne")
        )
        if sub.empty or campagne_ref not in sub["campagne"].values:
            continue

        val_ref = sub.loc[sub["campagne"] == campagne_ref, "nb_passsport"].iloc[0]
        sub["sport"] = nom_sport
        sub["saison"] = sub["campagne"].apply(lambda c: f"{c}/{str(c + 1)[-2:]}")
        sub["indice"] = (sub["nb_passsport"] / val_ref) * 100
        lignes.append(sub)

    df_plot = pd.concat(lignes, ignore_index=True)
    campagnes_uniques = sorted(df_plot["campagne"].unique())

    fig = px.line(
        df_plot,
        x="campagne",
        y="indice",
        color="sport",
        markers=True,
        title=f"Recours au Pass'Sport par discipline (Base 100 = saison {campagne_ref}/{str(campagne_ref + 1)[-2:]})",
        labels={
            "campagne": "Saison sportive",
            "indice": "Indice des activations Pass'Sport (Base 100)",
            "sport": "Discipline",
        },
        hover_data={"saison": True, "campagne": False, "nb_passsport": ":,.0f", "indice": ":.1f"},
        template="plotly_white",
    )
    fig.update_traces(line=dict(width=3), marker=dict(size=8))
    fig.add_hline(y=100, line_dash="dot", line_color="gray")
    fig.add_vline(
        x=2024,
        line_dash="dash",
        line_color="#d62728",
        annotation_text="Rentrée post-JO Paris 2024",
        annotation_position="top left",
    )
    fig.update_xaxes(
        tickmode="array",
        tickvals=campagnes_uniques,
        ticktext=[f"{c}/{str(c + 1)[-2:]}" for c in campagnes_uniques],
    )
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig



def plot_rentree_hebdo_passsport(
    df_pass_hebdo: pd.DataFrame,
    code_fed: str = "124",
    nom_sport: str = "Tennis de table (FFTT)",
    campagnes: list[int] = [2023, 2024],
) -> go.Figure:
    """Compare le rythme hebdomadaire des activations Pass'Sport entre deux rentrées (pré-JO vs post-JO)."""
    sub = df_pass_hebdo[
        (df_pass_hebdo["code_fed"] == str(code_fed))
        & (df_pass_hebdo["campagne"].isin(campagnes))
        & (df_pass_hebdo["semaine"].between(33, 48))  # Mi-août à fin novembre
    ].copy()

    sub = (
        sub.groupby(["campagne", "semaine"], as_index=False)["nb_passsport"]
        .sum()
        .sort_values(["campagne", "semaine"])
    )
    sub["Campagne"] = sub["campagne"].map({
        2023: "Rentrée 2023/24 (Avant JO)",
        2024: "Rentrée 2024/25 (Post-JO Paris 2024)",
    }).fillna(sub["campagne"].astype(str))

    fig = px.bar(
        sub,
        x="semaine",
        y="nb_passsport",
        color="Campagne",
        barmode="group",
        title=f"{nom_sport} : activations hebdomadaires du Pass'Sport à la rentrée",
        labels={
            "semaine": "Numéro de semaine (35 = fin août / rentrée scolaire)",
            "nb_passsport": "Nombre de Pass'Sport activés",
        },
        color_discrete_map={
            "Rentrée 2023/24 (Avant JO)": "#7f7f7f",
            "Rentrée 2024/25 (Post-JO Paris 2024)": "#1f77b4",
        },
        template="plotly_white",
    )


    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig