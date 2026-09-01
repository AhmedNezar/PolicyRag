from fastapi import FastAPI
from contextlib import asynccontextmanager
from infrastructure.dependencies import db
from controllers.api.chat import chat_router
from controllers.api.conversation import conversation_router
from controllers.api.auth import auth_router
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from infrastructure.rate_limit import limiter

@asynccontextmanager
async def lifespan(_: FastAPI):
    # await db.init_db()
    yield
    await db.dispose()

app = FastAPI(lifespan=lifespan)
app.include_router(chat_router)
app.include_router(conversation_router)
app.include_router(auth_router)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.mount("/pages", StaticFiles(directory="pages"), name="pages")

@app.get("/")
async def health_check():
    return {"health": "ok"}
    