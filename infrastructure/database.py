from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from entities.base import Base
from config import Settings

class Database:
    def __init__(self, settings: Settings):
        self.database_url = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@localhost:5432/{settings.POSTGRES_DB}"
        self.engine = create_async_engine(self.database_url, echo=True)
        self.async_session = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            autoflush=False,
            expire_on_commit=False,
        )
    
    # async def init_db(self) -> None:
    #     async with self.engine.begin() as conn:
    #         await conn.run_sync(Base.metadata.drop_all)
    #         await conn.run_sync(Base.metadata.create_all)
            
    async def dispose(self) -> None:
        await self.engine.dispose()
            
        
    
