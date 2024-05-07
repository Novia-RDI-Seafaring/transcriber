import os
from .audio_transcriber import combine_subtitle_lines
from .audio_transcriber import transcribe
from .audio_clip_generator import generate_audio_clips
from .file_utils import get_content
from interview_transcriber.audio_clip_generator import adjust_audio_duration

import torch
import umap
import nemo.collections.asr as nemo_asr

from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
import numpy as np

def identify_speakers(audio_file_path, subtitles=None, context_string="", use_local=False, language=None):   
    if subtitles is None:
        subtitles = transcribe(audio_file_path, context_string, use_local=use_local, language=language)
    else:
        subtitles = get_content(subtitles)

    print("SUBTITLES:", subtitles)
    # Get the base name of the file (i.e., 'audiofile.mp3')
    base_name = os.path.basename(audio_file_path)

    # Remove the file extension to get 'audiofile'
    filename_without_extension = os.path.splitext(base_name)[0]

    output_folder = os.path.join(os.path.dirname(audio_file_path),  f"{filename_without_extension}_clips")
    combined_subs, speaker_data = combine_subtitle_lines(subtitles)
    augmented_speaker_data = generate_audio_clips(speaker_data, audio_file_path, output_folder)
    print("Augmented Speaker Data:", augmented_speaker_data)
    embeddings = get_speaker_embeddings(augmented_speaker_data)
    print("Embeddings List:", embeddings)
    print("getting speakers from embeddings...")

    speakers, k, kluster_labels, embeddings_umap = get_speakers_from_embeddings(embeddings)
    print(speakers)
    for i, segment in enumerate(augmented_speaker_data):
        augmented_speaker_data[i]["speaker"] = speakers[i]
    
    return augmented_speaker_data, embeddings, speakers, k, kluster_labels, embeddings_umap

def apply_pca(embeddings):
    print("Applying PCA...")
    if isinstance(embeddings, torch.Tensor):
        embeddings = embeddings.detach().cpu().numpy()  # Ensure the embeddings are numpy arrays
    pca = PCA(n_components=2)  # You can adjust components based on your requirements
    reduced_embeddings = pca.fit_transform(embeddings)
    return reduced_embeddings

def get_speakers_from_embeddings(embeddings):
    print("Running on embeddings with shape:", embeddings.shape)
    if embeddings.shape[0] < 4:  # Less than 4 might be too few for meaningful UMAP
        print("Insufficient data points for UMAP, applying PCA instead.")
        embeddings_umap = apply_pca(embeddings)  # This will handle conversion and PCA
    else:
        n_neighbors = max(2, min(embeddings.shape[0] - 1, int(embeddings.shape[0] * 0.1), 50))
        print(f"Using n_neighbors: {n_neighbors}")
        reducer = umap.UMAP(n_neighbors=n_neighbors, min_dist=0.0, random_state=None, n_jobs=-1)
        print("Fit_transform step...")
        try:
            embeddings_umap = reducer.fit_transform(embeddings)
        except Exception as e:
            print("Error in UMAP transformation:", e)
            return None

    print("Get clusters from reduced embeddings, shape:", embeddings_umap.shape)
    k, kluster_labels = get_clusters(embeddings_umap, 10)
    print(f"Identified {k} clusters.")
    speaker_labels = label_to_speakers(kluster_labels)
    return speaker_labels, k, kluster_labels, embeddings_umap


def get_speaker_embeddings(speaker_data_with_clips):
    print("Getting speaker embeddings")
    speaker_model = nemo_asr.models.EncDecSpeakerLabelModel.from_pretrained("nvidia/speakerverification_en_titanet_large")
    embeddings = []
    print("speaker_data_with_clips:", speaker_data_with_clips)
    # Export each silent part as a separate audio file
    for i, segment in enumerate(speaker_data_with_clips):
        print(i)
        # Export the original segment
        original_file = segment['clip']
        trimmed_file = original_file.replace(".wav", "_trimmed.wav")
        adjust_audio_duration(original_file, trimmed_file, 2)

        # Get embeddings for the trimmed segment
        print(f"getting speaker embedding for {trimmed_file}")
        embeddings.append(
            speaker_model.get_embedding(trimmed_file)
        )
    if embeddings:
        concatenated_embeddings = torch.cat(embeddings, dim=0)
    else:
        print("Warning: No embeddings generated.")
        return None  # or handle as appropriate
    return concatenated_embeddings



def get_clusters(data, max_clusters=10):
    n_samples = data.shape[0]
    max_clusters = min(max_clusters, n_samples - 1)  # Ensure max_clusters is less than number of samples

    if max_clusters < 2:
        raise ValueError(f"Not enough data points to form multiple clusters for silhouette analysis. {max_clusters}, {n_samples}")

    silhouette_scores = []
    K_to_try = range(2, max_clusters + 1)  # Ensure we always try at least two clusters

    for k in K_to_try:
        print("getting k means for k =", k)
        kmeans = KMeans(n_clusters=k, random_state=0).fit(data)
        # Calculate silhouette score for each k
        if k > 1:
            print("getting silhouette_score for k =", k)
            score = silhouette_score(data, kmeans.labels_)
            silhouette_scores.append(score)

    # Find the optimal k
    print("getting np argmax")
    optimal_k_index = np.argmax(silhouette_scores)
    optimal_k = K_to_try[optimal_k_index]

    print("Applying k-means for optimal k =", optimal_k)
    kmeans = KMeans(n_clusters=optimal_k, random_state=0).fit(data)
    labels = kmeans.labels_

    return optimal_k, labels


def label_to_speakers(labels):
    # Find unique speaker IDs in the order of appearance
    unique_speakers = []
    for label in labels:
        if label not in unique_speakers:
            unique_speakers.append(label)
    
    # Create a mapping of original speaker IDs to new speaker labels
    speaker_mapping = {unique_speakers[i]: f"Speaker {i+1}" for i in range(len(unique_speakers))}
    
    # Map original labels to new speaker labels
    speakers = [speaker_mapping[label] for label in labels]
    
    return speakers
