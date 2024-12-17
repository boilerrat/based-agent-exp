import os


def fetch_world_files(folder_path = "worlds") -> list:
    # List files in the folder
    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    if not files:
        print("No files found in the folder.")
        return list()

    return files
