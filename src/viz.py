import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

GEOJSON_DEPS_URL = (
    "https://raw.githubusercontent.com/gregoiredavid/france-geojson/"
    "master/departements-version-simplifiee.geojson"
)

OLYMPIADES = [
    (2004, "Athènes"),
    (2008, "Pékin"),
    (2012, "Londres"),
    (2016, "Rio"),
    (2021, "Tokyo"),
    (2024, "Paris"),
]

LEGEND_TOP = dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)


def plot_boxplot_dispersion_departementale(
    df_licences,
    feds,
    annee_debut=2023,
    annee_fin=2025,
    col_fed="code_fed",
):
    """Distribution des taux de croissance départementaux entre deux années."""
    sub = df_licences[
        df_licences["annee"].isin([annee_debut, annee_fin])
        & df_licences[col_fed].isin(feds.values())
        & (df_licences["departement"] != "NR")
    ]

    piv = (
        sub.groupby([col_fed, "departement", "annee"])["licences"]
        .sum()
        .unstack("annee")
        .dropna(subset=[annee_debut, annee_fin])
        .rename(columns={annee_debut: "licences_debut", annee_fin: "licences_fin"})
        .reset_index()
    )

    piv = piv[piv["licences_debut"] >= 50].copy()
    piv["variation_pct"] = (piv["licences_fin"] / piv["licences_debut"] - 1) * 100
    piv["sport"] = piv[col_fed].astype(str).map({str(v): k for k, v in feds.items()})

    ordre = piv.groupby("sport")["variation_pct"].median().sort_values(ascending=False).index

    fig = px.box(
        piv,
        x="sport",
        y="variation_pct",
        color="sport",
        points="all",
        category_orders={"sport": list(ordre)},
        hover_data={
            "departement": True,
            "licences_debut": ":,.0f",
            "licences_fin": ":,.0f",
            "variation_pct": ":.1f",
        },
        title=f"Dispersion territoriale : croissances départementales ({annee_debut}-{annee_fin})",
        labels={
            "sport": "Discipline",
            "variation_pct": f"Variation par département ({annee_debut}-{annee_fin}, %)",
            "departement": "Département",
            "licences_debut": f"Licences {annee_debut}",
            "licences_fin": f"Licences {annee_fin}",
        },
        template="plotly_white",
    )
    fig.update_traces(jitter=0.35, pointpos=-1.6, marker=dict(size=5, opacity=0.65))
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.update_layout(showlegend=False)
    return fig


def plot_historique_olympique(df_histo, code_fed="124", nom_sport="Tennis de table"):
    """Trajectoire nationale longue des licences avec repères des olympiades."""
    df_sub = df_histo[df_histo["code_fed"] == str(code_fed)].sort_values("annee")

    fig = px.line(
        df_sub,
        x="annee",
        y="licences",
        markers=True,
        title=f"{nom_sport} : trajectoire historique des licences et cycles olympiques",
        labels={"annee": "Année", "licences": "Nombre total de licenciés"},
        template="plotly_white",
    )
    fig.update_traces(line=dict(width=3, color="#1f77b4"))

    for annee_jo, ville in OLYMPIADES:
        if df_sub["annee"].min() <= annee_jo <= df_sub["annee"].max():
            fig.add_vline(
                x=annee_jo,
                line_dash="dash",
                line_color="#d62728" if ville == "Paris" else "gray",
                annotation_text=ville,
                annotation_position="top left",
            )
    return fig


def plot_medailles_vs_croissance(df_croise):
    """Nuage de points reliant médailles françaises et croissance des licences."""
    df = df_croise.copy()
    df["label_court"] = (
        df["nom_fed"]
        .str.replace(r"^Fédération Française (de |d'|des )", "", regex=True)
        .str.replace(r"(, Jujitsu.*| et Disciplines.*| et Sports de Pagaie)$", "", regex=True)
    )
    df["categorie"] = df["code_fed"].astype(str).apply(
        lambda c: "Tennis de table (Frères Lebrun)" if c == "124" else "Autres fédérations olympiques"
    )
    moyenne = df["croissance_pct"].mean()

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
        title="Effet Paris 2024 : médailles françaises vs croissance des licences (2023-2025)",
        labels={
            "total_medailles": "Nombre de médailles françaises (cumul athlètes)",
            "croissance_pct": "Croissance des licences 2023-2025 (%)",
            "nb_athletes": "Athlètes engagés",
            "categorie": "",
        },
        template="plotly_white",
    )
    fig.update_traces(textposition="top center", textfont=dict(size=10), marker=dict(opacity=0.85))
    fig.add_hline(y=0, line_color="lightgray")
    fig.add_hline(
        y=moyenne,
        line_dash="dot",
        line_color="gray",
        annotation_text=f"Moyenne ({moyenne:.1f} %)",
        annotation_position="bottom right",
    )
    fig.update_layout(legend=LEGEND_TOP)
    return fig


