import uuid

import pytest

import pcapi.core.bookings.factories as bookings_factories
import pcapi.core.payments.factories as payments_factories
import pcapi.core.users.factories as users_factories
from pcapi.model_creators.generic_creators import create_bank_information
from pcapi.model_creators.generic_creators import create_booking
from pcapi.model_creators.generic_creators import create_offerer
from pcapi.model_creators.generic_creators import create_payment
from pcapi.model_creators.generic_creators import create_payment_message
from pcapi.model_creators.generic_creators import create_venue
from pcapi.model_creators.specific_creators import create_offer_with_thing_product
from pcapi.model_creators.specific_creators import create_stock_from_offer
from pcapi.models.bank_information import BankInformationStatus
from pcapi.models.payment_status import PaymentStatus
from pcapi.models.payment_status import TransactionStatus
from pcapi.repository import payment_queries
from pcapi.repository import repository


class FindErrorPaymentsTest:
    @pytest.mark.usefixtures("db_session")
    def test_returns_payments_with_last_payment_status_error(self, app):
        # Given
        user = users_factories.UserFactory()
        booking = create_booking(user=user)
        error_payment1 = create_payment(
            booking, booking.stock.offer.venue.managingOfferer, 10, status=TransactionStatus.ERROR
        )
        error_payment2 = create_payment(
            booking, booking.stock.offer.venue.managingOfferer, 10, status=TransactionStatus.ERROR
        )
        pending_payment = create_payment(booking, booking.stock.offer.venue.managingOfferer, 10)
        repository.save(error_payment1, error_payment2, pending_payment)

        # When
        payments = payment_queries.find_error_payments()

        # Then
        assert len(payments) == 2
        for payment in payments:
            assert payment.currentStatus.status == TransactionStatus.ERROR

    @pytest.mark.usefixtures("db_session")
    def test_does_not_return_payment_if_has_status_error_but_not_last(self, app):
        # Given
        user = users_factories.UserFactory()
        booking = create_booking(user=user)
        error_payment = create_payment(booking, booking.stock.offer.venue.managingOfferer, 10)
        pending_payment = create_payment(booking, booking.stock.offer.venue.managingOfferer, 10)
        error_status = PaymentStatus()
        error_status.status = TransactionStatus.ERROR
        sent_status = PaymentStatus()
        sent_status.status = TransactionStatus.SENT
        error_payment.statuses.extend([error_status, sent_status])
        repository.save(error_payment, pending_payment)

        # When
        payments = payment_queries.find_error_payments()

        # Then
        assert payments == []


class FindRetryPaymentsTest:
    @pytest.mark.usefixtures("db_session")
    def test_returns_payments_with_last_payment_status_retry(self, app):
        # Given
        user = users_factories.UserFactory()
        booking = create_booking(user=user)
        offerer = booking.stock.offer.venue.managingOfferer
        retry_payment1 = create_payment(booking, offerer, 10, status=TransactionStatus.RETRY)
        retry_payment2 = create_payment(booking, offerer, 10, status=TransactionStatus.RETRY)
        pending_payment = create_payment(booking, offerer, 10, status=TransactionStatus.PENDING)
        repository.save(retry_payment1, retry_payment2, pending_payment)

        # When
        payments = payment_queries.find_retry_payments()

        # Then
        assert len(payments) == 2
        for payment in payments:
            assert payment.currentStatus.status == TransactionStatus.RETRY

    @pytest.mark.usefixtures("db_session")
    def test_does_not_return_payment_if_has_status_retry_but_not_last(self, app):
        # Given
        user = users_factories.UserFactory()
        booking = create_booking(user=user)
        payment = create_payment(booking, booking.stock.offer.venue.managingOfferer, 10)
        payment = create_payment(booking, booking.stock.offer.venue.managingOfferer, 10)
        pending_payment = create_payment(booking, booking.stock.offer.venue.managingOfferer, 10)
        retry_status = PaymentStatus()
        retry_status.status = TransactionStatus.RETRY
        sent_status = PaymentStatus()
        sent_status.status = TransactionStatus.SENT
        payment.statuses.extend([retry_status, sent_status])
        repository.save(payment, pending_payment)

        # When
        payments = payment_queries.find_retry_payments()

        # Then
        assert payments == []


