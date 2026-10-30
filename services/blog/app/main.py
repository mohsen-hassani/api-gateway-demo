from common.app import create_app
from common.errors import ApiError
from common.seed import POSTS
from common.settings import Settings


def create(settings: Settings | None = None):
    settings = settings or Settings.from_env("blog-service")
    app = create_app(settings)

    @app.get("/posts")
    async def list_posts():
        summaries = [{k: v for k, v in post.items() if k != "body"} for post in POSTS]
        return {"posts": summaries}

    @app.get("/posts/{post_id}")
    async def get_post(post_id: int):
        for post in POSTS:
            if post["id"] == post_id:
                return post
        raise ApiError(404, "post_not_found", f"No post with id {post_id}")

    return app


app = create()
