from datetime import datetime
from typing import List

from pcapi.core.offerers.models import Venue
from pcapi.models import db


def update_venue_creation_date() -> None:
    venues: List[Venue] = Venue.query.filter(Venue.dateCreated.is_(None)).order_by(Venue.id).all()
    for venue in venues:
        venue_before_date_created: datetime = (
            Venue.query.order_by(Venue.id.desc())
            .filter(Venue.dateCreated.isnot(None))
            .filter(Venue.id < venue.id)
            .with_entities(Venue.dateCreated)
            .first()[0]
        )
        venue_after_date_created: datetime = (
            Venue.query.order_by(Venue.id.asc())
            .filter(Venue.dateCreated.isnot(None))
            .filter(Venue.id > venue.id)
            .with_entities(Venue.dateCreated)
            .first()[0]
        )
        time_before = datetime.timestamp(venue_before_date_created)
        time_after = datetime.timestamp(venue_after_date_created)
        middle_time = (time_before + time_after) / 2
        middle_datetime = datetime.fromtimestamp(middle_time)
        venue.dateCreated = middle_datetime
        db.session.add(venue)
        db.session.commit()
