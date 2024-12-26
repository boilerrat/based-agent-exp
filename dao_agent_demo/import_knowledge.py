import os
import argparse
from tinydb import TinyDB, Query

def extract_keywords(file_name):
    """
    Extract keywords from the filename by splitting on underscores and removing the file extension.
    """
    base_name = os.path.splitext(file_name)[0]  # Remove file extension
    keywords = base_name.split('_')  # Split by underscores
    return keywords

def import_markdown_files_to_db(directory, db_path):
    """
    Import all Markdown files from a directory into TinyDB with keywords based on filenames.
    Skip files that have already been imported.
    """
    db = TinyDB(db_path)
    File = Query()

    for file_name in os.listdir(directory):
        if file_name.endswith('.md'):  # Process only Markdown files
            file_path = os.path.join(directory, file_name)
            
            # Check if the file has already been imported
            if db.contains(File.file_name == file_name):
                print(f"Skipping already imported file: {file_name}")
                continue
            
            # Read the file content
            with open(file_path, 'r') as file:
                content = file.read()
            
            # Extract keywords from filename
            keywords = extract_keywords(file_name)
            
            # Create a record for the database
            record = {
                'file_name': file_name,
                'content': content,
                'keywords': keywords
            }
            
            # Insert into the database
            db.insert(record)
            print(f"Imported: {file_name}")
    
    print(f"Import completed. All records are stored in {db_path}.")

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Import Markdown files into TinyDB.")
    parser.add_argument(
        '--directory', 
        type=str, 
        default='./knowledge', 
        help="Directory containing Markdown files (default: './knowledge')"
    )
    parser.add_argument(
        '--db_path', 
        type=str, 
        default='db.json', 
        help="Path to the TinyDB database file (default: 'db.json')"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Run the import function
    import_markdown_files_to_db(args.directory, args.db_path)

