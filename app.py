import plotly.graph_objs as go
import dash
from dash import dcc, html, State, Patch
from dash.dependencies import Input, Output
import dash_player as dp
import base64
import numpy as np
import dash_dangerously_set_inner_html
import sys
import os
import pickle
import shutil


from interview_transcriber.speaker_identifier_with_embeddings import identify_speakers

if len(sys.argv) > 2:
    audio_file_path = sys.argv[1]
    language = sys.argv[2]
else:
    print("usage: python app.py path/to/audio/file language")
    sys.exit(1)


def load_or_identify_speakers(audio_file_path):
    # Construct the path for the cached file
    cache_file_path = audio_file_path + ".datacache.pickle"

    # Check if the cached file exists
    if os.path.exists(cache_file_path):
        # Load the cached data
        with open(cache_file_path, 'rb') as cache_file:
            subtitle_data, embeddings, speaker_labels, k, kluster_labels, EMBEDDINGS_UMAP = pickle.load(cache_file)
        print("Loaded data from cache.")
    else:
        # Run the function to identify speakers and generate data
        subtitle_data, embeddings, speaker_labels, k, kluster_labels, EMBEDDINGS_UMAP = identify_speakers(audio_file_path)

        # Save the data to a cache file for future use
        with open(cache_file_path, 'wb') as cache_file:
            pickle.dump((subtitle_data, embeddings, speaker_labels, k, kluster_labels, EMBEDDINGS_UMAP), cache_file)
        print("Processed data and saved to cache.")

    for s in subtitle_data:
        source_path = s["clip"]
        destination =  "assets/" + source_path
        os.makedirs(os.path.dirname(destination), exist_ok=True)  # create the directory if it doesn't exist
        shutil.copy(source_path, destination)  # copy the file to the destination

    return subtitle_data, embeddings, speaker_labels, k, kluster_labels, EMBEDDINGS_UMAP


audio_clips, embeddings, speaker_labels, k, kluster_labels, EMBEDDINGS_UMAP = load_or_identify_speakers(audio_file_path)


HEIGHT = 300
margin = dict(l=60, r=20, t=20, b=50, pad=0)

fig_settings = {
    "height": HEIGHT,  #
    # "width": HEIGHT,
    "paper_bgcolor": "rgba(255, 255, 255, 0)",
    "margin": margin,
    "legend": dict(
        x=1, y=1,
        xanchor="right",
        yanchor="top",
        bgcolor="rgba(255, 255, 255, 0.5)",
        font=dict(size=14),
        itemwidth=30,
        tracegroupgap=10,
    ),
    "font": dict(size=14),
    "font_family": "Verdana",
    "title": dict(font=dict(size=14)),
}


# UMAP scatter figure
def get_scatter_figure():

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=EMBEDDINGS_UMAP[:, 0],
            y=EMBEDDINGS_UMAP[:, 1],
            hovertext=[str(i) for i in np.arange(EMBEDDINGS_UMAP.shape[0])],
            hoverinfo="text",
            mode='markers',
            marker=dict(
                size=10,
                opacity=0.8,
                # colorbar={'thickness': 20}
            ),
            showlegend=False)
    )
    fig.update_xaxes(showticklabels=False, automargin=False),
    fig.update_yaxes(showticklabels=False, automargin=False),
    fig.update_layout(fig_settings, dragmode="lasso")
    return fig

app = dash.Dash(__name__) 

