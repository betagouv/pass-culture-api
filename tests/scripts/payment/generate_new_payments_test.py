import pytest

import pcapi.core.users.factories as users_factories
from pcapi.model_creators.generic_creators import create_bank_information
from pcapi.model_creators.generic_creators import create_booking
from pcapi.model_creators.generic_creators import create_offerer
from pcapi.model_creators.generic_creators import create_payment
from pcapi.model_creators.generic_creators import create_venue
from pcapi.model_creators.specific_creators import create_offer_with_thing_product
from pcapi.model_creators.specific_creators import create_stock_from_offer
from pcapi.models import ThingType
from pcapi.models.payment import Payment
from pcapi.repository import repository
from pcapi.scripts.payment.batch_steps import generate_new_payments


class GenerateNewPaymentsTest:
    @pytest.mark.usefixtures("db_session")
    def test_records_new_payment_lines_in_database(self, app):
        # Given
        offerer = create_offerer()
        venue = create_venue(offerer)
        offer = create_offer_with_thing_product(venue)
        paying_stock = create_stock_from_offer(offer)
        free_stock = create_stock_from_offer(offer, price=0)
        user = users_factories.UserFactory()
        booking1 = create_booking(user=user, stock=paying_stock, venue=venue, is_used=True)
        booking2 = create_booking(user=user, stock=paying_stock, venue=venue, is_used=True)
        booking3 = create_booking(user=user, stock=paying_stock, venue=venue, is_used=True)
        booking4 = create_booking(user=user, stock=free_stock, venue=venue, is_used=True)
        payment1 = create_payment(booking2, offerer, 10, payment_message_name="ABCD123")

        repository.save(payment1)
        repository.save(booking1, booking3, booking4)

        initial_payment_count = Payment.query.count()

        # When
        generate_new_payments()

        # Then
        assert Payment.query.count() - initial_payment_count == 2

    @pytest.mark.usefixtures("db_session")
    def test_returns_a_tuple_of_pending_and_not_processable_payments(self, app):
        # Given
        offerer1 = create_offerer(siren="123456789")
        offerer2 = create_offerer(siren="987654321")
        repository.save(offerer1)
        bank_information = create_bank_information(
            bic="BDFEFR2LCCB", iban="FR7630006000011234567890189", offerer=offerer1
        )
        venue1 = create_venue(offerer1, siret="12345678912345")
        venue2 = create_venue(offerer2, siret="98765432154321")
        offer1 = create_offer_with_thing_product(venue1)
        offer2 = create_offer_with_thing_product(venue2)
        paying_stock1 = create_stock_from_offer(offer1)
        paying_stock2 = create_stock_from_offer(offer2)
        free_stock1 = create_stock_from_offer(offer1, price=0)
        user = users_factories.UserFactory()
        booking1 = create_booking(user=user, stock=paying_stock1, venue=venue1, is_used=True)
        booking2 = create_booking(user=user, stock=paying_stock1, venue=venue1, is_used=True)
        booking3 = create_booking(user=user, stock=paying_stock2, venue=venue2, is_used=True)
        booking4 = create_booking(user=user, stock=free_stock1, venue=venue1, is_used=True)
        repository.save(booking1, booking2, booking3, booking4, bank_information)

        # When
        pending, not_processable = generate_new_payments()

        # Then
        assert len(pending) == 2
        assert len(not_processable) == 1

    @pytest.mark.usefixtures("db_session")
    def test_reimburses_offerer_if_he_has_more_than_20000_euros_in_bookings_on_several_venues(self, app):
        # Given
        offerer1 = create_offerer(siren="123456789")
        repository.save(offerer1)
        bank_information = create_bank_information(
            bic="BDFEFR2LCCB", iban="FR7630006000011234567890189", offerer=offerer1
        )
        venue1 = create_venue(offerer1, siret="12345678912345")
        venue2 = create_venue(offerer1, siret="98765432154321")
        venue3 = create_venue(offerer1, siret="98123432154321")
        offer1 = create_offer_with_thing_product(venue1)
        offer2 = create_offer_with_thing_product(venue2)
        offer3 = create_offer_with_thing_product(venue3)
        paying_stock1 = create_stock_from_offer(offer1, price=10000)
        paying_stock2 = create_stock_from_offer(offer2, price=10000)
        paying_stock3 = create_stock_from_offer(offer3, price=10000)
        user = users_factories.UserFactory()
        user.deposit.amount = 50000
        repository.save(user.deposit)
        booking1 = create_booking(user=user, stock=paying_stock1, venue=venue1, is_used=True, quantity=1)
        booking2 = create_booking(user=user, stock=paying_stock2, venue=venue2, is_used=True, quantity=1)
        booking3 = create_booking(user=user, stock=paying_stock3, venue=venue3, is_used=True, quantity=1)
        repository.save(booking1, booking2, booking3, bank_information)

        # When
        pending, not_processable = generate_new_payments()

        # Then
        assert len(pending) == 3
        assert len(not_processable) == 0
        assert sum(p.amount for p in pending) == 30000

    @pytest.mark.usefixtures("db_session")
    def test_reimburses_offerer_with_degressive_rate_for_venues_with_bookings_exceeding_20000_euros(self, app):
        # Given
        offerer1 = create_offerer(siren="123456789")
        repository.save(offerer1)
        bank_information = create_bank_information(
            bic="BDFEFR2LCCB", iban="FR7630006000011234567890189", offerer=offerer1
        )
        venue1 = create_venue(offerer1, siret="12345678912345")
        venue2 = create_venue(offerer1, siret="98765432154321")
        venue3 = create_venue(offerer1, siret="98123432154321")
        offer1 = create_offer_with_thing_product(venue1)
        offer2 = create_offer_with_thing_product(venue2)
        offer3 = create_offer_with_thing_product(venue3)
        paying_stock1 = create_stock_from_offer(offer1, price=10000)
        paying_stock2 = create_stock_from_offer(offer2, price=10000)
        paying_stock3 = create_stock_from_offer(offer3, price=30000)
        user = users_factories.UserFactory()
        user.deposit.amount = 50000
        repository.save(user.deposit)
        booking1 = create_booking(user=user, stock=paying_stock1, venue=venue1, is_used=True, quantity=1)
        booking2 = create_booking(user=user, stock=paying_stock2, venue=venue2, is_used=True, quantity=1)
        booking3 = create_booking(user=user, stock=paying_stock3, venue=venue3, is_used=True, quantity=1)
        repository.save(booking1, booking2, booking3, bank_information)

        # When
        pending, not_processable = generate_new_payments()

        # Then
        assert len(pending) == 3
        assert len(not_processable) == 0
        assert sum(p.amount for p in pending) == 48500

    @pytest.mark.usefixtures("db_session")
    def test_full_reimburses_book_product_when_bookings_are_below_20000_euros(self, app):
        # Given
        offerer1 = create_offerer(siren="123456789")
        repository.save(offerer1)
        bank_information = create_bank_information(
            bic="BDFEFR2LCCB", iban="FR7630006000011234567890189", offerer=offerer1
        )
        venue1 = create_venue(offerer1, siret="12345678912345")
        venue2 = create_venue(offerer1, siret="98765432154321")
        offer1 = create_offer_with_thing_product(venue1, thing_type=ThingType.LIVRE_EDITION, url=None)
        offer2 = create_offer_with_thing_product(venue2, thing_type=ThingType.LIVRE_EDITION, url=None)
        paying_stock1 = create_stock_from_offer(offer1, price=10000)
        paying_stock2 = create_stock_from_offer(offer2, price=19990)
        user = users_factories.UserFactory()
        user.deposit.amount = 50000
        repository.save(user.deposit)
        booking1 = create_booking(user=user, stock=paying_stock1, venue=venue1, is_used=True, quantity=1)
        booking2 = create_booking(user=user, stock=paying_stock2, venue=venue2, is_used=True, quantity=1)
        repository.save(booking1, booking2, bank_information)

        # When
        pending, not_processable = generate_new_payments()

        # Then
        assert len(pending) == 2
        assert len(not_processable) == 0
        assert sum(p.amount for p in pending) == 29990

    @pytest.mark.usefixtures("db_session")
    def test_reimburses_95_percent_for_book_product_when_bookings_exceed_20000_euros(self, app):
        # Given
        offerer1 = create_offerer(siren="123456789")
        repository.save(offerer1)
        bank_information = create_bank_information(
            bic="BDFEFR2LCCB", iban="FR7630006000011234567890189", offerer=offerer1
        )
        venue1 = create_venue(offerer1, siret="12345678912345")
        venue2 = create_venue(offerer1, siret="98765432154321")
        venue3 = create_venue(offerer1, siret="98123432154321")
        offer1 = create_offer_with_thing_product(venue1, thing_type=ThingType.LIVRE_EDITION, url=None)
        offer2 = create_offer_with_thing_product(venue2, thing_type=ThingType.LIVRE_EDITION, url=None)
        offer3 = create_offer_with_thing_product(venue3, thing_type=ThingType.LIVRE_EDITION, url=None)
        paying_stock1 = create_stock_from_offer(offer1, price=10000)
        paying_stock2 = create_stock_from_offer(offer2, price=10000)
        paying_stock3 = create_stock_from_offer(offer3, price=30000)
        user = users_factories.UserFactory()
        user.deposit.amount = 50000
        repository.save(user.deposit)
        booking1 = create_booking(user=user, stock=paying_stock1, venue=venue1, is_used=True, quantity=1)
        booking2 = create_booking(user=user, stock=paying_stock2, venue=venue2, is_used=True, quantity=1)
        booking3 = create_booking(user=user, stock=paying_stock3, venue=venue3, is_used=True, quantity=1)
        repository.save(booking1, booking2, booking3, bank_information)

        # When
        pending, not_processable = generate_new_payments()

        # Then
        assert len(pending) == 3
        assert len(not_processable) == 0
        assert sum(p.amount for p in pending) == 48500

    @pytest.mark.usefixtures("db_session")
    def test_reimburses_95_percent_for_book_product_when_bookings_exceed_40000_euros(self, app):
        # Given
        offerer1 = create_offerer(siren="123456789")
        repository.save(offerer1)
        bank_information = create_bank_information(
            bic="BDFEFR2LCCB", iban="FR7630006000011234567890189", offerer=offerer1
        )
        venue1 = create_venue(offerer1, siret="12345678912345")
        venue2 = create_venue(offerer1, siret="98765432154321")
        venue3 = create_venue(offerer1, siret="98123432154321")
        offer1 = create_offer_with_thing_product(venue1, thing_type=ThingType.LIVRE_EDITION, url=None)
        offer2 = create_offer_with_thing_product(venue2, thing_type=ThingType.LIVRE_EDITION, url=None)
        offer3 = create_offer_with_thing_product(venue3, thing_type=ThingType.LIVRE_EDITION, url=None)
        paying_stock1 = create_stock_from_offer(offer1, price=10000)
        paying_stock2 = create_stock_from_offer(offer2, price=10000)
        paying_stock3 = create_stock_from_offer(offer3, price=50000)
        user = users_factories.UserFactory()
        user.deposit.amount = 80000
        repository.save(user.deposit)
        booking1 = create_booking(user=user, stock=paying_stock1, venue=venue1, is_used=True, quantity=1)
        booking2 = create_booking(user=user, stock=paying_stock2, venue=venue2, is_used=True, quantity=1)
        booking3 = create_booking(user=user, stock=paying_stock3, venue=venue3, is_used=True, quantity=1)
        repository.save(booking1, booking2, booking3, bank_information)

        # When
        pending, not_processable = generate_new_payments()

        # Then
        assert len(pending) == 3
        assert len(not_processable) == 0
        assert sum(p.amount for p in pending) == 67500

    @pytest.mark.usefixtures("db_session")
    def test_reimburses_95_percent_for_book_product_when_bookings_exceed_100000_euros(self, app):
        # Given
        offerer1 = create_offerer(siren="123456789")
        repository.save(offerer1)
        bank_information = create_bank_information(
            bic="BDFEFR2LCCB", iban="FR7630006000011234567890189", offerer=offerer1
        )
        venue1 = create_venue(offerer1, siret="12345678912345")
        venue2 = create_venue(offerer1, siret="98765432154321")
        venue3 = create_venue(offerer1, siret="98123432154321")
        offer1 = create_offer_with_thing_product(venue1, thing_type=ThingType.LIVRE_EDITION, url=None)
        offer2 = create_offer_with_thing_product(venue2, thing_type=ThingType.LIVRE_EDITION, url=None)
        offer3 = create_offer_with_thing_product(venue3, thing_type=ThingType.LIVRE_EDITION, url=None)
        paying_stock1 = create_stock_from_offer(offer1, price=10000)
        paying_stock2 = create_stock_from_offer(offer2, price=10000)
        paying_stock3 = create_stock_from_offer(offer3, price=100000)
        user = users_factories.UserFactory()
        user.deposit.amount = 120000
        repository.save(user.deposit)
        booking1 = create_booking(user=user, stock=paying_stock1, venue=venue1, is_used=True, quantity=1)
        booking2 = create_booking(user=user, stock=paying_stock2, venue=venue2, is_used=True, quantity=1)
        booking3 = create_booking(user=user, stock=paying_stock3, venue=venue3, is_used=True, quantity=1)
        repository.save(booking1, booking2, booking3, bank_information)

        # When
        pending, not_processable = generate_new_payments()

        # Then
        assert len(pending) == 3
        assert len(not_processable) == 0
        assert sum(p.amount for p in pending) == 115000