def plot_effet_local_base100(
    df_base100,
    nom_sport,
    nom_star,
    annee_ref=2019,
    annee_evenement=2024.5,
    evenement_label="JO Paris 2024",
    annee_evenement2=None,
    evenement_label2=None,
):
    """Compare l'évolution en base 100 entre un territoire cible et le reste de la France."""
    fig = px.line(
        df_base100,
        x="annee",
        y="indice_base_100",
        color="zone",
        markers=True,
        title=f"{nom_sport} ({nom_star}) : évolution des licences en base {annee_ref} = 100",
        labels={
            "annee": "Année",
            "indice_base_100": f"Indice (Base 100 en {annee_ref})",
            "zone": "Territoire",
        },
        template="plotly_white",
    )
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


def plot_carte_croissance_dep(df_croissance, nom_sport, annee_debut=2023, annee_fin=2025):
    """Carte choroplèthe départementale du taux de variation des licences."""
    borne = max(
        abs(df_croissance["taux_croissance"].quantile(0.05)),
        abs(df_croissance["taux_croissance"].quantile(0.95)),
    )

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
            "variation_nette": "Gain net",
        },
        title=f"{nom_sport} : évolution des licences par département ({annee_debut}-{annee_fin})",
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(margin=dict(l=0, r=0, t=50, b=0))
    return fig


def plot_effet_age(df_ages, nom_sport, nom_star, annee_ref=2019):
    """Évolution en base 100 des licences par tranche d'âge."""
    df = df_ages.sort_values(["tranche_age", "annee"]).copy()
    ref = df[df["annee"] == annee_ref].set_index("tranche_age")["licences"]
    df["indice_base_100"] = df["licences"] / df["tranche_age"].map(ref) * 100

    fig = px.line(
        df,
        x="annee",
        y="indice_base_100",
        color="tranche_age",
        category_orders={"tranche_age": ["Moins de 10 ans", "10 à 14 ans", "15 à 19 ans", "20 ans et plus"]},
        markers=True,
        title=f"{nom_sport} ({nom_star}) : évolution par tranche d'âge (Base {annee_ref} = 100)",
        labels={
            "annee": "Année",
            "indice_base_100": f"Indice (Base 100 en {annee_ref})",
            "tranche_age": "Tranche d'âge",
        },
        template="plotly_white",
    )
    fig.add_hline(y=100, line_dash="dot", line_color="gray")
    fig.add_vline(x=2024, line_dash="dash", line_color="#d62728", annotation_text="JO Paris 2024")
    fig.update_traces(line=dict(width=3))
    return fig


def plot_effet_genre(df_genre, nom_sport, nom_star, annee_ref=2019):
    """Compare en base 100 la dynamique des licenciées femmes et des licenciés hommes."""
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
            "indice": f"Indice (Base 100 en {annee_ref})",
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


