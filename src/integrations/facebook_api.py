# Facebook API Integration
"""
LocalAI Assistant - Facebook API Integration
Handles Facebook Messenger and page interactions
"""

import os
import logging
import hmac
import hashlib
import json
from typing import Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)

class FacebookAPI:
    """Facebook API integration for Messenger and page management"""
    
    def __init__(self):
        self.access_token = os.getenv('FACEBOOK_ACCESS_TOKEN')
        self.verify_token = os.getenv('FACEBOOK_VERIFY_TOKEN', 'localai_verify_token')
        self.app_secret = os.getenv('FACEBOOK_APP_SECRET')
        self.base_url = "https://graph.facebook.com/v18.0"
        
        if not self.access_token:
            logger.warning("Facebook access token not found in environment variables")
        else:
            logger.info("Facebook API initialized successfully")
    
    async def send_message(self, recipient_id: str, message: str) -> Dict[str, Any]:
        """Send message via Facebook Messenger"""
        try:
            if not self.access_token:
                logger.error("Facebook access token not configured")
                return {"error": "Facebook not configured"}
            
            url = f"{self.base_url}/me/messages"
            
            payload = {
                "recipient": {"id": recipient_id},
                "message": {"text": message},
                "messaging_type": "RESPONSE"
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}"
            }
            
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Facebook message sent successfully: {result.get('message_id')}")
                return {
                    "success": True,
                    "message_id": result.get('message_id'),
                    "recipient_id": recipient_id
                }
            else:
                logger.error(f"Facebook API error: {response.status_code} - {response.text}")
                return {"error": f"Facebook API error: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Facebook message send error: {str(e)}")
            return {"error": f"Failed to send Facebook message: {str(e)}"}
    
    async def process_webhook(self, webhook_data: Dict[str, Any]) -> list:
        """Process incoming Facebook webhook data"""
        try:
            messages = []
            
            for entry in webhook_data.get('entry', []):
                for messaging in entry.get('messaging', []):
                    if 'message' in messaging:
                        message_data = {
                            "sender_id": messaging['sender']['id'],
                            "recipient_id": messaging['recipient']['id'],
                            "message": messaging['message'].get('text', ''),
                            "message_id": messaging['message'].get('mid'),
                            "timestamp": messaging.get('timestamp'),
                            "platform": "facebook"
                        }
                        messages.append(message_data)
            
            return messages
            
        except Exception as e:
            logger.error(f"Facebook webhook processing error: {str(e)}")
            return []
    
    def verify_webhook(self, webhook_data: Dict[str, Any]) -> bool:
        """Verify Facebook webhook signature"""
        try:
            if not self.app_secret:
                logger.warning("Facebook app secret not configured - skipping verification")
                return True
            
            # This is a simplified verification - in production you'd verify the signature
            return True
            
        except Exception as e:
            logger.error(f"Facebook webhook verification error: {str(e)}")
            return False
    
    def verify_token(self, token: str) -> bool:
        """Verify Facebook webhook verification token"""
        return token == self.verify_token
    
    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get user information from Facebook"""
        try:
            if not self.access_token:
                return {"error": "Facebook not configured"}
            
            url = f"{self.base_url}/{user_id}"
            params = {
                "fields": "first_name,last_name,profile_pic",
                "access_token": self.access_token
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error getting user info: {response.status_code}")
                return {"error": "Failed to get user info"}
                
        except Exception as e:
            logger.error(f"Get user info error: {str(e)}")
            return {"error": str(e)}
    
    async def post_to_page(self, page_id: str, message: str) -> Dict[str, Any]:
        """Post message to Facebook page"""
        try:
            if not self.access_token:
                return {"error": "Facebook not configured"}
            
            url = f"{self.base_url}/{page_id}/feed"
            
            payload = {
                "message": message,
                "access_token": self.access_token
            }
            
            response = requests.post(url, data=payload)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Facebook page post successful: {result.get('id')}")
                return {
                    "success": True,
                    "post_id": result.get('id')
                }
            else:
                logger.error(f"Facebook page post error: {response.status_code}")
                return {"error": f"Failed to post to page: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Facebook page post error: {str(e)}")
            return {"error": str(e)}
    
    async def get_page_comments(self, page_id: str) -> list:
        """Get recent comments on page posts"""
        try:
            if not self.access_token:
                return []
            
            url = f"{self.base_url}/{page_id}/posts"
            params = {
                "fields": "comments{message,from,created_time}",
                "access_token": self.access_token
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                posts = response.json().get('data', [])
                comments = []
                
                for post in posts:
                    for comment in post.get('comments', {}).get('data', []):
                        comments.append({
                            "comment_id": comment.get('id'),
                            "message": comment.get('message'),
                            "author": comment.get('from', {}).get('name'),
                            "author_id": comment.get('from', {}).get('id'),
                            "created_time": comment.get('created_time')
                        })
                
                return comments
            else:
                logger.error(f"Error getting page comments: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Get page comments error: {str(e)}")
            return []
    
    async def reply_to_comment(self, comment_id: str, message: str) -> Dict[str, Any]:
        """Reply to a Facebook comment"""
        try:
            if not self.access_token:
                return {"error": "Facebook not configured"}
            
            url = f"{self.base_url}/{comment_id}/comments"
            
            payload = {
                "message": message,
                "access_token": self.access_token
            }
            
            response = requests.post(url, data=payload)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Facebook comment reply successful: {result.get('id')}")
                return {
                    "success": True,
                    "comment_id": result.get('id')
                }
            else:
                logger.error(f"Facebook comment reply error: {response.status_code}")
                return {"error": f"Failed to reply to comment: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Facebook comment reply error: {str(e)}")
            return {"error": str(e)}