from sqlalchemy import Column, String, Text, Integer

from pcapi.models.db import Model
from pcapi.models.pc_object import PcObject


class Criterion(PcObject, Model):
    name = Column(String(140), nullable=False, unique=True)

    description = Column(Text, nullable=True)

    scoreDelta = Column(Integer, nullable=False)

    def __repr__(self):
        return '%s' % self.name