from datetime import datetime, timedelta
from unittest import mock

from flask import current_app as app
import pytest

from pcapi.core.bookings import api
from pcapi.core.bookings import factories
from pcapi.core.bookings import exceptions
import pcapi.core.offers.factories as offers_factories
import pcapi.core.payments.factories as payments_factories
import pcapi.core.recommendations.factories as recommendations_factories
import pcapi.core.users.factories as users_factories
from pcapi.models import api_errors
from pcapi.models import offer_type
from pcapi.models.feature import override_features
from pcapi.utils.token import random_token


@pytest.mark.usefixtures("db_session")
class BookOfferTest:
    @mock.patch('pcapi.infrastructure.services.notification.mailjet_notification_service.send_raw_email')
    @mock.patch('pcapi.connectors.redis.add_offer_id')
    def test_create_booking(self, mocked_add_offer_id, mocked_send_raw_email):
        user = users_factories.UserFactory()
        stock = offers_factories.StockFactory(price=10)

        booking = api.book_offer(beneficiary=user, stock=stock, quantity=1)

        assert booking.quantity == 1
        assert booking.amount == 10
        assert booking.stock == stock
        assert booking.recommendation is None
        assert len(booking.token) == 6
        assert not booking.isCancelled
        assert not booking.isUsed

        mocked_add_offer_id.assert_called_once_with(client=app.redis_client, offer_id=stock.offer.id)

        email_data1 = mocked_send_raw_email.call_args_list[0][1]['data']
        assert email_data1['MJ-TemplateID'] == 1095029  # to offerer
        email_data2 = mocked_send_raw_email.call_args_list[1][1]['data']
        assert email_data2['MJ-TemplateID'] == 1163067  # to beneficiary

    def test_create_booking_with_recommendation(self):
        user = users_factories.UserFactory()
        stock = offers_factories.StockFactory()
        recommendation = recommendations_factories.RecommendationFactory(user=user, offer=stock.offer)

        booking = api.book_offer(
            beneficiary=user,
            stock=stock,
            quantity=1,
            recommendation=recommendation,
        )

        assert booking.recommendation == recommendation

    @override_features(SYNCHRONIZE_ALGOLIA=False)
    @mock.patch('pcapi.connectors.redis.add_offer_id')
    def test_do_not_sync_algolia_if_feature_is_disabled(self, mocked_add_offer_id):
        user = users_factories.UserFactory()
        stock = offers_factories.StockFactory()

        api.book_offer(beneficiary=user, stock=stock, quantity=1)
        mocked_add_offer_id.assert_not_called()

    def test_raise_if_is_admin(self):
        user = users_factories.UserFactory(canBookFreeOffers=False, isAdmin=True)
        stock = offers_factories.StockFactory()

        with pytest.raises(api_errors.ApiErrors) as exc:
            api.book_offer(beneficiary=user, stock=stock, quantity=1)
        assert 'insufficientFunds' in exc.value.errors

    def test_raise_if_pro_user(self):
        user = users_factories.UserFactory(canBookFreeOffers=False, isAdmin=False)
        stock = offers_factories.StockFactory()

        with pytest.raises(api_errors.ApiErrors) as exc:
            api.book_offer(beneficiary=user, stock=stock, quantity=1)
        assert 'insufficientFunds' in exc.value.errors

    def test_raise_if_no_more_stock(self):
        booking = factories.BookingFactory(stock__quantity=1)
        with pytest.raises(exceptions.StockIsNotBookable):
            api.book_offer(
                beneficiary=users_factories.UserFactory(),
                stock=booking.stock,
                quantity=1,
            )

    def test_raise_if_user_has_already_booked(self):
        booking = factories.BookingFactory()
        with pytest.raises(exceptions.OfferIsAlreadyBooked):
            api.book_offer(
                beneficiary=booking.user,
                stock=booking.stock,
                quantity=1,
            )

    def test_raise_if_user_has_no_more_money(self):
        stock = offers_factories.StockFactory(price=800)
        with pytest.raises(exceptions.UserHasInsufficientFunds):
            api.book_offer(
                beneficiary=users_factories.UserFactory(),
                stock=stock,
                quantity=1,
            )

    def test_raise_if_invalid_quantity(self):
        with pytest.raises(exceptions.QuantityIsInvalid):
            api.book_offer(
                beneficiary=users_factories.UserFactory(),
                stock=offers_factories.StockFactory(),
                quantity=2,
            )


