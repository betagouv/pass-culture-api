from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from pcapi.models import PcObject
from pcapi.models.db import Model


class VenueType(PcObject, Model):
    label = Column(String(100), nullable=False)

    venue = relationship('VenueSQLEntity')