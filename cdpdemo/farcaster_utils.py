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

        
    def post_cast(self, content: str, channel_id: Optional[str] = None,parent: Optional[str] = None, parent_fid: Optional[str] = None) -> str:
        """
        Post a cast
        
        Args:
            content (str): The content of the cast
            channel_id (Optional[str]): The channel ID
            parent (Optional[str]): The parent cast hash (for reply)
            
        Returns:
            str: Status message about the cast
        """
        try:
            channel_id = channel_id or os.getenv("FARCASTER_CHANNEL_ID")
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
            if parent_fid:
                payload["parent_fid"] = parent_fid
            if channel_id:
                payload["channel_id"] = channel_id
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
                    'author_fid':  reply['author']['fid'],
                    
                }
                for reply in replies
            ]

            return result


            
            return response.json()
        except Exception as e:
            return f"Error getting replies: {str(e)}"
        
    def safe_get(d, keys, default=None):
        """
        Safely access a nested dictionary.
        Args:
            d (dict): The dictionary to access.
            keys (list): A list of keys representing the nested structure.
            default: The default value to return if any key is missing.
        Returns:
            The value at the nested key or the default value.
        """
        for key in keys:
            if isinstance(d, dict):
                d = d.get(key, default)
            else:
                return default
        return d
        
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

# notification['cast']['author']['verified_address']['eth_addresses'][0]
            result = [
                {
                    'timestamp': notification['cast']['timestamp'],
                    'hash': notification['cast']['hash'],
                    'text': notification['cast']['text'],
                    'author': notification['cast']['author']['username'],
                    'author_fid':  notification['cast']['author']['fid'],
                    'author_verified_address': (
                            notification['cast']['author']['verified_addresses']['eth_addresses'][0]
                            if 'verified_addresses' in notification['cast']['author'] and
                            'eth_addresses' in notification['cast']['author']['verified_addresses'] and
                            len(notification['cast']['author']['verified_addresses']['eth_addresses']) > 0
                            else None
                        ),
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


    def get_casts(self, fid:str = os.getenv("FARCASTER_FID"), limit: int = 25, include_replies: bool = True) -> List[Dict]:
        """
        Get recent casts

        Args:
            fid (str): The fid of the user
            limit (int): The number of casts to fetch
            include_replies (bool): Whether to include replies in the casts
                
        Returns:
            List[Dict]: List of relevant casts containing timestamp, hash, text, and author
        """
        viewer_fid = os.getenv("FARCASTER_FID")
        try:
            # Constructing the URL for fetching casts
            url = self.v2_url + f"feed/user/casts?fid={fid}&viewer_fid={viewer_fid}&limit={limit}&include_replies={include_replies}"

            response = requests.get(url, headers=self.headers)

            # Ensure the response is successful
            if response.status_code != 200:
                return f"Error getting casts: {response.status_code} - {response.text}"

            # Parse response JSON
            response_data = response.json()

            # Extract the list of casts from the response
            casts = response_data.get('casts', [])

            # Extracting details from each cast
            result = [
                {
                    'timestamp': cast['timestamp'],
                    'hash': cast['hash'],
                    'text': cast['text'],
                    'author': cast['author']['username'],
                    'author_fid':  cast['author']['fid'],
                }
                for cast in casts
            ]

            return result

        except Exception as e:
            return f"Error getting casts: {str(e)}"


    def get_user_by_username(self, username: str) -> Dict:
        """
        Get user information by username
        
        Args:
            username (str): The username of the user
            
        Returns:
            Dict: User information
        """
        try:
            url = self.v2_url + f"user/by_username?username={username}&viewer_fid={os.getenv('FARCASTER_FID')}"
            response = requests.get(url, headers=self.headers)

            return response.json()
        except Exception as e:
            return f"Error getting user by username: {str(e)}"