# App layout
app.layout = html.Div([
    html.Div([  # Row
        html.Div([  # Column 1: Graph
            dcc.Graph(
                id='scatter-plot',
                config={'displayModeBar': False},
                figure=get_scatter_figure()
            )
        ], style={'width': '50%', 'display': 'inline-block', 'height': f'{HEIGHT}px'}),
        html.Div([  # Column 2: Abstract
            html.Div(id='speaker-clip-text', children="", style={'overflowY': 'scroll', 'height': f'{HEIGHT-50}px', 'vertical-align': 'top'}),

        ], style={'width': '50%', 'display': 'inline-block', 'vertical-align': 'top'})
    ]),   

    html.Div([  # Row
        html.Div([  # Column 1: Graph
            html.Div(id='bottom-ui1', children="", style={'overflowY': 'scroll', 'height': f'{HEIGHT-50}px', 'vertical-align': 'top', 'position': 'absolute', 'top': '0'}),
            html.Div(id='bottom-ui2', children="", style={'overflowY': 'scroll', 'height': f'{HEIGHT-50}px', 'vertical-align': 'top', 'position': 'absolute', 'top': '0'})        
        ], style={'width': '50%', 'display': 'inline-block', 'height': f'{HEIGHT}px', "position": "relative"}),
        html.Div([  # Column 2: 
            html.H2(children="Transcript"),
            html.Div(id='transcript', children="", style={'overflowY': 'scroll', 'height': f'{HEIGHT-50}px', 'vertical-align': 'top'})
        ], style={'width': '50%', 'display': 'inline-block', 'vertical-align': 'top'}) 
    ]),    

], style={'backgroundColor':'white'})

@app.callback(
    Output('speaker-clip-text', 'children'),
    Input('scatter-plot', 'hoverData')
)
def on_hover(hover_data):

    if hover_data is None:
        return "Hover over a point to see the transcript."

    # Get the index of the hovered point
    point_index = hover_data['points'][0]['pointIndex']


    child_html = [
        html.H3(f"Hello there {point_index}"), # audio_clips
        html.P([html.Strong(f"{speaker_labels[point_index]}:"), f"{audio_clips[point_index]['text']}" ])

    ]

    return child_html


@app.callback(
    Output('bottom-ui1', 'children',  allow_duplicate=True,),
    Input("scatter-plot", "selectedData"),
    prevent_initial_call=True

)
def on_selection(select_data):
    print(select_data)

    child_html = html.Div([  # Column 1: Graph

        html.H3(f"Name the speakers"), # audio_clips

        html.Div([ # Row
            html.Div([ # Text input field
                dcc.Input(
                    id='name-input', 
                    type='text', 
                    placeholder='Enter name...', 
                ),
            ], style={'width': '80%', 'display': 'inline-block'}),
            html.Div([ # Submit button
                html.Button(
                    'Submit', 
                    id='submit-button', 
                    n_clicks=0,
                ),
            ], style={'width': '20%', 'display': 'inline-block'}),
        ], style={'width': '100%', 'height': '30px'}),


    ], style={'width': '500px', 'margin-left': '50px'}),


    return child_html

@app.callback(
    Output('bottom-ui1', 'children',  allow_duplicate=True),
    Input('scatter-plot', 'clickData'),
    prevent_initial_call=True

) 
def on_click(click_data):

    if click_data is None:
        return ""

    # Get the index of the hovered point
    point_index = click_data['points'][0]['pointIndex']
    media_url = app.get_asset_url(
        audio_clips[point_index]['clip']
    )
    print(point_index)
    encoded_sound = "data:audio/mp3;base64," + base64.b64encode(open(audio_clips[point_index]['clip'], 'rb').read()).decode('utf-8')


    child_html = [
        html.H3(f"Listen to {point_index}"), # audio_clips

        dash_dangerously_set_inner_html.DangerouslySetInnerHTML(f'''
            <div id="audiodiv" >
                <audio id="audio_player" src="{encoded_sound}"  controls="controls" autobuffer="autobuffer" autoplay="autoplay">
                </audio>
            </div>
        '''),                          
        html.P([html.Strong("Clip:"), f"{media_url}" ]),
        html.P([html.Strong("Text:"), f"{audio_clips[point_index]['text']}" ]),
    ]

    return child_html
"""
@app.callback(
    Output('bottom-ui1', 'children',  allow_duplicate=True),
    Input("name-input", "value"),
    Input("scatter-plot", "selectedData"),

    prevent_initial_call=True

) 
def on_click_name(new_name, click_data):
    print(new_name, click_data)
    return []"""

app.run_server(debug=True)