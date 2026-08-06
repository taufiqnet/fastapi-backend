from contextlib import asynccontextmanager
from pathlib import Path
import shutil

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    Depends,
    HTTPException,
)

from fastapi.staticfiles import StaticFiles

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import (
    Post,
    get_async_session,
    create_db_and_tables,
)

# ==========================================================
# Upload Directory
# ==========================================================

UPLOAD_DIR = Path("app/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================================
# Lifespan
# ==========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield


# ==========================================================
# FastAPI
# ==========================================================

app = FastAPI(
    title="PMS API",
    version="1.0.0",
    lifespan=lifespan,
)

# Serve uploaded files
app.mount(
    "/uploads",
    StaticFiles(directory="app/uploads"),
    name="uploads",
)


# ==========================================================
# Home
# ==========================================================

@app.get("/")
async def root():
    return {
        "message": "Welcome to PMS API"
    }


# ==========================================================
# Upload Post
# ==========================================================

@app.post("/posts")
async def create_post(
    caption: str = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
):
    filename = file.filename

    filepath = UPLOAD_DIR / filename

    with filepath.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    post = Post(
        caption=caption,
        url=f"/uploads/{filename}",
        file_type=file.content_type,
        file_name=filename,
    )

    session.add(post)

    await session.commit()

    await session.refresh(post)

    return {
        "message": "Post created successfully",
        "post": post,
    }


# ==========================================================
# Get All Posts
# ==========================================================

@app.get("/posts")
async def get_posts(
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(Post).order_by(Post.created_at.desc())
    )

    posts = result.scalars().all()

    return posts


# ==========================================================
# Get Single Post
# ==========================================================

@app.get("/posts/{post_id}")
async def get_post(
    post_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(Post).where(Post.id == post_id)
    )

    post = result.scalar_one_or_none()

    if post is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )

    return post


# ==========================================================
# Delete Post
# ==========================================================

@app.delete("/posts/{post_id}")
async def delete_post(
    post_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(Post).where(Post.id == post_id)
    )

    post = result.scalar_one_or_none()

    if post is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )

    file_path = Path("app") / post.url.lstrip("/")

    if file_path.exists():
        file_path.unlink()

    await session.delete(post)

    await session.commit()

    return {
        "message": "Post deleted successfully"
    }


# ==========================================================
# Update Caption
# ==========================================================

@app.put("/posts/{post_id}")
async def update_caption(
    post_id: str,
    caption: str = Form(...),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(Post).where(Post.id == post_id)
    )

    post = result.scalar_one_or_none()

    if post is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )

    post.caption = caption

    await session.commit()

    await session.refresh(post)

    return {
        "message": "Caption updated successfully",
        "post": post,
    }


# ==========================================================
# Replace Uploaded File
# ==========================================================

@app.put("/posts/{post_id}/file")
async def update_file(
    post_id: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(Post).where(Post.id == post_id)
    )

    post = result.scalar_one_or_none()

    if post is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )

    # Delete old file
    old_file = Path("app") / post.url.lstrip("/")

    if old_file.exists():
        old_file.unlink()

    filename = file.filename

    filepath = UPLOAD_DIR / filename

    with filepath.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    post.url = f"/uploads/{filename}"
    post.file_name = filename
    post.file_type = file.content_type

    await session.commit()

    await session.refresh(post)

    return {
        "message": "File updated successfully",
        "post": post,
    }