class FindPaymentsByMessageTest:
    @pytest.mark.usefixtures("db_session")
    def test_returns_payments_matching_message(self, app):
        # given
        user = users_factories.UserFactory()
        booking = create_booking(user=user)
        offerer = booking.stock.offer.venue.managingOfferer
        transaction1 = create_payment_message(name="XML1")
        transaction2 = create_payment_message(name="XML2")
        transaction3 = create_payment_message(name="XML3")
        uuid1, uuid2, uuid3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        payments = [
            create_payment(booking, offerer, 5, transaction_end_to_end_id=uuid1, payment_message=transaction1),
            create_payment(booking, offerer, 5, transaction_end_to_end_id=uuid2, payment_message=transaction2),
            create_payment(booking, offerer, 5, transaction_end_to_end_id=uuid1, payment_message=transaction3),
            create_payment(booking, offerer, 5, transaction_end_to_end_id=uuid3, payment_message=transaction1),
            create_payment(booking, offerer, 5, transaction_end_to_end_id=uuid1, payment_message=transaction1),
        ]
        repository.save(*payments)

        # when
        matching_payments = payment_queries.find_payments_by_message("XML1")

        # then
        assert len(matching_payments) == 3
        for payment in matching_payments:
            assert payment.paymentMessageName == "XML1"

    @pytest.mark.usefixtures("db_session")
    def test_returns_nothing_if_message_is_not_matched(self, app):
        # given
        user = users_factories.UserFactory()
        booking = create_booking(user=user)
        offerer = booking.stock.offer.venue.managingOfferer
        message1 = create_payment_message(name="XML1")
        message2 = create_payment_message(name="XML2")
        message3 = create_payment_message(name="XML3")
        uuid1, uuid2, uuid3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        payments = [
            create_payment(booking, offerer, 5, transaction_end_to_end_id=uuid1, payment_message=message1),
            create_payment(booking, offerer, 5, transaction_end_to_end_id=uuid2, payment_message=message2),
            create_payment(booking, offerer, 5, transaction_end_to_end_id=uuid3, payment_message=message3),
        ]
        repository.save(*payments)

        # when
        matching_payments = payment_queries.find_payments_by_message("unknown message")

        # then
        assert matching_payments == []


class GeneratePayementsByMessageIdTest:
    @pytest.mark.usefixtures("db_session")
    def test_only_returns_payments_with_given_message(self, app):
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
        payment1 = create_payment(booking1, offerer, 10, payment_message_name="ABCD123")
        payment2 = create_payment(booking2, offerer, 10, payment_message_name="EFGH456")
        repository.save(payment1, payment2, booking3, booking4)

        # When
        payements_by_id = payment_queries.get_payments_by_message_id("ABCD123")

        # Then
        assert len(payements_by_id) == 1
        assert payements_by_id[0].paymentMessage.name == "ABCD123"


