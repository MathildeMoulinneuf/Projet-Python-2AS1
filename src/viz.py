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