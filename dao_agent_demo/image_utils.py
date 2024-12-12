import os

from time import sleep
from typing import List, Dict, Optional
import requests
import uuid

from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class ImageThumbnailer:
    def __init__(self):
        """Initialize image thumbnailer with credentials"""
        print("initializing image thumbnailer")

        self.v1_url = f"https://api.imgbb.com/1/upload?key={os.getenv('IMG_BB_API_KEY')}"
        

    def upload_image(self, image_url: str) -> str:
        """
        Upload an image
        Args:
            image_url (str): The url to the image
        Returns:
            str: URL of the uploaded image
        """
        try:
            url = self.v1_url
            payload = {
                "image": image_url
            }
            response = requests.post(url, data=payload)
            return response.json()["data"]["medium"]["url"]
        except Exception as e:
            return f"Error uploading image: {str(e)}"
        
