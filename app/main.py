from fastapi import FastAPI, HTTPException
from app.schemas import PostCreate
from app.database import get_async_session, Post, create_db_and_tables, get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield

app = FastAPI(
    title="PMS API",
    version="1.0.0",
    lifespan=lifespan,
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


@app.post("/posts")
def create_post(post: PostCreate):
    new_id = max(p["id"] for p in text_posts) + 1

    new_post = {
        "id": new_id,
        "title": post.title,
        "content": post.content
    }

    text_posts.append(new_post)

    return new_post

@app.delete("/posts/{id}")
def delete_post(id: int):
    for index, post in enumerate(text_posts):
        if post["id"] == id:
            deleted_post = text_posts.pop(index)
            return {
                "message": "Post deleted successfully",
                "post": deleted_post
            }

    raise HTTPException(status_code=404, detail="Post not found")