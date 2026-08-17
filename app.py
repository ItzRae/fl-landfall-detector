import matplotlib as mpl
import matplotlib.colors as colors
import pandas as pd
import pydeck as pdk
import streamlit as st

DATA_PATH = "output/florida_hurricane_landfalls.csv"

def wind_to_color(wind, normalizer, colormap):
    """Map wind speed to an RGBA color for the landfall map"""

    r, g, b, _ = colormap(normalizer(wind))

    return [
        int(r * 255),
        int(g * 255),
        int(b * 255),
        220,
    ]


st.set_page_config(
    page_title="Florida Hurricane Landfalls",
    layout="wide",
)

st.title("Florida Hurricane Landfalls")
st.caption("Independent landfall detection from Atlantic HURDAT2 best-track data.")
st.divider()

df = pd.read_csv(
    DATA_PATH,
    parse_dates=["landfall_datetime"],
)

# Filters section
st.sidebar.header("Filters")

dataset_min_year = int(
    df["landfall_datetime"].dt.year.min()
)
dataset_max_year = int(
    df["landfall_datetime"].dt.year.max()
)

year_range = st.sidebar.slider(
    "Year range",
    min_value=dataset_min_year,
    max_value=dataset_max_year,
    value=(dataset_min_year, dataset_max_year),
)

storm_options = [
    "All",
    *sorted(df["storm_name"].unique()),
]

selected_storm = st.sidebar.selectbox(
    "Storm",
    storm_options,
)

minimum_wind = st.sidebar.slider(
    "Minimum wind speed (kt)",
    min_value=int(df["max_wind_kt"].min()),
    max_value=int(df["max_wind_kt"].max()),
    value=int(df["max_wind_kt"].min()),
)

filtered_df = df[
    df["landfall_datetime"].dt.year.between(
        year_range[0],
        year_range[1],
    )
    & (df["max_wind_kt"] >= minimum_wind)
].copy()

if selected_storm != "All":
    filtered_df = filtered_df[
        filtered_df["storm_name"] == selected_storm
    ]

# Summary metrics  =============================

metric_col1, metric_col2, metric_col3 = st.columns(3)

with metric_col1:
    st.metric(
        "Detected landfalls",
        len(filtered_df),
    )

with metric_col2:
    st.metric(
        "Years",
        f"{year_range[0]}–{year_range[1]}",
    )

with metric_col3:
    max_filtered_wind = filtered_df["max_wind_kt"].max()

    st.metric(
        "Max wind",
        (
            f"{max_filtered_wind:.1f} kt"
            if not filtered_df.empty
            else "—"
        ),
    )

st.divider()

# Interactive landfall map =============================

st.subheader("Landfall Map")
st.caption(
    "Marker color represents estimated sustained wind at landfall."
)

map_df = filtered_df[
    [
        "latitude",
        "longitude",
        "storm_id",
        "storm_name",
        "landfall_datetime",
        "max_wind_kt",
    ]
].copy()

map_df["landfall_date"] = (
    map_df["landfall_datetime"]
    .dt.strftime("%b %d, %Y")
)

map_df["landfall_time"] = (
    map_df["landfall_datetime"]
    .dt.strftime("%-I:%M %p")
)

map_df["max_wind_kt"] = (
    map_df["max_wind_kt"].round(2)
)


if not map_df.empty:
    map_min_wind = map_df["max_wind_kt"].min()
    map_max_wind = map_df["max_wind_kt"].max()

    # Avoid a zero-width normalization range when all visible
    # landfalls have the same wind speed
    if map_min_wind == map_max_wind:
        map_max_wind += 1

    normalizer = colors.Normalize(
        vmin=map_min_wind,
        vmax=map_max_wind,
    )

    colormap = mpl.colormaps["YlOrRd"]

    map_df["color"] = map_df["max_wind_kt"].apply(
        lambda wind: wind_to_color(
            wind,
            normalizer,
            colormap,
        )
    )
     # Add ID of storm to display if it is UNNAMED 
    map_df["storm_label"] = map_df.apply(
        lambda row: (
            f"UNNAMED ({row['storm_id']})"
            if row["storm_name"] == "UNNAMED"
            else row["storm_name"]
        ),
        axis=1,
    )

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df,
        get_position="[longitude, latitude]",
        get_radius=3000,
        radius_min_pixels=4,
        radius_max_pixels=10,
        get_fill_color="color",
        get_line_color=[255, 255, 255, 180],
        line_width_min_pixels=1,
        stroked=True,
        filled=True,
        pickable=True,
    )

    st.markdown(
        f"""
        <div style="margin-bottom:8px;">
            <div style="
                width:260px;
                height:12px;
                border-radius:6px;
                background:linear-gradient(
                    to right,
                    #ffffcc,
                    #fd8d3c,
                    #800026
                );
            "></div>
            <div style="
                width:260px;
                display:flex;
                justify-content:space-between;
                font-size:12px;
            ">
                <span>{map_min_wind:.0f} kt</span>
                <span>{map_max_wind:.0f} kt</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    view_state = pdk.ViewState(
        latitude=27.7,
        longitude=-82.0,
        zoom=5.4,
    )

    tooltip = {
        "html": """
            <b>{storm_label}</b><br/>
            {landfall_date}<br/>
            ~{landfall_time}<br/>
            Wind: {max_wind_kt} kt
        """
    }

    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style="light",
    )

    st.pydeck_chart(
        deck,
        width="stretch",
    )

else:
    st.info("No landfalls match the selected filters.")

# Results table  ============================

st.subheader("Landfall Table Results")
st.caption("All detected hurricanes that made landfall in Florida since 1900")

show_coordinates = st.checkbox(
    "Show latitude / longitude",
    value=False,
)

display_columns = [
    "storm_name",
    "storm_id",
    "landfall_datetime",
    "max_wind_kt",
]

display_df = filtered_df[display_columns].copy()

display_df["landfall_datetime"] = (
    display_df["landfall_datetime"]
    .dt.strftime("%b %d, %Y")
)

if show_coordinates:
    display_columns.extend(
        [
            "latitude",
            "longitude",
        ]
    )

display_df["max_wind_kt"] = (
    display_df["max_wind_kt"].round(1)
)

display_df = display_df.rename(
    columns={
        "storm_name": "Storm Name",
        "storm_id": "Storm ID",
        "landfall_datetime": "Landfall Date",
        "max_wind_kt": "Max Wind (kt)",
        "latitude": "Latitude",
        "longitude": "Longitude",
    }
)

st.dataframe(
    display_df,
    width="stretch",
    height=650,
    hide_index=True,
)