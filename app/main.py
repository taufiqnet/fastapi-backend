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
    }
]

@app.get("/")
async def root():
    return {"message": "Welcome to PMS API"}

@app.get("/posts")
def get_all_posts():
    return text_posts