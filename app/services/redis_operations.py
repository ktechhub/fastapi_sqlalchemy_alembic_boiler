from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

from app.models import get_model_class
from ..core.loggers import redis_logger as logger
from ..database.get_session import AsyncSessionLocal


async def perform_operation(message: dict):
    async with AsyncSessionLocal() as db:
        model_name = message["model"]
        operation = message["operation"]
        data = message["data"]

        model_class = get_model_class(model_name)
        if not model_class:
            logger.error(f"Model {model_name} not found.")
            return False

        try:
            if operation == "insert":
                new_record = model_class(**data)
                db.add(new_record)
                await db.commit()
                await db.refresh(new_record)
                logger.info(f"Inserted data into {model_name.lower()}s: {new_record}")

            elif operation == "update":
                stmt = select(model_class).where(model_class.id == data["id"])
                result = await db.execute(stmt)
                record = result.scalars().first()
                if record:
                    for key, value in data.items():
                        setattr(record, key, value)
                    await db.commit()
                    await db.refresh(record)
                    logger.info(f"Updated data {record.id} in {model_name.lower()}s")

            elif operation == "delete":
                stmt = select(model_class).where(model_class.id == data["id"])
                result = await db.execute(stmt)
                record = result.scalars().first()
                if record:
                    await db.delete(record)
                    await db.commit()
                    logger.info(f"Deleted data {record.id} from {model_name.lower()}s")

            else:
                logger.info(f"Invalid operation {operation} for {message}")
                return False

            return True

        except SQLAlchemyError as e:
            logger.error(f"Error executing operation for {message}: {e}")
            return False

        finally:
            await db.close()
