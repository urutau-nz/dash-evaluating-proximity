import pathlib
import os

import pandas as pd
import numpy as np
import json
import geopandas as gpd

import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
from dash.dependencies import Input, Output, State

amenities = ['hospital','supermarket','school','library']
amenity_names = {'hospital':'Hospitals','school':'Schools','supermarket':'Supermarkets','library':'Libraries'}

# app initialize
app = dash.Dash(
    __name__,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
    ],
)
server = app.server
app.config["suppress_callback_exceptions"] = True

app.title = 'Evaluating proximity'

# mapbox token
mapbox_access_token = open(".mapbox_token").read()

# Load data
blocks_path = './data/block.geojson'
with open(blocks_path) as response:
    blocks = json.load(response)

df_dist = pd.read_csv('./data/distance_to_nearest.csv',dtype={"geoid10": str})
df_dist[amenities] = df_dist[amenities]/1000

destinations = pd.read_csv('./data/destinations.csv')

df_ecdf = pd.read_csv('./data/ecdf.csv')

# Assign color to legend
colors = ['#EA5138','#E4AE36','#1F386B','#507332']
colormap = {}
for ind, amenity in enumerate(amenities):
    colormap[amenity] = colors[ind]

pl_deep=[[0.0, 'rgb(253, 253, 204)'],
         [0.1, 'rgb(201, 235, 177)'],
         [0.2, 'rgb(145, 216, 163)'],
         [0.3, 'rgb(102, 194, 163)'],
         [0.4, 'rgb(81, 168, 162)'],
         [0.5, 'rgb(72, 141, 157)'],
         [0.6, 'rgb(64, 117, 152)'],
         [0.7, 'rgb(61, 90, 146)'],
         [0.8, 'rgb(65, 64, 123)'],
         [0.9, 'rgb(55, 44, 80)'],
         [1.0, 'rgb(39, 26, 44)']]


def build_banner():
    return html.Div(
        id="banner",
        className="banner",
        children=[
            html.Img(src=app.get_asset_url("urutau-logo.png")),
            html.H6("Proximity to urban amenities"),
        ],
    )


def build_graph_title(title):
    return html.P(className="graph-title", children=title)


def generate_ecdf_plot(amenity_select):
    """
    :param amenity_select: the amenity of interest.
    :return: Figure object
    """
    layout = dict(
        xaxis=dict(title="distance to nearest {} (km)".format(amenity_select)),
        yaxis=dict(title="% of residents"),
        dragmode="select",
        clickmode="select",
    )


    data = []
    for amenity in [amenity_select]:
        dff = df_ecdf[df_ecdf.amenity==amenity]
        # add the cdf for that amenity
        new_trace = dict(
            x=dff.distance,
            y=dff.perc,
            maxdisplayed=6,
            opacity = 1,#1 if amenity == amenity_select else 0.5,
            text=dff.amenity,
            mode= 'markers',
            marker_opacity=0.7,
            marker_size=1,
            hovermode='closest',
            hovertemplate = "%{y:.2f}% of residents live within %{x:.1f}km of a %{text} <br>" + "<extra></extra>",
            hoverlabel = dict(font_size=20),
            line=dict(shape="spline", color=colormap[amenity]),
        )
        data.append(new_trace)
    return {"data": data, "layout": layout}


def generate_map(amenity, dff_dest, x_range=None):
    """
    Generate map showing the distance to services and the locations of them

    :param amenity: the service of interest.
    :param dff_dest: the lat and lons of the service.
    :param x_range: distance range to highlight.
    :return: Plotly figure object.
    """

    layout = go.Layout(
        clickmode="none",
        dragmode="zoom",

        showlegend=True,
        autosize=True,
        hovermode="closest",
        margin=dict(l=0, r=0, t=0, b=0),
        mapbox=go.layout.Mapbox(
            accesstoken=mapbox_access_token,
            bearing=0,
            center=go.layout.mapbox.Center(lat = 39.292126, lon = -76.613632),
            pitch=0,
            zoom=10.5,
            style="basic", #"dark", #
        ),
        legend=dict(
            bgcolor="#1f2c56",
            orientation="h",
            font=dict(color="white"),
            x=0,
            y=0,
            yanchor="bottom",
        ),
    )

    if x_range:
        # get the indices of the values within the specified range
        idx = df_dist.index[df_dist[amenity].between(x_range[0],x_range[1], inclusive=True)].tolist()

    data = []
    # choropleth map showing the distance at the block level
    data.append(go.Choroplethmapbox(
        geojson = blocks,
        locations = df_dist['geoid10'].tolist(),
        z = df_dist[amenity].tolist(),
        colorscale = pl_deep,
        colorbar = dict(thickness=20, ticklen=3), zmin=0, zmax=5,
        marker_line_width=0, marker_opacity=0.7,
        visible=True,
        hovertemplate="Distance: %{z:.2f}km<br>" +
                        "<extra></extra>",
        selectedpoints=idx if x_range else df_dist.index.tolist(),
    ))

    # scatterplot of the amenity locations
    data.append(go.Scattermapbox(
        lat=dff_dest["lat"],
        lon=dff_dest["lon"],
        mode="markers",
        marker={"color": colormap[amenity], "size": 9},
        name=amenity_names[amenity],
        hoverinfo="skip", hovertemplate="",
    ))

    return {"data": data, "layout": layout}


