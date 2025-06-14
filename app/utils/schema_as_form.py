import inspect
from typing import Type
from fastapi import Form
from pydantic import BaseModel


def as_form(cls: Type[BaseModel]):
    """
    Adds an as_form class method to decorated models. The as_form class method
    can be used with FastAPI endpoints
    """
    new_params = [
        inspect.Parameter(
            (
                field.alias if field.alias is not None else field_info[0]
            ),  # Use field name indirectly
            inspect.Parameter.POSITIONAL_ONLY,
            default=(Form(field.default) if not field.is_required() else Form(...)),
            annotation=field.annotation,
        )
        for field_info, field in zip(
            cls.model_fields.items(), cls.model_fields.values()
        )
    ]

    async def _as_form(**data):
        return cls(**data)

    sig = inspect.signature(_as_form)
    sig = sig.replace(parameters=new_params)
    _as_form.__signature__ = sig
    setattr(cls, "as_form", _as_form)
    return cls
