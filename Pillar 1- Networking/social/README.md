# Social Features API

Basic FastAPI endpoints for Posts, Updates, SMEs, and Following.

## Setup
```bash
pip install -r requirements.txt
python social_features.py
```

## Endpoints

### Posts
- `POST /posts` - Create post
- `GET /posts` - Get all posts
- `GET /posts/{author_id}` - Get user's posts

### Updates
- `POST /updates` - Create update
- `GET /updates` - Get all updates
- `GET /updates/{user_id}` - Get user's updates

### SMEs
- `GET /smes` - Get all SMEs
- `GET /smes/{category}` - Get SMEs by category

### Following
- `POST /follow` - Follow user
- `DELETE /follow/{follower_id}/{target_id}` - Unfollow
- `GET /followers/{user_id}` - Get followers
- `GET /following/{user_id}` - Get following
- **Response:** List of `PostResponse` (ordered by most recent)

#### Get Posts by Author
- **GET** `/posts/by-author/{author_id}?limit=50`
- **Response:** List of author's posts (ordered by most recent)

---

### 📢 Updates

#### Create an Update
- **POST** `/updates`
- **Body:**
  ```json
  {
    "user_id": 1,
    "update_text": "Status change or notification"
  }
  ```
- **Response:** `UpdateResponse` with id, user_id, update_text, time_posted

#### Get Single Update
- **GET** `/updates/{update_id}`
- **Response:** `UpdateResponse`

#### Get All Updates
- **GET** `/updates?limit=50`
- **Response:** List of all updates (ordered by most recent)

#### Get Updates by User
- **GET** `/updates/by-user/{user_id}?limit=50`
- **Response:** List of user's updates (ordered by most recent)

---

### 🗺️ SMEs (Nearby Experts)

#### Find Nearby SMEs
- **GET** `/smes/nearby?latitude=40.7128&longitude=-74.0060&radius_km=5.0`
- **Query Params:**
  - `latitude`: User's latitude (required)
  - `longitude`: User's longitude (required)
  - `radius_km`: Search radius (0.1-100 km, default 5 km)
- **Response:** List of `SMEResponse` sorted by distance (closest first)
- **Example:**
  ```json
  [
    {
      "id": 1,
      "name": "Tech Experts Inc",
      "category": "Technology",
      "latitude": 40.7128,
      "longitude": -74.0060,
      "distance_km": 0.5
    }
  ]
  ```

#### Get SMEs by Category
- **GET** `/smes/by-category/{category}`
- **Response:** List of `SMEResponse` in that category

#### Get All SMEs
- **GET** `/smes`
- **Response:** List of all `SMEResponse`

---

### 👥 Following & Followers

#### Follow a User
- **POST** `/follow`
- **Body:**
  ```json
  {
    "follower_id": 1,
    "target_id": 2
  }
  ```
- **Response:** `FollowerResponse` with id, user_id (follower), target_id
- **Error:** Cannot follow yourself or if already following

#### Unfollow a User
- **DELETE** `/follow/{follower_id}/{target_id}`
- **Response:** `{"message": "Unfollowed successfully"}`

#### Get Followers
- **GET** `/followers/{user_id}`
- **Response:** List of users following the specified user
- **Example:**
  ```json
  [
    {
      "id": 1,
      "user_id": 3,
      "target_id": 1
    }
  ]
  ```

#### Get Following
- **GET** `/following/{user_id}`
- **Response:** List of users that the specified user is following

#### Get User Feed
- **GET** `/posts/feed/{user_id}?limit=50`
- **Response:** Posts from all users that `user_id` is following (ordered by most recent)
- **Query Params:** `limit` (1-100, default 50)

---

## Data Models

### PostResponse
```json
{
  "id": 1,
  "author_id": 1,
  "content": "Post content",
  "time_posted": "2024-01-01T12:00:00"
}
```

### UpdateResponse
```json
{
  "id": 1,
  "user_id": 1,
  "update_text": "Update text",
  "time_posted": "2024-01-01T12:00:00"
}
```

### SMEResponse
```json
{
  "id": 1,
  "name": "Expert Name",
  "category": "Category",
  "latitude": 40.7128,
  "longitude": -74.0060
}
```

### FollowerResponse
```json
{
  "id": 1,
  "user_id": 3,
  "target_id": 1
}
```

---

## Example Usage

### Create and fetch posts:
```bash
# Create a post
curl -X POST "http://localhost:8000/posts" \
  -H "Content-Type: application/json" \
  -d '{"author_id": 1, "content": "Hello World!"}'

# Get all posts
curl "http://localhost:8000/posts?limit=10"
```

### Follow a user and get feed:
```bash
# Follow user 2
curl -X POST "http://localhost:8000/follow" \
  -H "Content-Type: application/json" \
  -d '{"follower_id": 1, "target_id": 2}'

# Get user 1's feed
curl "http://localhost:8000/posts/feed/1?limit=20"
```

### Find nearby SMEs:
```bash
curl "http://localhost:8000/smes/nearby?latitude=40.7128&longitude=-74.0060&radius_km=10"
```

---

## Notes

- Coordinates use latitude/longitude (decimal degrees)
- Distance calculations use the Haversine formula (accurate within ~0.5% for distances < 1000 km)
- All timestamps are in ISO 8601 format
- Database path defaults to `Nexus.db` in the working directory
