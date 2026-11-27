import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

pio.templates.default = "plotly_white"

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


def plot_boxplot_dispersion_departementale(
    df_licences, feds, annee_debut=2023, annee_fin=2025, col_fed="code_fed"
):
    """Distribution des croissances départementales entre deux années."""
    sub = df_licences[
        df_licences["annee"].isin([annee_debut, annee_fin])
        & df_licences[col_fed].isin(feds.values())
        & (df_licences["departement"] != "NR")
    ]

    piv = sub.groupby([col_fed, "departement", "annee"])["licences"].sum().unstack("annee").dropna()
    piv = piv.rename(columns={annee_debut: "lic_deb", annee_fin: "lic_fin"}).reset_index()
    piv = piv[piv["lic_deb"] >= 50].copy()

    piv["variation_pct"] = (piv["lic_fin"] / piv["lic_deb"] - 1) * 100
    piv["sport"] = piv[col_fed].astype(str).map({str(v): k for k, v in feds.items()})
    ordre = piv.groupby("sport")["variation_pct"].median().sort_values(ascending=False).index

    fig = px.box(
        piv,
        x="sport",
        y="variation_pct",
        color="sport",
        points="all",
        category_orders={"sport": list(ordre)},
        hover_data=["departement", "lic_deb", "lic_fin"],
        title=f"Croissances départementales par discipline ({annee_debut}-{annee_fin})",
        labels={"sport": "Discipline", "variation_pct": "Variation (%)"},
    )
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.update_layout(showlegend=False)
    return fig


def plot_historique_olympique(df_histo, code_fed="124", nom_sport="Tennis de table"):
    """Evolution nationale des licences depuis 2002 avec repères olympiques."""
    df_sub = df_histo[df_histo["code_fed"] == str(code_fed)].sort_values("annee")

    fig = px.line(
        df_sub,
        x="annee",
        y="licences",
        markers=True,
        title=f"{nom_sport} : évolution des licences et cycles olympiques",
        labels={"annee": "Année", "licences": "Licenciés"},
    )
    fig.update_traces(line_width=3)

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
    """Nuage de points entre médailles françaises et croissance des licences."""
    df = df_croise.copy()
    df["label"] = (
        df["nom_fed"]
        .str.replace(r"^Fédération Française (de |d'|des )", "", regex=True)
        .str.replace(r"(, Jujitsu.*| et Disciplines.*| et Sports de Pagaie)$", "", regex=True)
    )
    df["groupe"] = df["code_fed"].astype(str).apply(
        lambda c: "Tennis de table" if c == "124" else "Autres sports"
    )
    moyenne = df["croissance_pct"].mean()

    fig = px.scatter(
        df,
        x="total_medailles",
        y="croissance_pct",
        size="nb_athletes",
        color="groupe",
        color_discrete_map={"Tennis de table": "#d62728", "Autres sports": "#1f77b4"},
        text="label",
        hover_name="nom_fed",
        hover_data=["disciplines_jo", "gain_net", "medailles_or"],
        title="Paris 2024 : médailles françaises vs croissance des licences (2023-2025)",
        labels={
            "total_medailles": "Médailles françaises (cumul athlètes)",
            "croissance_pct": "Croissance 2023-2025 (%)",
            "groupe": "",
        },
    )
    fig.update_traces(textposition="top center", textfont_size=10)
    fig.add_hline(y=0, line_color="lightgray")
    fig.add_hline(y=moyenne, line_dash="dot", line_color="gray", annotation_text=f"Moyenne ({moyenne:.1f} %)")
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
    """Courbes en base 100 comparant un département cible et le reste de la France."""
    fig = px.line(
        df_base100,
        x="annee",
        y="indice_base_100",
        color="zone",
        markers=True,
        title=f"{nom_sport} ({nom_star}) : licences en base {annee_ref} = 100",
        labels={"annee": "Année", "indice_base_100": f"Indice (base {annee_ref})", "zone": "Zone"},
    )
    fig.update_traces(line_width=3)
    fig.add_hline(y=100, line_dash="dot", line_color="gray")
    fig.add_vline(x=annee_evenement, line_dash="dash", line_color="#d62728", annotation_text=evenement_label)
    if annee_evenement2 is not None and evenement_label2 is not None:
        fig.add_vline(x=annee_evenement2, line_dash="dash", line_color="#d62728", annotation_text=evenement_label2)
    return fig


