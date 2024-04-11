import os

def ensure_path_exists(file_path):
    # If the given path is a directory, create it if it doesn't exist
    if os.path.isdir(file_path):
        if not os.path.exists(file_path):
            os.makedirs(file_path)
    # If the given path is a file, create its parent directory if it doesn't exist
    else:
        folder = os.path.dirname(file_path)
        if not os.path.exists(folder):
            os.makedirs(folder)

def file_has_content(file_path):
    if not os.path.exists(file_path):
        return False
    
    # Read the content of the file
    with open(file_path, 'r') as file:
        content = file.read()
    
    # Check if the content is not empty
    return content.strip() != ""