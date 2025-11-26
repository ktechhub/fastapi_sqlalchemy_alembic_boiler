import asyncio
from dotenv import load_dotenv

load_dotenv()

from app.services.redis_push import redis_push_async


async def main():
    for i in range(10):
        await redis_push_async(
            {"queue_name": "telegram", "data": {"message": f"Hello, world! {i+1}"}}
        )


if __name__ == "__main__":
    asyncio.run(main())
