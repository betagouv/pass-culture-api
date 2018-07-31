""" stock """
from datetime import datetime, timedelta
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import BigInteger,\
                       CheckConstraint,\
                       Column,\
                       DateTime,\
                       DDL,\
                       event,\
                       ForeignKey,\
                       Integer,\
                       Numeric    
from sqlalchemy.orm import relationship

from models.db import Model
from models.deactivable_mixin import DeactivableMixin
from models.event_occurrence import EventOccurrence
from models.pc_object import PcObject
from models.providable_mixin import ProvidableMixin


class Stock(PcObject,
            Model,
            DeactivableMixin,
            ProvidableMixin):

    id = Column(BigInteger,
                primary_key=True,
                autoincrement=True)

    # an stock is either linked to a thing or to an eventOccurrence

    dateModified = Column(DateTime,
                          nullable=False,
                          default=datetime.utcnow)

    eventOccurrenceId = Column(BigInteger,
                              ForeignKey("event_occurrence.id"),
                              CheckConstraint('"eventOccurrenceId" IS NOT NULL OR "occasionId" IS NOT NULL',
                                              name='check_stock_has_event_occurrence_or_occasion'),
                              index=True,
                              nullable=True)

    eventOccurrence = relationship('EventOccurrence',
                                  foreign_keys=[eventOccurrenceId],
                                  backref='stocks')

    offerId = Column(BigInteger,
                        ForeignKey('offer.id'),
                        index=True,
                        nullable=True)

    offer = relationship('Offer',
                            foreign_keys=[offerId],
                            backref='stocks')

    price = Column(Numeric(10, 2),
                   nullable=False)

    available = Column(Integer,
                       index=True,
                       nullable=True)

    # TODO: add pmr
    #pmrGroupSize = Column(db.Integer,
    #                         nullable=False,
    #                         default=1)

    groupSize = Column(Integer,
                       nullable=False,
                       default=1)

    bookingLimitDatetime = Column(DateTime,
                                  nullable=True)

    bookingRecapSent = Column(DateTime,
                              nullable=True)

    @property
    def resolvedOffer(self):
        return self.offer or self.eventOccurrence.offer


@event.listens_for(Stock, 'before_insert')
def page_defaults(mapper, configuration, target):
    # `bookingLimitDatetime` defaults to midnight before `beginningDatetime`
    # for eventOccurrences
    if target.eventOccurrenceId and not target.bookingLimitDatetime:
        eventOccurrence = target.eventOccurrence
        if eventOccurrence is None:
            eventOccurrence = EventOccurrence\
                                      .query\
                                      .filter_by(id=target.eventOccurrenceId)\
                                      .first_or_404()
        target.bookingLimitDatetime = eventOccurrence.beginningDatetime\
                                                    .replace(hour=23)\
                                                    .replace(minute=59) - timedelta(days=3)


Stock.trig_ddl = """
    CREATE OR REPLACE FUNCTION check_stock()
    RETURNS TRIGGER AS $$
    BEGIN
      IF NOT NEW.available IS NULL AND
      ((SELECT COUNT(*) FROM booking WHERE "stockId"=NEW.id) > NEW.available) THEN
        RAISE EXCEPTION 'available_too_low'
              USING HINT = 'stock.available cannot be lower than number of bookings';
      END IF;

      IF NOT NEW."bookingLimitDatetime" IS NULL AND
      (NEW."bookingLimitDatetime" > (SELECT "beginningDatetime" FROM event_occurrence WHERE id=NEW."eventOccurrenceId")) THEN

      RAISE EXCEPTION 'bookingLimitDatetime_too_late'
      USING HINT = 'stock.bookingLimitDatetime after event_occurrence.beginningDatetime';
      END IF;

      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    DROP TRIGGER IF EXISTS stock_update ON stock;
    CREATE CONSTRAINT TRIGGER stock_update AFTER INSERT OR UPDATE
    ON stock
    FOR EACH ROW EXECUTE PROCEDURE check_stock()
    """
event.listen(Stock.__table__,
             'after_create',
             DDL(Stock.trig_ddl))
