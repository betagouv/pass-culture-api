from typing import List

import pytest
from pytest import fixture

from pcapi.core.bookings.models import Booking
from pcapi.core.offers.models import Offer
from pcapi.core.offers.models import Stock
from pcapi.core.users.models import User
from pcapi.models.venue_sql_entity import VenueSQLEntity
from pcapi.sandboxes.scripts.creators.bookings_recap.bookings_recap import save_bookings_recap_sandbox


class BookingsRecapTest:
    @pytest.mark.usefixtures("db_session")
    def test_should_create_bookings_recap_sandbox(self, app: fixture):
        # When
        save_bookings_recap_sandbox()

        # Then
        assert Booking.query.count() == 14
        assert User.query.count() == 4
        assert Offer.query.count() == 6
        assert Stock.query.count() == 6
        assert VenueSQLEntity.query.count() == 4

        assert self._find_bookings_by_user_firstname("Riri") == 4
        assert self._find_bookings_by_user_firstname("Fifi") == 4
        assert self._find_bookings_by_user_firstname("Loulou") == 6

    def _find_bookings_by_user_firstname(self, name: str) -> List[Booking]:
        return Booking.query.join(User).filter(User.firstName == name).count()
