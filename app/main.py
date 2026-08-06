import uuid
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
from app.schemas import PostResponse

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
# Shared upload validation
# ==========================================================

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
}


async def validate_and_save_upload(file: UploadFile) -> tuple[str, str]:
    """Validate an incoming image UploadFile, save it to disk with a
    unique filename, and return (filename, content_type)."""

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected.",
        )

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG, WEBP and GIF images are allowed.",
        )

    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Invalid image extension.",
        )

    contents = await file.read()

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Image size cannot exceed 10 MB.",
        )

    await file.seek(0)

    # Always generate our own filename - never trust the client's
    # filename (avoids collisions and path traversal issues).
    filename = f"{uuid.uuid4()}{extension}"
    filepath = UPLOAD_DIR / filename

    with filepath.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return filename, file.content_type


# ==========================================================
# Upload Post
# ==========================================================

@app.post("/posts", response_model=PostResponse)
async def create_post(
    caption: str = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
):
    filename, content_type = await validate_and_save_upload(file)

    post = Post(
        caption=caption,
        url=f"/uploads/{filename}",
        file_type=content_type,
        file_name=filename,
    )

    session.add(post)

    await session.commit()

    await session.refresh(post)

    return post


# ==========================================================
# Get All Posts
# ==========================================================

@app.get("/posts", response_model=list[PostResponse])
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

@app.get("/posts/{post_id}", response_model=PostResponse)
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

    # Delete uploaded file
    file_path = UPLOAD_DIR / post.file_name

    if file_path.exists():
        file_path.unlink()

    # Delete database record
    await session.delete(post)
    await session.commit()

    return {
        "message": "Post deleted successfully"
    }


# ==========================================================
# Update Caption
# ==========================================================

@app.put("/posts/{post_id}", response_model=PostResponse)
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

    return post


# ==========================================================
# Replace Uploaded File
# ==========================================================

@app.put("/posts/{post_id}/file", response_model=PostResponse)
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

    filename, content_type = await validate_and_save_upload(file)

    # Delete old file (only after the new one is validated/saved,
    # so a bad upload never destroys the existing image)
    old_file = Path("app") / post.url.lstrip("/")

    if old_file.exists():
        old_file.unlink()

    post.url = f"/uploads/{filename}"
    post.file_name = filename
    post.file_type = content_type

    await session.commit()

    await session.refresh(post)

    return post