def plot_carte_croissance_dep(df_croissance, nom_sport, annee_debut=2023, annee_fin=2025):
    """Carte départementale de l'évolution des licences."""
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
        hover_data=["departement", "variation_nette"],
        labels={"taux_croissance": "Variation (%)", "variation_nette": "Gain net"},
        title=f"{nom_sport} : évolution par département ({annee_debut}-{annee_fin})",
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(margin=dict(l=0, r=0, t=50, b=0))
    return fig


def plot_effet_age(df_ages, nom_sport, nom_star, annee_ref=2019):
    """Evolution en base 100 des licences par tranche d'âge."""
    df = df_ages.sort_values(["tranche_age", "annee"]).copy()
    ref = df[df["annee"] == annee_ref].set_index("tranche_age")["licences"]
    df["indice"] = df["licences"] / df["tranche_age"].map(ref) * 100

    fig = px.line(
        df,
        x="annee",
        y="indice",
        color="tranche_age",
        category_orders={"tranche_age": ["Moins de 10 ans", "10 à 14 ans", "15 à 19 ans", "20 ans et plus"]},
        markers=True,
        title=f"{nom_sport} ({nom_star}) : licences par tranche d'âge (base {annee_ref})",
        labels={"annee": "Année", "indice": f"Indice (base {annee_ref})", "tranche_age": "Age"},
    )
    fig.update_traces(line_width=3)
    fig.add_hline(y=100, line_dash="dot", line_color="gray")
    fig.add_vline(x=2024, line_dash="dash", line_color="#d62728", annotation_text="JO Paris 2024")
    return fig


def plot_effet_genre(df_genre, nom_sport, nom_star, annee_ref=2019):
    """Compare en base 100 les licences femmes et hommes."""
    df_long = df_genre.melt(
        id_vars="annee", value_vars=["indice_f", "indice_h"], var_name="sexe", value_name="indice"
    )
    df_long["sexe"] = df_long["sexe"].map({"indice_f": "Femmes", "indice_h": "Hommes"})

    fig = px.line(
        df_long,
        x="annee",
        y="indice",
        color="sexe",
        markers=True,
        color_discrete_map={"Femmes": "#e377c2", "Hommes": "#1f77b4"},
        title=f"{nom_sport} ({nom_star}) : Femmes vs Hommes (base {annee_ref})",
        labels={"annee": "Année", "indice": f"Indice (base {annee_ref})", "sexe": "Genre"},
    )
    fig.update_traces(line_width=3)
    fig.add_hline(y=100, line_dash="dot", line_color="gray")
    fig.add_vline(x=2024, line_dash="dash", line_color="#d62728", annotation_text="JO Paris 2024")
    return fig


def plot_comparaison_federations_base100(
    df_comp, annee_ref=2023, titre="Comparaison de deux fédérations (Base 100)", couleurs=None
):
    """Compare l'évolution totale et féminine de plusieurs fédérations."""
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(f"Total (base {annee_ref})", f"Femmes (base {annee_ref})"),
    )

    for fed, groupe in df_comp.groupby("federation"):
        style = dict(width=3, color=couleurs.get(fed)) if couleurs else dict(width=3)
        fig.add_trace(
            go.Scatter(x=groupe["annee"], y=groupe["indice_total"], mode="lines+markers", name=fed, line=style),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(x=groupe["annee"], y=groupe["indice_femmes"], mode="lines+markers", name=fed, showlegend=False, line=style),
            row=1, col=2,
        )

    for col in (1, 2):
        fig.add_hline(y=100, line_dash="dot", line_color="gray", row=1, col=col)
        fig.add_vline(x=2024, line_dash="dash", line_color="#d62728", row=1, col=col)

    fig.update_layout(title=titre, legend_orientation="h")
    fig.update_yaxes(title_text=f"Indice (base {annee_ref})", row=1, col=1)
    return fig


