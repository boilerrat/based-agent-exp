import os

from time import sleep
from typing import List, Dict, Optional
import requests
import uuid

from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class FarcasterBot:
    def __init__(self):
        """Initialize Warpcast bot with credentials"""
        print("initializing bot")

        self.v2_url = "https://api.neynar.com/v2/farcaster/"
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-key": os.getenv("NAYNAR_API_KEY")
        }

        
    def post_cast(self, content: str, parent: Optional[str] = None) -> str:
        """
        Post a cast
        
        Args:
            content (str): The content of the cast
            parent (Optional[str]): The parent cast hash (for reply)
            
        Returns:
            str: Status message about the cast
        """
        try:
            url = self.v2_url + "cast"
            unique_id = str(uuid.uuid4())[:16]
            payload = { 
                "signer_uuid": os.getenv("NAYNAR_SIGNER_UUID"),
                "idem": unique_id,
                "text": content,
                "parent_author_fid": int(os.getenv("FARCASTER_FID"))
            }
            if parent:
                payload["parent"] = parent
            response = requests.post(url, json=payload, headers=self.headers)

            return f"Successfully posted cast with ID: {response.json()['cast']['hash']}"
        except Exception as e:
            return f"Error posting cast: {str(e)}"
        
        
    def get_replies(self) -> Dict:
        """
        Get recent replies
            
        Returns:
            Dict: Cast object containing relevant information
        """
        try:
            url = self.v2_url + "feed/user/replies_and_recasts?fid=" + os.getenv("FARCASTER_FID") + "&filter=all&limit=25"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                return f"Error getting relies: {response.status_code} - {response.text}"
            
            # Parse response JSON
            response_data = response.json()

            # Extract the list of relies from the response
            replies = response_data.get('casts', [])

            # Extracting details from each notification
            result = [
                {
                    'timestamp': reply['timestamp'],
                    'parent_hash': reply['parent_hash'],
                    'hash': reply['hash'],
                    'text': reply['text'],
                    'author': reply['author']['username'],
                    
                }
                for reply in replies
            ]

            return result


            
            return response.json()
        except Exception as e:
            return f"Error getting replies: {str(e)}"
        
    def get_notifications(self) -> List[Dict]:
        """
        Get recent replies
            
        Returns:
            List[Dict]: List of relevant notifications containing timestamp, thread hash, text, and author
        """
        try:
            # Constructing the URL for fetching notifications
            url = self.v2_url + "notifications?fid=" + os.getenv("FARCASTER_FID") + "&type=&priority_mode=false"

            response = requests.get(url, headers=self.headers)

            # Ensure the response is successful
            if response.status_code != 200:
                return f"Error getting notifications: {response.status_code} - {response.text}"

            # Parse response JSON
            response_data = response.json()

            # Extract the list of notifications from the response
            notifications = response_data.get('notifications', [])

            # Extracting details from each notification
            result = [
                {
                    'timestamp': notification['cast']['timestamp'],
                    'hash': notification['cast']['hash'],
                    'text': notification['cast']['text'],
                    'author': notification['cast']['author']['username'],
                    'type': notification['type'],
                    'seen': notification['seen'],
                    'age_in_sec': (datetime.utcnow() - datetime.strptime(notification['cast']['timestamp'], "%Y-%m-%dT%H:%M:%S.%fZ")).total_seconds()
                }
                for notification in notifications
                if notification.get('type') in ['reply', 'mention'] and 'cast' in notification
            ]

            return result

        except Exception as e:
            return f"Error getting notifications: {str(e)}"


    def mark_notifications_as_seen(self) -> str:
        """
        Mark a notification as seen
        
            
        Returns:
            str: Status message about the action
        """

        try:
            url = self.v2_url + "notifications/seen"
            payload = os.getenv("NAYNAR_SIGNER_UUID")
            response = requests.post(url, json=payload, headers=self.headers)
            print(response.text)
            return f"Successfully marked notifications as seen {response}"
        except Exception as e:
            return f"Error marking notification as seen: {str(e)}"

    # def reply_to_cast(self, cast_id: str, content: str) -> str:
    #     """
    #     Reply to a specific cast
        
    #     Args:
    #         cast_id (str): ID of the cast to reply to
    #         content (str): Content of the reply
            
    #     Returns:
    #         str: Status message about the reply
    #     """
    #     try:
    #         cast = self.client.get_cast(cast_id)
    #         print(cast)

    #         # Check if the cast exists
            
    #         # reply = self.client.post_cast(content, None, cast_id)
    #         return f"Successfully replied to cast {cast_id}"
    #     except Exception as e:
    #         return f"Error replying to cast: {str(e)}"