app.layout = html.Div(
    children=[
        html.Div(
            id="top-row",
            children=[
                html.Div(
                    className="row",
                    id="top-row-header",
                    children=[
                        html.Div(
                            id="header-container",
                            children=[
                                build_banner(),
                                html.P(
                                    id="instructions",
                                    children=dcc.Markdown('''
                                    Access, and equitable access, to urban amenities is essential
                                    for community cohesion and resilience. Explore access to several amenities
                                    in Baltimore, MD. Zoom into the areas and discover the distance the residents
                                    have to travel to get to these day-to-day facilities. Select a range on the
                                    graph to highlight the areas with that distance on the map. Where should
                                    more amenities be provided?
                                    Work based on [Logan et. al (2019).](http://journals.sagepub.com/doi/10.1177/2399808317736528)
                                    '''),
                                ),
                                build_graph_title("Select Amenity"),
                                dcc.Dropdown(
                                    id="amenity-select",
                                    options=[
                                        {"label": amenity_names[i].upper(), "value": i}
                                        for i in amenities
                                    ],
                                    value=amenities[0],
                                ),
                            ],
                        )
                    ],
                ),
                html.Div(
                    className="row",
                    id="top-row-graphs",
                    children=[
                        # Access map
                        html.Div(
                            id="map-container",
                            children=[
                                build_graph_title("Distance to nearest amenity"),
                                dcc.Graph(
                                    id="map",
                                    figure={
                                        "layout": {
                                            "paper_bgcolor": "#192444",
                                            "plot_bgcolor": "#192444",
                                        }
                                    },
                                    config={"scrollZoom": True, "displayModeBar": True,
                                            "modeBarButtonsToRemove":["lasso2d","select2d"],
                                    },
                                ),
                            ],
                        ),
                        # ECDF
                        html.Div(
                            id="ecdf-container",
                            className="six columns",
                            children=[
                                build_graph_title("How fair is people's access?"),
                                dcc.Graph(id="ecdf",
                                    figure={
                                        "layout": {
                                            'clickmode': 'event+select',
                                            "paper_bgcolor": "#192444",
                                            "plot_bgcolor": "#192444",
                                            'mode': 'markers+lines',

                                        }
                                    },
                                    config={"scrollZoom": True, "displayModeBar": True,
                                            "modeBarButtonsToRemove":['toggleSpikelines','hoverCompareCartesian'],
                                    },
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        html.Div(
            id="footer-row",
            children=[
                html.P(
                    id="footer-text",
                    children=dcc.Markdown('''
                        Thank you to the developers of [Dash and Plotly]
                        (https://plotly.com/dash/), who made this app possible.'''
                    )
                )
            ]
        )
    ]
)


# Update access map
@app.callback(
    Output("map", "figure"),
    [
        Input("amenity-select", "value"),
        # Input("ecdf", "relayoutData"),
        Input("ecdf", "selectedData"),
    ],
)
def update_map(
    amenity_select, ecdf_selectedData
):
    x_range = None
    # subset the desination df
    dff_dest = destinations[destinations.dest_type == amenity_select]

    # Find which one has been triggered
    ctx = dash.callback_context

    prop_id = ""
    prop_type = ""
    if ctx.triggered:
        splitted = ctx.triggered[0]["prop_id"].split(".")
        prop_id = splitted[0]
        prop_type = splitted[1]

    if prop_id == 'ecdf' and prop_type == "selectedData":
        if ecdf_selectedData:
            x_range = ecdf_selectedData['range']['x']
        else:
            x_range=None

    return generate_map(amenity_select, dff_dest, x_range=x_range)


# Update ecdf
@app.callback(
    Output("ecdf", "figure"),
    [
        Input("amenity-select", "value"),
    ],
)
def update_production(amenity_select):
    return generate_ecdf_plot(amenity_select)


# Running the server
if __name__ == "__main__":
    app.run_server(debug=True)
