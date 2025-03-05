#!/usr/bin/env python
"""
Threads API Setup Script

This script helps you set up the Threads API by guiding you through the OAuth process
and saving the resulting tokens to your .env file.
"""

import os
import sys
import time
import requests
import webbrowser
from dotenv import load_dotenv, set_key

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

def main():
    print("=== Threads API Setup ===")
    
    # Check if we have the required credentials
    client_id = os.getenv('THREADS_CLIENT_ID')
    client_secret = os.getenv('THREADS_CLIENT_SECRET')
    redirect_uri = os.getenv('THREADS_REDIRECT_URI')
    
    if not client_id or not client_secret or not redirect_uri:
        print("Error: Missing required credentials in .env file")
        print("Please ensure you have the following variables set:")
        print("  THREADS_CLIENT_ID")
        print("  THREADS_CLIENT_SECRET")
        print("  THREADS_REDIRECT_URI")
        print("\nYou can get these by creating an app at https://developers.facebook.com/")
        return
    
    # Generate the authorization URL
    auth_url = f"https://www.threads.net/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&scope=threads_basic,threads_media"
    
    print("\nStep 1: Open the following URL in your browser:")
    print(auth_url)
    
    # Try to open the browser automatically
    try:
        webbrowser.open(auth_url)
    except:
        pass
    
    print("\nStep 2: Log in and authorize the app")
    print("You will be redirected to your redirect URI with a 'code' parameter")
    
    # Get the authorization code from the user
    auth_code = input("\nEnter the authorization code from the URL: ")
    
    if not auth_code:
        print("Error: No authorization code provided")
        return
    
    print("\nStep 3: Exchanging code for access token...")
    
    # Exchange the code for an access token
    token_data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': redirect_uri
    }
    
    try:
        response = requests.post(
            "https://graph.threads.net/oauth/access_token", 
            data=token_data
        )
        
        if response.status_code == 200:
            token_info = response.json()
            access_token = token_info.get('access_token')
            refresh_token = token_info.get('refresh_token')
            expires_in = token_info.get('expires_in', 3600)
            token_expiry = str(time.time() + expires_in)
            
            # Save tokens to .env file
            env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
            
            set_key(env_file, 'THREADS_ACCESS_TOKEN', access_token)
            set_key(env_file, 'THREADS_REFRESH_TOKEN', refresh_token)
            set_key(env_file, 'THREADS_TOKEN_EXPIRY', token_expiry)
            
            print("\nSuccess! Tokens have been saved to your .env file")
            print(f"Access token will expire in {expires_in} seconds")
            
            # Test the token by getting the user profile
            print("\nTesting the token by fetching your profile...")
            
            profile_url = "https://graph.threads.net/v1/me"
            params = {'access_token': access_token}
            
            profile_response = requests.get(profile_url, params=params)
            
            if profile_response.status_code == 200:
                profile = profile_response.json()
                print(f"Success! Logged in as: {profile.get('username')}")
            else:
                print(f"Warning: Could not fetch profile: {profile_response.text}")
            
        else:
            print(f"Error: Failed to get access token: {response.text}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 