from pytube import YouTube
from pytube.extract import video_id
import os
from interview_transcriber.file_utils import ensure_path_exists

def download_youtube_video(video_url, folder_path='data/video/youtube'):
    """
    Download a YouTube video into a specific folder.
    
    Parameters:
    - video_url: str. The URL of the YouTube video to download.
    - folder_path: str. The path to the folder where the video will be saved. Defaults to 'data'.
    """
    # Ensure the folder exists

    
    try:
        # Create YouTube video object
        yt = YouTube(video_url)
        
        id = video_id(video_url)

        print("id: " + id)

        folder = os.path.join(folder_path, id)    
        ensure_path_exists(folder)

        # Get the highest resolution stream available
        video_stream = yt.streams.get_lowest_resolution()
        
        # Download the video
        video_path = video_stream.download(output_path=folder)
        return video_path, video_stream.title, id

        print(f"Video downloaded successfully: {video_stream.title}")
    except Exception as e:
        print(f"An error occurred: {e}")



def video_folder_exists(video_url, folder_path='data/video/youtube'):

    try:
        # Create YouTube video object
        yt = YouTube(video_url)
        
        id = video_id(video_url)
        folder = os.path.join(folder_path, id)    

        if os.path.exists(folder):
           return True # a bit naive yes.... 

    except Exception as e:
        return False
    
    return False