@pytest.mark.usefixtures("db_session")
class CancelByBeneficiaryTest:
    @mock.patch('pcapi.infrastructure.services.notification.mailjet_notification_service.send_raw_email')
    def test_cancel_booking(self, mocked_send_raw_email):
        booking = factories.BookingFactory()

        api.cancel_booking_by_beneficiary(booking.user, booking)

        assert booking.isCancelled
        email_data1 = mocked_send_raw_email.call_args_list[0][1]['data']
        assert email_data1['Mj-TemplateID'] == 1091464  # to beneficiary
        email_data2 = mocked_send_raw_email.call_args_list[1][1]['data']
        assert email_data2['MJ-TemplateID'] == 780015  # to offerer

    @override_features(SYNCHRONIZE_ALGOLIA=False)
    @mock.patch('pcapi.connectors.redis.add_offer_id')
    def test_do_not_sync_algolia_if_feature_is_disabled(self, mocked_add_offer_id):
        booking = factories.BookingFactory()
        api.cancel_booking_by_beneficiary(booking.user, booking)
        mocked_add_offer_id.assert_not_called()

    def test_raise_if_booking_is_already_used(self):
        booking = factories.BookingFactory(isUsed=True)

        with pytest.raises(exceptions.BookingIsAlreadyUsed):
            api.cancel_booking_by_beneficiary(booking.user, booking)
        assert not booking.isCancelled

    def test_raise_if_too_late_to_cancel(self):
        booking = factories.BookingFactory(
            stock__beginningDatetime=datetime.now() + timedelta(days=1),
        )
        with pytest.raises(exceptions.EventHappensInLessThan72Hours):
            api.cancel_booking_by_beneficiary(booking.user, booking)
        assert not booking.isCancelled

    def test_raise_if_trying_to_cancel_someone_else_s_booking(self):
        booking = factories.BookingFactory()
        other_user = users_factories.UserFactory()
        with pytest.raises(exceptions.BookingDoesntExist):
            api.cancel_booking_by_beneficiary(other_user, booking)
        assert not booking.isCancelled


@pytest.mark.usefixtures("db_session")
class CancelByOffererTest:
    def test_cancel(self):
        booking = factories.BookingFactory()
        api.cancel_booking_by_offerer(booking)
        assert booking.isCancelled

    def test_raise_if_already_cancelled(self):
        booking = factories.BookingFactory(isCancelled=True)
        with pytest.raises(api_errors.ResourceGoneError):
            api.cancel_booking_by_offerer(booking)
        assert booking.isCancelled  # unchanged

    def test_raise_if_already_used(self):
        booking = factories.BookingFactory(isUsed=True)
        with pytest.raises(api_errors.ForbiddenError):
            api.cancel_booking_by_offerer(booking)
        assert booking.isUsed  # unchanged
        assert not booking.isCancelled


@pytest.mark.usefixtures("db_session")
class MarkAsUsedTest:
    def test_mark_as_used(self):
        booking = factories.BookingFactory()
        api.mark_as_used(booking)
        assert booking.isUsed

    def test_mark_as_used_when_stock_starts_soon(self):
        booking = factories.BookingFactory(
            stock__beginningDatetime=datetime.now() + timedelta(days=1)
        )
        api.mark_as_used(booking)
        assert booking.isUsed

    def test_raise_if_already_used(self):
        booking = factories.BookingFactory(isUsed=True)
        with pytest.raises(api_errors.ResourceGoneError):
            api.mark_as_used(booking)
        assert booking.isUsed  # unchanged

    def test_raise_if_cancelled(self):
        booking = factories.BookingFactory(isCancelled=True)
        with pytest.raises(api_errors.ResourceGoneError):
            api.mark_as_used(booking)
        assert not booking.isUsed

    def test_raise_if_too_soon_to_mark_as_used(self):
        booking = factories.BookingFactory(
            stock__beginningDatetime=datetime.now() + timedelta(days=4)
        )
        with pytest.raises(api_errors.ForbiddenError):
            api.mark_as_used(booking)
        assert not booking.isUsed


