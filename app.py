import plotly.graph_objs as go
import dash
from dash import dcc, html, State
from dash.dependencies import Input, Output
import base64
import numpy as np
import dash_dangerously_set_inner_html
import sys
import os
import pickle
import shutil
import random

from interview_transcriber.speaker_identifier_with_embeddings import identify_speakers

def parse_arguments():
    if len(sys.argv) < 4:
        print("usage: python app.py path/to/audio/file language --use_local=true/false")
        sys.exit(1)
    audio_file_path = sys.argv[1]
    language = sys.argv[2]
    use_local_flag = sys.argv[3]
    if use_local_flag == "--use_local=true":
        use_local = True
    elif use_local_flag == "--use_local=false":
        use_local = False
    else:
        print("Error: The third argument must be --use_local=true or --use_local=false.")
        sys.exit(1)
    return audio_file_path, language, use_local

audio_file_path, language, use_local = parse_arguments()

def load_or_identify_speakers(audio_file_path, use_local):
    cache_file_path = audio_file_path + ".datacache.pickle"
    if os.path.exists(cache_file_path):
        with open(cache_file_path, 'rb') as cache_file:
            subtitle_data, embeddings, speaker_labels, k, kluster_labels, EMBEDDINGS_UMAP = pickle.load(cache_file)
        print("Loaded data from cache.")
    else:
        subtitle_data, embeddings, speaker_labels, k, kluster_labels, EMBEDDINGS_UMAP = identify_speakers(audio_file_path, use_local=use_local)
        with open(cache_file_path, 'wb') as cache_file:
            pickle.dump((subtitle_data, embeddings, speaker_labels, k, kluster_labels, EMBEDDINGS_UMAP), cache_file)
        print("Processed data and saved to cache.")

    for s in subtitle_data:
        source_path = s["clip"]
        destination = "assets/" + source_path
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.copy(source_path, destination)
    
    return subtitle_data, embeddings, speaker_labels, k, kluster_labels, EMBEDDINGS_UMAP

audio_clips, embeddings, speaker_labels, k, kluster_labels, EMBEDDINGS_UMAP = load_or_identify_speakers(audio_file_path, use_local)

HEIGHT = 300
margin = dict(l=60, r=20, t=20, b=50, pad=0)

fig_settings = {
    "height": HEIGHT,
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

def get_color_from_label(label):
    random.seed(hash(label))
    return "#{:02x}{:02x}{:02x}".format(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

def get_scatter_figure(EMBEDDINGS_UMAP, audio_clips, speaker_labels):
    colors = [get_color_from_label(label) for label in speaker_labels]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=EMBEDDINGS_UMAP[:, 0],
            y=EMBEDDINGS_UMAP[:, 1],
            hovertext=[audio_clips[i]["text"][:20 - 3] + "..." for i in range(EMBEDDINGS_UMAP.shape[0])],
            hoverinfo="text",
            mode='markers',
            marker=dict(
                size=10,
                opacity=0.8,
                color=colors,
            ),
            showlegend=False)
    )
    fig.update_xaxes(showticklabels=False, automargin=False)
    fig.update_yaxes(showticklabels=False, automargin=False)
    fig.update_layout(dragmode="lasso")
    return fig

app = dash.Dash(__name__, suppress_callback_exceptions=True)

app.layout = html.Div([
    html.Div([
        html.Div([
            dcc.Graph(
                id='scatter-plot',
                config={'displayModeBar': False},
                figure=get_scatter_figure(EMBEDDINGS_UMAP, audio_clips, speaker_labels)
            )
        ], style={'width': '100%', 'display': 'inline-block', 'height': f'{HEIGHT}px'}),
        html.Div(id='dynamic-content', children="", style={'height': '50px', 'vertical-align': 'top', 'position': 'absolute', 'padding': '30px', 'width': '450px', 'left': '50px', 'top': f'{HEIGHT+50}px'}),
        html.Div(id='bottom-ui1', children="", style={'height': f'{HEIGHT-50}px', 'vertical-align': 'top', 'padding': '30px', 'position': 'absolute', 'top': f'{HEIGHT+50}px'}),
    ], style={'width': '50%', 'display': 'inline-block', 'height': '100vh', "position": "relative"}),
    html.Div([
        html.H2(children="Transcript"),
        html.Div(id='transcript', children="", style={'vertical-align': 'top'})
    ], style={'width': '50%', 'height': '90vh', 'display': 'inline-block', 'vertical-align': 'top', 'overflowY': 'scroll'}),
    dcc.Store(id='speaker-labels', data=speaker_labels),
    dcc.Store(id='selected-clip', data=None),
    dcc.Store(id='selected-speakers', data=None),
    dcc.Store(id='selected-data', data=None)  # Store for selection data
], style={'backgroundColor': 'white'})

