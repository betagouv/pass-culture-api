import pytest

import pcapi.core.offers.factories as offers_factories
from pcapi.core.offers.models import Offer
from pcapi.utils.human_ids import humanize

from tests.conftest import TestClient


@pytest.mark.usefixtures("db_session")
class Returns204:
    def when_activating_existing_offers(self, app):
        # Given
        offer1 = offers_factories.OfferFactory(isActive=False)
        venue = offer1.venue
        offer2 = offers_factories.OfferFactory(venue=venue, isActive=False)
        offerer = venue.managingOfferer
        offers_factories.UserOffererFactory(user__email="pro@example.com", offerer=offerer)

        # When
        client = TestClient(app.test_client()).with_auth("pro@example.com")
        data = {"ids": [humanize(offer1.id), humanize(offer2.id)], "isActive": True}
        response = client.patch("/offers/active-status", json=data)

        # Then
        assert response.status_code == 204
        assert Offer.query.get(offer1.id).isActive
        assert Offer.query.get(offer2.id).isActive

    def when_deactivating_existing_offers(self, app):
        # Given
        offer1 = offers_factories.OfferFactory()
        venue = offer1.venue
        offer2 = offers_factories.OfferFactory(venue=venue)
        offerer = venue.managingOfferer
        offers_factories.UserOffererFactory(user__email="pro@example.com", offerer=offerer)

        # When
        client = TestClient(app.test_client()).with_auth("pro@example.com")
        data = {"ids": [humanize(offer1.id), humanize(offer2.id)], "isActive": False}
        response = client.patch("/offers/active-status", json=data)

        # Then
        assert response.status_code == 204
        assert not Offer.query.get(offer1.id).isActive
        assert not Offer.query.get(offer2.id).isActive
