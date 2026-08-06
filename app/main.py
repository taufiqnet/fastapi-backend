from fastapi import FastAPI

app = FastAPI(
    title="PMS API",
    version="1.0.0"
)

text_posts = [
    {
        "id": 1,
        "title": "Post 1",
        "content": "This is the first post"
    },
    {
        "id": 2,
        "title": "Post 2",
        "content": "This is the second post"
    }
]

@app.get("/")
async def root():
    return {"message": "Welcome to PMS API"}

@app.get("/posts")
def get_all_posts():
    return text_posts

@app.get("/posts/{id}")
def get_post(id: int):
    for post in text_posts:
        if post["id"] == id:
            return post

    raise HTTPException(status_code=404, detail="Post not found")