@app.callback(
    Output('selected-data', 'data'),
    Input('scatter-plot', 'selectedData'),
    prevent_initial_call=True
)
def store_selected_data(selectedData):
    return selectedData

@app.callback(
    Output('dynamic-content', 'children'),
    Output('selected-speakers', 'data'),
    Input('selected-data', 'data'),
    prevent_initial_call=True
)
def update_ui_for_naming(selectedData):
    if selectedData:
        return html.Div([
            dcc.Input(id='name-input', type='text', placeholder='Enter name...'),
            html.Button('Submit', id='submit-button', n_clicks=0)
        ]), selectedData
    return "No points selected.", selectedData

@app.callback(
    Output('speaker-labels', "data"),
    Output('scatter-plot', 'figure'),
    Input('submit-button', 'n_clicks'),
    State('speaker-labels', 'data'),
    State('selected-speakers', "data"),
    State('name-input', 'value'),
    prevent_initial_call=True
)
def handle_name_submission(n_clicks, speakers, selectedData, name):
    if name and selectedData:
        indices = [point['pointIndex'] for point in selectedData['points']]
        for idx in indices:
            speakers[idx] = name  # Update the speaker labels
        
        figure = get_scatter_figure(EMBEDDINGS_UMAP, audio_clips, speakers)  # Update the figure with new labels
        return speakers, figure
    return speakers, dash.no_update

@app.callback(
    Output('transcript', "children"),
    Input('speaker-labels', 'data'),
    Input('selected-clip', 'data'),
    Input('selected-data', 'data'),
    prevent_initial_call=True
)
def update_transcript(speakers, selected_clip, selected_data):
    print("------------- updating transcript ---------------")

    if selected_clip is not None:
        point_index = selected_clip
    elif selected_data and 'points' in selected_data and len(selected_data['points']) > 0:
        point_index = selected_data['points'][0]['pointIndex']
    else:
        point_index = 0

    p = []
    for index, clip in enumerate(audio_clips):
        background_color = get_color_from_label(speakers[index])
        style = {
            'backgroundColor': f'rgba({int(background_color[1:3], 16)}, {int(background_color[3:5], 16)}, {int(background_color[5:7], 16)}, 0.5)'
        }
        if index == point_index:
            p.append(
                html.P([html.B(f"{speakers[index]}: {clip['text']}", id=f"highlighted-{index}")], style=style)
            )
        else:
            p.append(
                html.P(f"{speakers[index]}: {clip['text']}", style=style)
            )

    return p

@app.callback(
    Output('bottom-ui1', 'children', allow_duplicate=True),
    Input('scatter-plot', 'clickData'),
    prevent_initial_call=True
)
def on_click(click_data):
    if click_data is None:
        return ""
    point_index = click_data['points'][0]['pointIndex']
    media_url = app.get_asset_url(audio_clips[point_index]['clip'])
    encoded_sound = "data:audio/mp3;base64," + base64.b64encode(open(audio_clips[point_index]['clip'], 'rb').read()).decode('utf-8')
    child_html = [
        html.H3(f"Listen to {point_index}"),
        dash_dangerously_set_inner_html.DangerouslySetInnerHTML(f'''
            <div id="audiodiv">
                <audio id="audio_player" src="{encoded_sound}" controls="controls" autobuffer="autobuffer" autoplay="autoplay">
                </audio>
            </div>
        '''),
        html.P([html.Strong("Clip:"), f"{media_url}"]),
        html.P([html.Strong("Text:"), f"{audio_clips[point_index]['text']}"]),
        html.Button('Highlight text', id='highlight', n_clicks=0)
    ]
    return child_html

app.clientside_callback(
    """
    function (n_clicks) {
        if (n_clicks === 0) return window.dash_clientside.no_update;

        var highlightedElements = document.querySelectorAll('[id^="highlighted-"]');
        if (highlightedElements.length === 0) return window.dash_clientside.no_update;

        var highlighted = highlightedElements[highlightedElements.length - 1];
        var scrollableDiv = document.getElementById('transcript');

        if (!highlighted || !scrollableDiv) return window.dash_clientside.no_update;

        // Calculate the position to scroll
        var scrollTop = highlighted.offsetTop - scrollableDiv.offsetTop - (scrollableDiv.clientHeight / 2) + (highlighted.clientHeight / 2);

        // Scroll to the calculated position
        scrollableDiv.scrollTop = scrollTop;

        return window.dash_clientside.no_update;
    }
    """,
    Output('selected-clip', 'data'),
    Input('highlight', 'n_clicks'),
)

if __name__ == '__main__':
    app.run_server(debug=True, port=8051)