@pytest.mark.usefixtures("db_session")
class MarkAsUnusedTest:
    def test_mark_as_unused(self):
        booking = factories.BookingFactory(isUsed=True)
        api.mark_as_unused(booking)
        assert not booking.isUsed

    def test_raise_if_activation_booking(self):
        booking = factories.BookingFactory(
            isUsed=True,
            stock__offer__type=str(offer_type.EventType.ACTIVATION),
        )
        with pytest.raises(api_errors.ForbiddenError):
            api.mark_as_unused(booking)
        assert booking.isUsed  # unchanged

    def test_raise_if_not_yet_used(self):
        booking = factories.BookingFactory(isUsed=False)
        with pytest.raises(api_errors.ResourceGoneError):
            api.mark_as_unused(booking)
        assert not booking.isUsed  # unchanged

    def test_raise_if_cancelled(self):
        booking = factories.BookingFactory(isUsed=True, isCancelled=True)
        with pytest.raises(api_errors.ResourceGoneError):
            api.mark_as_unused(booking)
        assert booking.isUsed  # unchanged

    def test_raise_if_has_payment(self):
        booking = factories.BookingFactory(isUsed=True)
        payments_factories.PaymentFactory(booking=booking)
        with pytest.raises(api_errors.ResourceGoneError):
            api.mark_as_unused(booking)
        assert booking.isUsed  # unchanged


class GenerateQrCodeTest:
    @mock.patch('qrcode.QRCode')
    def test_correct_technical_parameters(self, build_qr_code):
        api.generate_qr_code(random_token(), offer_extra_data={})
        build_qr_code.assert_called_once_with(
            version=2,
            error_correction=3,
            box_size=5,
            border=1,
        )

    @mock.patch('qrcode.QRCode.make_image')
    def test_should_build_qr_code_with_correct_image_parameters(
            self,
            build_qr_code_image_parameters
    ):
        api.generate_qr_code(booking_token='ABCDE', offer_extra_data={})
        build_qr_code_image_parameters.assert_called_once_with(
            back_color='white',
            fill_color='black',
        )

    @mock.patch('qrcode.QRCode.add_data')
    def test_include_product_isbn_if_provided(self, build_qr_code_booking_info):
        api.generate_qr_code('ABCDE', offer_extra_data={})
        build_qr_code_booking_info.assert_called_once_with(
            f'PASSCULTURE:v2;'
            f'TOKEN:ABCDE'
        )

        build_qr_code_booking_info.reset_mock()
        api.generate_qr_code('ABCDE', offer_extra_data={'isbn': '123456789'})
        build_qr_code_booking_info.assert_called_once_with(
            f'PASSCULTURE:v2;'
            f'EAN13:123456789;'
            f'TOKEN:ABCDE'
        )

    def test_generated_qr_code(self):
        qr_code = api.generate_qr_code('ABCDE', offer_extra_data={})
        assert isinstance(qr_code, str)
        assert qr_code == "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAJsAAACbAQAAAABdGtQhAAABs0lEQVR4nL1XMY7bMBCcFQXQqagf0EDeYSlp8o/8w7Hko/8VyfcR6gdURwKSJ4VdxYc0580WJDDFDHZJzoBCPNVcPWPAZ8EiIlKq5ZcUkWEWkfrTnB+DHRnRukDHBJAclIQoNeyI8758wwVFmhdwflD1fWMF2HNjXsL5b9BEdBw0hYQrIAkoXXOEZdIRQgaA3LoQc+tCBGCiihBJkiMMLVNPklQSmsiIjqvPrVs9mbQ6mpLhY2GI6BiUhG5uBW8uRDu6QMDpjK4uP3DxkLR9LSds+/wlKV1v+wYz4brYyGnmBGp5Xfk+r750zXEulav9ruOq5QxOxI6uhh2x7e3bSzifqwaW1QscPNikvuzQ/9Tp6ODDxBu2fekTAKFWHgFbhytMtL+bC3ZYdM4IWRJgR0daJkN7czoPtsLBD76cgDnTD8jvSS0m5nUGFtlLhU3ktOhE+d29c5d6kskwt0qje+SRcPBoXYhZy+uQOzJydCFaJsMsWnmUW5jIKT16g9boHuChMbyn31XpHT3AK46wZwlx176M829QuKL0Cdi1rp7t6HQs6H4yvOGIDPR6t07+12/iD1lz9hCJWM0gAAAAAElFTkSuQmCC"