def plot_comparaison_federations_base100(
    df_comp,
    annee_ref=2023,
    titre="Comparaison de deux fédérations (Base 100)",
    couleurs=None,
):
    """Compare côte à côte l'évolution totale et féminine de plusieurs fédérations."""
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(
            f"Total des licenciés (Base 100 en {annee_ref})",
            f"Licenciées femmes uniquement (Base 100 en {annee_ref})",
        ),
    )

    for fed, groupe in df_comp.groupby("federation"):
        line_cfg = dict(width=3, color=couleurs.get(fed)) if couleurs else dict(width=3)
        fig.add_trace(
            go.Scatter(
                x=groupe["annee"],
                y=groupe["indice_total"],
                mode="lines+markers",
                name=fed,
                legendgroup=fed,
                line=line_cfg,
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
                line=line_cfg,
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


def plot_comparaison_lebrun_ferrand_prevot(df_comp, annee_ref=2023):
    """Compare l'évolution totale et féminine de la FFTT et de la FFC."""
    return plot_comparaison_federations_base100(
        df_comp,
        annee_ref=annee_ref,
        titre="Comparaison directe : Frères Lebrun (FFTT) vs Pauline Ferrand-Prévot (FFC)",
        couleurs={
            "Tennis de table (Frères Lebrun)": "#1f77b4",
            "Cyclisme (P. Ferrand-Prévot)": "#e377c2",
        },
    )


def plot_superposition_genre_role_models(df_comp, annee_ref=2023):
    """Superpose les courbes Femmes (plein) et Hommes (pointillés) de deux sports."""
    fig = go.Figure()
    styles = {
        "Tennis de table (Frères Lebrun)": ("#1f77b4", "Tennis de table (Lebrun)"),
        "Cyclisme (P. Ferrand-Prévot)": ("#e377c2", "Cyclisme (Ferrand-Prévot)"),
    }

    for fed, groupe in df_comp.groupby("federation"):
        groupe = groupe.sort_values("annee")
        couleur, nom = styles.get(fed, (None, fed))

        fig.add_trace(
            go.Scatter(
                x=groupe["annee"],
                y=groupe["indice_femmes"],
                mode="lines+markers",
                name=f"{nom} - Femmes",
                line=dict(color=couleur, width=3.5),
                marker=dict(size=7),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=groupe["annee"],
                y=groupe["indice_hommes"],
                mode="lines+markers",
                name=f"{nom} - Hommes",
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
        title=f"Identification genrée : Femmes vs Hommes selon le rôle modèle (Base 100 en {annee_ref})",
        xaxis_title="Année",
        yaxis_title=f"Indice (Base 100 en {annee_ref})",
        template="plotly_white",
        hovermode="x unified",
        legend=LEGEND_TOP,
    )
    return fig


def plot_dumbbell_genre_role_models(
    df_licences,
    sports_stars,
    annee_debut=2023,
    annee_fin=2025,
    col_fed="code_fed",
):
    """Graphique en haltères comparant la croissance Femmes vs Hommes par discipline."""
    sub = df_licences[
        df_licences["annee"].isin([annee_debut, annee_fin])
        & df_licences[col_fed].isin(sports_stars.values())
    ]
    agg = sub.groupby([col_fed, "annee"], as_index=False)[["licences_f", "licences_h"]].sum()

    lignes = []
    for label, code in sports_stars.items():
        s = agg[agg[col_fed] == str(code)].set_index("annee")
        if annee_debut not in s.index or annee_fin not in s.index:
            continue
        f_deb, f_fin = s.loc[annee_debut, "licences_f"], s.loc[annee_fin, "licences_f"]
        h_deb, h_fin = s.loc[annee_debut, "licences_h"], s.loc[annee_fin, "licences_h"]
        if f_deb > 0 and h_deb > 0:
            lignes.append({
                "sport": label,
                "evol_f": (f_fin / f_deb - 1) * 100,
                "evol_h": (h_fin / h_deb - 1) * 100,
            })

    df_plot = pd.DataFrame(lignes).sort_values("evol_f")
    x_seg, y_seg = [], []
    for _, row in df_plot.iterrows():
        x_seg.extend([row["evol_f"], row["evol_h"], None])
        y_seg.extend([row["sport"], row["sport"], None])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x_seg,
            y=y_seg,
            mode="lines",
            line=dict(color="#bdbdbd", width=3),
            showlegend=False,
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df_plot["evol_f"],
            y=df_plot["sport"],
            mode="markers+text",
            name="Femmes",
            marker=dict(color="#e377c2", size=14),
            text=[f"{v:+.1f} %" for v in df_plot["evol_f"]],
            textposition="top center",
            hovertemplate="%{y}<br>Femmes : %{x:+.1f} %<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df_plot["evol_h"],
            y=df_plot["sport"],
            mode="markers+text",
            name="Hommes",
            marker=dict(color="#1f77b4", size=13, symbol="diamond"),
            text=[f"{v:+.1f} %" for v in df_plot["evol_h"]],
            textposition="bottom center",
            hovertemplate="%{y}<br>Hommes : %{x:+.1f} %<extra></extra>",
        )
    )

    fig.add_vline(x=0, line_dash="dot", line_color="gray")
    fig.update_layout(
        title=f"Identification genrée : croissance Femmes vs Hommes ({annee_debut}-{annee_fin})",
        xaxis_title=f"Variation des licences {annee_debut}-{annee_fin} (%)",
        yaxis_title="",
        template="plotly_white",
        height=440,
        legend=LEGEND_TOP,
    )
    return fig


def plot_effet_communal_compare(df_com_tt, df_com_velo):
    """Compare la diffusion communale Montpellier vs Hérault et Reims vs Marne."""
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
        title="Diffusion infra-départementale : ville d'entraînement vs département (Base 2019 = 100)",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.08, xanchor="right", x=1),
    )
    fig.update_yaxes(title_text="Indice (Base 100 en 2019)", row=1, col=1)
    return fig


