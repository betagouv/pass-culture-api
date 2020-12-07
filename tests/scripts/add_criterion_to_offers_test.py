from unittest import mock

import pytest

import pcapi.core.offers.factories as offers_factories
from pcapi.scripts.add_criterion_to_offers import add_criterion_to_offers


@pytest.mark.usefixtures("db_session")
class AddCriterionToOffersTest:
    @mock.patch("pcapi.connectors.redis.add_offer_id")
    def test_add_criterion(self, mocked_add_offer_id):
        # Given
        isbns = ["2-221-00164-8", "9782234012530"]
        offer1 = offers_factories.OfferFactory(extraData={"isbn": "2221001648"})
        offer2 = offers_factories.OfferFactory(extraData={"isbn": "9782234012530"})
        inactive_offer = offers_factories.OfferFactory(extraData={"isbn": "9782234012530"}, isActive=False)
        unmatched_offer = offers_factories.OfferFactory()
        criterion_name = "Pretty good books"
        criterion = offers_factories.CriterionFactory(name=criterion_name)

        # When
        add_criterion_to_offers(criterion_name, isbns)

        # Then
        assert offer1.criteria == [criterion]
        assert offer2.criteria == [criterion]
        assert not inactive_offer.criteria
        assert not unmatched_offer.criteria
        # fmt: off
        reindexed_offer_ids = {
            mocked_add_offer_id.call_args_list[i][1]["offer_id"]
            for i in range(mocked_add_offer_id.call_count)
        }
        # fmt: on
        assert reindexed_offer_ids == {offer1.id, offer2.id}