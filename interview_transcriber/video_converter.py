from interview_transcriber.file_utils import ensure_path_exists
import subprocess
import os

def create_audiofilepath(video_path):
    audio_path = video_path.replace("/video/", "/audio/").replace(".mp4", ".mp3")
    ensure_path_exists(audio_path)
    return audio_path

def there_is_a_converted_audio_file(video_path):
    print(f"video path: {video_path}")
    audio_path = create_audiofilepath(video_path)
    print(f"audio path: {audio_path}")
    return os.path.isfile(audio_path)

def convert_video_to_mp3(video_path, audio_folder='data/audio'):
    """
    Converts a video file to an MP3 file using FFmpeg and saves it in the data/audio folder.

    Parameters:
    video_path (str): The path to the video file to be converted.
    """

    output_file = create_audiofilepath(video_path) #os.path.join(audio_folder, os.path.splitext(os.path.basename(video_path))[0] + '.mp3')
    
    # Command to convert video to mp3
    cmd = ['ffmpeg', '-i', video_path, '-q:a', '0', '-map', 'a', output_file]
    
    try:
        # Execute the command
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Converted {video_path} to {output_file}")
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"Failed to convert video to MP3: {e}")
    