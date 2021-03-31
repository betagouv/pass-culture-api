from pydantic.class_validators import validator

from pcapi.routes.native.utils import convert_to_cent
from pcapi.serialization.utils import to_camel

from . import BaseModel


class SettingsResponse(BaseModel):
    deposit_amount: int
    _convert_deposit_amount = validator("deposit_amount", pre=True, allow_reuse=True)(convert_to_cent)

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True