class FindNotProcessableWithBankInformationTest:
    @pytest.mark.usefixtures("db_session")
    def test_should_not_return_payments_to_retry_if_no_bank_information(self, app):
        # Given
        offerer = create_offerer()
        user = users_factories.UserFactory()
        venue = create_venue(offerer)
        stock = create_stock_from_offer(create_offer_with_thing_product(venue), price=0)
        booking = create_booking(user=user, stock=stock)
        not_processable_payment = create_payment(
            booking, offerer, 10, status=TransactionStatus.NOT_PROCESSABLE, iban="CF13QSDFGH456789", bic="QSDFGH8Z555"
        )
        repository.save(not_processable_payment)

        # When
        payments_to_retry = payment_queries.find_not_processable_with_bank_information()

        # Then
        assert payments_to_retry == []

    @pytest.mark.usefixtures("db_session")
    def test_should_return_payment_to_retry_if_bank_information_linked_to_offerer_and_current_status_is_not_processable(
        self, app
    ):
        # Given
        offerer = create_offerer()
        user = users_factories.UserFactory()
        venue = create_venue(offerer)
        stock = create_stock_from_offer(create_offer_with_thing_product(venue), price=0)
        booking = create_booking(user=user, stock=stock)
        not_processable_payment = create_payment(
            booking, offerer, 10, status=TransactionStatus.NOT_PROCESSABLE, iban="CF13QSDFGH456789", bic="QSDFGH8Z555"
        )
        bank_information = create_bank_information(offerer=offerer)
        repository.save(not_processable_payment, bank_information)

        # When
        payments_to_retry = payment_queries.find_not_processable_with_bank_information()

        # Then
        assert not_processable_payment in payments_to_retry

    @pytest.mark.usefixtures("db_session")
    def test_should_not_return_payments_to_retry_if_bank_information_linked_to_offerer_and_current_status_is_not_not_processable(
        self, app
    ):
        # Given
        offerer = create_offerer()
        user = users_factories.UserFactory()
        venue = create_venue(offerer)
        stock = create_stock_from_offer(create_offer_with_thing_product(venue), price=0)
        booking = create_booking(user=user, stock=stock)
        not_processable_payment = create_payment(
            booking, offerer, 10, status=TransactionStatus.NOT_PROCESSABLE, iban="CF13QSDFGH456789", bic="QSDFGH8Z555"
        )
        bank_information = create_bank_information(offerer=offerer)
        repository.save(not_processable_payment, bank_information)
        not_processable_payment.setStatus(TransactionStatus.SENT)
        repository.save(not_processable_payment)

        # When
        payments_to_retry = payment_queries.find_not_processable_with_bank_information()

        # Then
        assert payments_to_retry == []

    @pytest.mark.usefixtures("db_session")
    def test_should_not_return_payment_to_retry_if_bank_information_status_is_not_accepted(self, app):
        # Given
        offerer = create_offerer()
        user = users_factories.UserFactory()
        venue = create_venue(offerer)
        stock = create_stock_from_offer(create_offer_with_thing_product(venue), price=0)
        booking = create_booking(user=user, stock=stock)
        not_processable_payment = create_payment(
            booking, offerer, 10, status=TransactionStatus.NOT_PROCESSABLE, iban="CF13QSDFGH456789", bic="QSDFGH8Z555"
        )
        bank_information = create_bank_information(venue=venue, iban=None, bic=None, status=BankInformationStatus.DRAFT)
        repository.save(not_processable_payment, bank_information)

        # When
        payments_to_retry = payment_queries.find_not_processable_with_bank_information()

        # Then
        assert payments_to_retry == []

    @pytest.mark.usefixtures("db_session")
    def test_should_return_payment_to_retry_if_bank_information_linked_to_venue_and_current_status_is_not_processable(
        self, app
    ):
        # Given
        offerer = create_offerer()
        user = users_factories.UserFactory()
        venue = create_venue(offerer)
        stock = create_stock_from_offer(create_offer_with_thing_product(venue), price=0)
        booking = create_booking(user=user, stock=stock)
        not_processable_payment = create_payment(
            booking, offerer, 10, status=TransactionStatus.NOT_PROCESSABLE, iban="CF13QSDFGH456789", bic="QSDFGH8Z555"
        )
        bank_information = create_bank_information(venue=venue)
        repository.save(not_processable_payment, bank_information)

        # When
        payments_to_retry = payment_queries.find_not_processable_with_bank_information()

        # Then
        assert not_processable_payment in payments_to_retry


@pytest.mark.usefixtures("db_session")
def test_has_payment():
    booking = bookings_factories.BookingFactory()
    assert not payment_queries.has_payment(booking)

    payments_factories.PaymentFactory(booking=booking)
    assert payment_queries.has_payment(booking)