def plot_comparaison_lebrun_ferrand_prevot(df_comp, annee_ref=2023):
    """Compare la FFTT (Lebrun) et la FFC (Ferrand-Prévot)."""
    return plot_comparaison_federations_base100(
        df_comp,
        annee_ref=annee_ref,
        titre="Frères Lebrun (FFTT) vs Pauline Ferrand-Prévot (FFC)",
        couleurs={
            "Tennis de table (Frères Lebrun)": "#1f77b4",
            "Cyclisme (P. Ferrand-Prévot)": "#e377c2",
        },
    )


def plot_superposition_genre_role_models(df_comp, annee_ref=2023):
    """Superpose les évolutions femmes et hommes de deux disciplines."""
    fig = go.Figure()
    couleurs = {
        "Tennis de table (Frères Lebrun)": "#1f77b4",
        "Cyclisme (P. Ferrand-Prévot)": "#e377c2",
    }

    for fed, grp in df_comp.groupby("federation"):
        grp = grp.sort_values("annee")
        c = couleurs.get(fed)
        fig.add_trace(go.Scatter(
            x=grp["annee"], y=grp["indice_femmes"], mode="lines+markers",
            name=f"{fed} (F)", line=dict(color=c, width=3),
        ))
        fig.add_trace(go.Scatter(
            x=grp["annee"], y=grp["indice_hommes"], mode="lines+markers",
            name=f"{fed} (H)", line=dict(color=c, width=2, dash="dash"), opacity=0.7,
        ))

    fig.add_hline(y=100, line_dash="dot", line_color="gray")
    fig.add_vline(x=2024, line_dash="dash", line_color="#d62728", annotation_text="JO Paris 2024")
    fig.update_layout(
        title=f"Femmes vs Hommes selon le rôle modèle (base {annee_ref})",
        xaxis_title="Année",
        yaxis_title=f"Indice (base {annee_ref})",
        legend_orientation="h",
    )
    return fig


def plot_dumbbell_genre_role_models(
    df_licences, sports_stars, annee_debut=2023, annee_fin=2025, col_fed="code_fed"
):
    """Compare la croissance femmes vs hommes sur plusieurs disciplines."""
    sub = df_licences[
        df_licences["annee"].isin([annee_debut, annee_fin])
        & df_licences[col_fed].isin(sports_stars.values())
    ]
    agg = sub.groupby([col_fed, "annee"], as_index=False)[["licences_f", "licences_h"]].sum()

    rows = []
    for label, code in sports_stars.items():
        s = agg[agg[col_fed] == str(code)].set_index("annee")
        if annee_debut in s.index and annee_fin in s.index:
            f0, f1 = s.loc[annee_debut, "licences_f"], s.loc[annee_fin, "licences_f"]
            h0, h1 = s.loc[annee_debut, "licences_h"], s.loc[annee_fin, "licences_h"]
            if f0 > 0 and h0 > 0:
                rows.append({"sport": label, "evol_f": (f1 / f0 - 1) * 100, "evol_h": (h1 / h0 - 1) * 100})

    df_plot = pd.DataFrame(rows).sort_values("evol_f")

    fig = go.Figure()
    for _, row in df_plot.iterrows():
        fig.add_trace(go.Scatter(
            x=[row["evol_f"], row["evol_h"]], y=[row["sport"], row["sport"]],
            mode="lines", line=dict(color="#bdbdbd", width=3), showlegend=False, hoverinfo="skip",
        ))

    fig.add_trace(go.Scatter(
        x=df_plot["evol_f"], y=df_plot["sport"], mode="markers+text", name="Femmes",
        marker=dict(color="#e377c2", size=12),
        text=[f"{v:+.1f}%" for v in df_plot["evol_f"]], textposition="top center",
    ))
    fig.add_trace(go.Scatter(
        x=df_plot["evol_h"], y=df_plot["sport"], mode="markers+text", name="Hommes",
        marker=dict(color="#1f77b4", size=12, symbol="diamond"),
        text=[f"{v:+.1f}%" for v in df_plot["evol_h"]], textposition="bottom center",
    ))

    fig.add_vline(x=0, line_dash="dot", line_color="gray")
    fig.update_layout(
        title=f"Croissance Femmes vs Hommes ({annee_debut}-{annee_fin})",
        xaxis_title="Variation (%)",
        height=420,
        legend_orientation="h",
    )
    return fig