def plot_comparaison_longue_base100(df_histo, feds, annee_ref=2008):
    """Trajectoire longue (2002-2025) de plusieurs fédérations en base 100."""
    lignes = []
    for label, code in feds.items():
        sub = df_histo[df_histo["code_fed"] == str(code)].sort_values("annee").copy()
        if sub.empty or annee_ref not in sub["annee"].values:
            continue
        val_ref = sub.loc[sub["annee"] == annee_ref, "licences"].iloc[0]
        sub["federation"] = label
        sub["indice"] = sub["licences"] / val_ref * 100
        lignes.append(sub)

    df_plot = pd.concat(lignes, ignore_index=True)

    fig = px.line(
        df_plot,
        x="annee",
        y="indice",
        color="federation",
        markers=True,
        title=f"Révélation vs icône installée : trajectoire historique (Base 100 en {annee_ref})",
        labels={"annee": "Année", "indice": f"Indice (Base 100 en {annee_ref})", "federation": "Fédération"},
        template="plotly_white",
    )
    fig.update_traces(line=dict(width=2.8))
    fig.add_hline(y=100, line_dash="dot", line_color="gray")

    for annee_jo, ville in OLYMPIADES:
        if annee_jo >= 2008:
            label_jo = "Pékin (1er podium Riner)" if annee_jo == 2008 else ville
            fig.add_vline(
                x=annee_jo,
                line_dash="dash",
                line_color="#d62728" if annee_jo == 2024 else "gray",
                annotation_text=label_jo,
                annotation_position="top left",
            )

    fig.update_layout(legend=LEGEND_TOP)
    return fig


def plot_evolution_passsport_sports(df_pass_dep, feds, campagne_ref=2023):
    """Évolution des recours Pass'Sport en base 100 par discipline."""
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
        sub["indice"] = sub["nb_passsport"] / val_ref * 100
        lignes.append(sub)

    df_plot = pd.concat(lignes, ignore_index=True)
    campagnes = sorted(df_plot["campagne"].unique())

    fig = px.line(
        df_plot,
        x="campagne",
        y="indice",
        color="sport",
        markers=True,
        title=f"Recours au Pass'Sport par discipline (Base 100 = saison {campagne_ref}/{str(campagne_ref + 1)[-2:]})",
        labels={"campagne": "Saison sportive", "indice": "Indice des activations (Base 100)", "sport": "Discipline"},
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
        tickvals=campagnes,
        ticktext=[f"{c}/{str(c + 1)[-2:]}" for c in campagnes],
    )
    fig.update_layout(legend=LEGEND_TOP)
    return fig


def plot_rentree_hebdo_passsport(
    df_pass_hebdo,
    code_fed="124",
    nom_sport="Tennis de table (FFTT)",
    campagnes=(2023, 2024),
):
    """Rythme hebdomadaire des activations Pass'Sport à la rentrée."""
    sub = df_pass_hebdo[
        (df_pass_hebdo["code_fed"] == str(code_fed))
        & df_pass_hebdo["campagne"].isin(campagnes)
        & df_pass_hebdo["semaine"].between(33, 48)
    ]
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
            "semaine": "Numéro de semaine (35 = fin août)",
            "nb_passsport": "Pass'Sport activés",
        },
        color_discrete_map={
            "Rentrée 2023/24 (Avant JO)": "#7f7f7f",
            "Rentrée 2024/25 (Post-JO Paris 2024)": "#1f77b4",
        },
        template="plotly_white",
    )
    fig.update_layout(legend=LEGEND_TOP)
    return fig