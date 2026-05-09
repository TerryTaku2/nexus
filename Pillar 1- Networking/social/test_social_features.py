"""
Simple test examples for Social Features API
Run: python test_social_features.py
"""

import requests

BASE_URL = "http://localhost:8001"

def test_posts():
    print("Testing Posts...")

    # Create a post
    post_data = {"author_id": 1, "content": "Hello World!"}
    resp = requests.post(f"{BASE_URL}/posts", json=post_data)
    print(f"Create Post: {resp.status_code}")

    # Get all posts
    resp = requests.get(f"{BASE_URL}/posts")
    print(f"Get Posts: {resp.status_code}")

def test_updates():
    print("Testing Updates...")

    # Create an update
    update_data = {"user_id": 1, "update_text": "Available now"}
    resp = requests.post(f"{BASE_URL}/updates", json=update_data)
    print(f"Create Update: {resp.status_code}")

    # Get all updates
    resp = requests.get(f"{BASE_URL}/updates")
    print(f"Get Updates: {resp.status_code}")

def test_following():
    print("Testing Following...")

    # Follow a user
    follow_data = {"follower_id": 1, "target_id": 2}
    resp = requests.post(f"{BASE_URL}/follow", json=follow_data)
    print(f"Follow: {resp.status_code}")

    # Get followers
    resp = requests.get(f"{BASE_URL}/followers/2")
    print(f"Get Followers: {resp.status_code}")

def test_smes():
    print("Testing SMEs...")

    # Get all SMEs
    resp = requests.get(f"{BASE_URL}/smes")
    print(f"Get SMEs: {resp.status_code}")

if __name__ == "__main__":
    print("Testing Social Features API")
    print("Make sure the API is running first")

    try:
        test_posts()
        test_updates()
        test_following()
        test_smes()
        print("Tests completed!")
    except Exception as e:
        print(f"Error: {e}")