def plot_effet_communal_compare(df_com_tt, df_com_velo):
    """Compare la diffusion communale Montpellier/Hérault et Reims/Marne."""
    fig = make_subplots(
        rows=1, cols=2, subplot_titles=("Tennis de table : Montpellier vs Hérault", "Cyclisme : Reims vs Marne")
    )

    for col_idx, df_sub in [(1, df_com_tt), (2, df_com_velo)]:
        for i, (terr, grp) in enumerate(df_sub.groupby("territoire")):
            fig.add_trace(
                go.Scatter(
                    x=grp["annee"], y=grp["indice_2019"], mode="lines+markers",
                    name=terr, line=dict(width=3, dash="solid" if i == 0 else "dash"),
                ),
                row=1, col=col_idx,
            )
        fig.add_hline(y=100, line_dash="dot", line_color="gray", row=1, col=col_idx)

    fig.update_layout(title="Ville d'entraînement vs reste du département (base 2019)", legend_orientation="h")
    fig.update_yaxes(title_text="Indice (base 2019)", row=1, col=1)
    return fig


def plot_comparaison_longue_base100(df_histo, feds, annee_ref=2008):
    """Trajectoire longue en base 100 pour plusieurs fédérations."""
    frames = []
    for label, code in feds.items():
        sub = df_histo[df_histo["code_fed"] == str(code)].sort_values("annee").copy()
        if sub.empty or annee_ref not in sub["annee"].values:
            continue
        ref = sub.loc[sub["annee"] == annee_ref, "licences"].iloc[0]
        sub["federation"] = label
        sub["indice"] = sub["licences"] / ref * 100
        frames.append(sub)

    fig = px.line(
        pd.concat(frames, ignore_index=True),
        x="annee",
        y="indice",
        color="federation",
        markers=True,
        title=f"Trajectoire historique comparée (base {annee_ref})",
        labels={"annee": "Année", "indice": f"Indice (base {annee_ref})", "federation": "Fédération"},
    )
    fig.update_traces(line_width=2.5)
    fig.add_hline(y=100, line_dash="dot", line_color="gray")

    for annee_jo, ville in OLYMPIADES:
        if annee_jo >= 2008:
            fig.add_vline(
                x=annee_jo,
                line_dash="dash",
                line_color="#d62728" if annee_jo == 2024 else "gray",
                annotation_text=ville,
                annotation_position="top left",
            )
    return fig


def plot_evolution_passsport_sports(df_pass_dep, feds, campagne_ref=2023):
    """Evolution des activations Pass'Sport en base 100 par discipline."""
    frames = []
    for nom_sport, code in feds.items():
        sub = (
            df_pass_dep[df_pass_dep["code_fed"] == str(code)]
            .groupby("campagne", as_index=False)["nb_passsport"]
            .sum()
            .sort_values("campagne")
        )
        if sub.empty or campagne_ref not in sub["campagne"].values:
            continue
        ref = sub.loc[sub["campagne"] == campagne_ref, "nb_passsport"].iloc[0]
        sub["sport"] = nom_sport
        sub["indice"] = sub["nb_passsport"] / ref * 100
        frames.append(sub)

    df_plot = pd.concat(frames, ignore_index=True)
    campagnes = sorted(df_plot["campagne"].unique())

    fig = px.line(
        df_plot,
        x="campagne",
        y="indice",
        color="sport",
        markers=True,
        title=f"Activations Pass'Sport par discipline (base {campagne_ref})",
        labels={"campagne": "Saison", "indice": "Indice (base 100)", "sport": "Discipline"},
        hover_data=["nb_passsport"],
    )
    fig.update_traces(line_width=3)
    fig.add_hline(y=100, line_dash="dot", line_color="gray")
    fig.add_vline(x=2023.5, line_dash="dash", line_color="#d62728", annotation_text="JO 2024")
    


    fig.update_xaxes(
        tickmode="array",
        tickvals=campagnes,
        ticktext=[f"{c}/{str(c + 1)[-2:]}" for c in campagnes],
    )
    return fig

