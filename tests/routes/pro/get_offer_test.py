from datetime import datetime

from freezegun import freeze_time
import pytest

from pcapi.model_creators.generic_creators import create_bank_information
from pcapi.model_creators.generic_creators import create_mediation
from pcapi.model_creators.generic_creators import create_offerer
from pcapi.model_creators.generic_creators import create_stock
from pcapi.model_creators.generic_creators import create_user
from pcapi.model_creators.generic_creators import create_venue
from pcapi.model_creators.specific_creators import create_offer_with_thing_product
from pcapi.model_creators.specific_creators import create_stock_with_event_offer
from pcapi.model_creators.specific_creators import create_stock_with_thing_offer
from pcapi.repository import repository
from pcapi.utils.human_ids import humanize

from tests.conftest import TestClient


class Returns200:
    @pytest.mark.usefixtures("db_session")
    def when_user_has_rights_on_managing_offerer(self, app):
        # Given
        beneficiary = create_user()
        offerer = create_offerer()
        venue = create_venue(offerer)
        offer = create_offer_with_thing_product(venue)
        stock = create_stock(offer=offer)
        create_bank_information(venue=venue, application_id=1)
        create_bank_information(offerer=offerer, application_id=2)
        repository.save(beneficiary, stock)

        # When
        response = TestClient(app.test_client()).with_auth(email=beneficiary.email).get(f"/offers/{humanize(offer.id)}")

        # Then
        response_json = response.json
        assert response.status_code == 200
        assert "iban" in response_json["venue"]
        assert "bic" in response_json["venue"]
        assert "iban" in response_json["venue"]["managingOfferer"]
        assert "bic" in response_json["venue"]["managingOfferer"]
        assert "validationToken" not in response_json["venue"]["managingOfferer"]
        assert "thumbUrl" in response_json

    @pytest.mark.usefixtures("db_session")
    def when_returns_an_active_mediation(self, app):
        # Given
        beneficiary = create_user()
        offerer = create_offerer()
        venue = create_venue(offerer)
        offer = create_offer_with_thing_product(venue)
        mediation = create_mediation(offer, is_active=True)
        repository.save(beneficiary, mediation)

        # When
        response = TestClient(app.test_client()).with_auth(email=beneficiary.email).get(f"/offers/{humanize(offer.id)}")

        # Then
        assert response.status_code == 200
        assert response.json["activeMediation"] is not None

    @pytest.mark.usefixtures("db_session")
    @freeze_time("2019-10-15 00:00:00")
    def when_returns_an_event_stock(self, app):
        # Given
        date_now = datetime(2020, 10, 15)

        beneficiary = create_user()
        offerer = create_offerer(date_created=date_now, date_modified_at_last_provider=date_now)
        venue = create_venue(offerer, date_created=date_now, date_modified_at_last_provider=date_now)
        stock = create_stock_with_event_offer(
            offerer=offerer,
            venue=venue,
            beginning_datetime=date_now,
            booking_limit_datetime=date_now,
            date_created=date_now,
            date_modified_at_last_provider=date_now,
            date_modifed=date_now,
        )
        stock.offer.dateCreated = date_now
        stock.offer.dateModifiedAtLastProvider = date_now
        stock.offer.product.dateModifiedAtLastProvider = date_now
        repository.save(beneficiary, stock)

        # When
        response = (
            TestClient(app.test_client()).with_auth(email=beneficiary.email).get(f"/offers/{humanize(stock.offer.id)}")
        )

        # Then
        assert response.status_code == 200
        assert response.json == {
            "activeMediation": None,
            "ageMax": None,
            "ageMin": None,
            "bookingEmail": "offer.booking.email@example.com",
            "conditions": None,
            "dateCreated": "2020-10-15T00:00:00Z",
            "dateModifiedAtLastProvider": "2020-10-15T00:00:00Z",
            "description": None,
            "durationMinutes": 60,
            "extraData": None,
            "fieldsUpdated": [],
            "hasBookingLimitDatetimesPassed": False,
            "id": humanize(stock.offer.id),
            "idAtProviders": None,
            "isActive": True,
            "isBookable": True,
            "isDigital": False,
            "isDuo": False,
            "isEditable": True,
            "isEvent": True,
            "isNational": False,
            "isThing": False,
            "lastProvider": None,
            "lastProviderId": None,
            "mediaUrls": [],
            "mediations": [],
            "name": "Mains, sorts et papiers",
            "offerType": {
                "appLabel": "Jeux - événement, rencontre ou concours",
                "conditionalFields": [],
                "description": "Résoudre l’énigme d’un jeu de piste dans votre "
                "ville ? Jouer en ligne entre amis ? Découvrir "
                "cet univers étrange avec une manette ?",
                "isActive": True,
                "offlineOnly": True,
                "onlineOnly": False,
                "proLabel": "Jeux - événements, rencontres, concours",
                "sublabel": "Jouer",
                "type": "Event",
                "value": "EventType.JEUX",
            },
            "product": {
                "ageMax": None,
                "ageMin": None,
                "conditions": None,
                "dateModifiedAtLastProvider": "2020-10-15T00:00:00Z",
                "description": None,
                "durationMinutes": 60,
                "extraData": None,
                "fieldsUpdated": [],
                "id": humanize(stock.offer.product.id),
                "idAtProviders": None,
                "isGcuCompatible": True,
                "isNational": False,
                "lastProviderId": None,
                "mediaUrls": [],
                "name": "Mains, sorts et papiers",
                "owningOffererId": None,
                "thumbCount": 0,
                "url": None,
            },
            "productId": humanize(stock.offer.product.id),
            "stocks": [
                {
                    "beginningDatetime": "2020-10-15T00:00:00Z",
                    "bookingLimitDatetime": "2020-10-15T00:00:00Z",
                    "bookingsQuantity": 0,
                    "cancellationLimitDate": "2019-10-17T00:00:00Z",
                    "dateCreated": "2020-10-15T00:00:00Z",
                    "dateModified": "2020-10-15T00:00:00Z",
                    "dateModifiedAtLastProvider": "2020-10-15T00:00:00Z",
                    "fieldsUpdated": [],
                    "id": humanize(stock.id),
                    "idAtProviders": None,
                    "isBookable": True,
                    "isEventDeletable": True,
                    "isEventExpired": False,
                    "isSoftDeleted": False,
                    "lastProviderId": None,
                    "offerId": humanize(stock.offer.id),
                    "price": 10.0,
                    "quantity": 10,
                    "remainingQuantity": 10,
                }
            ],
            "thumbUrl": None,
            "type": "EventType.JEUX",
            "url": None,
            "venue": {
                "address": "123 rue de Paris",
                "bic": None,
                "bookingEmail": None,
                "city": "Montreuil",
                "comment": None,
                "dateCreated": "2020-10-15T00:00:00Z",
                "dateModifiedAtLastProvider": "2020-10-15T00:00:00Z",
                "departementCode": "93",
                "fieldsUpdated": [],
                "iban": None,
                "id": humanize(venue.id),
                "idAtProviders": None,
                "isValidated": True,
                "isVirtual": False,
                "lastProviderId": None,
                "latitude": None,
                "longitude": None,
                "managingOfferer": {
                    "address": None,
                    "bic": None,
                    "city": "Montreuil",
                    "dateCreated": "2020-10-15T00:00:00Z",
                    "dateModifiedAtLastProvider": "2020-10-15T00:00:00Z",
                    "fieldsUpdated": [],
                    "iban": None,
                    "id": humanize(offerer.id),
                    "idAtProviders": None,
                    "isActive": True,
                    "isValidated": True,
                    "lastProviderId": None,
                    "name": "Test Offerer",
                    "postalCode": "93100",
                    "siren": "123456789",
                    "thumbCount": 0,
                },
                "managingOffererId": humanize(offerer.id),
                "name": "La petite librairie",
                "postalCode": "93100",
                "publicName": None,
                "siret": "12345678912345",
                "thumbCount": 0,
                "venueLabelId": None,
                "venueTypeId": None,
            },
            "venueId": humanize(venue.id),
            "withdrawalDetails": None,
        }

    @freeze_time("2019-10-15 00:00:00")
    @pytest.mark.usefixtures("db_session")
    def when_returns_an_thing_stock(self, app):
        # Given
        beneficiary = create_user()
        offerer = create_offerer()
        venue = create_venue(offerer)
        stock = create_stock_with_thing_offer(offerer=offerer, venue=venue)
        repository.save(beneficiary, stock)

        # When
        response = (
            TestClient(app.test_client()).with_auth(email=beneficiary.email).get(f"/offers/{humanize(stock.offer.id)}")
        )

        # Then
        assert response.status_code == 200
        data = response.json
        assert data["stocks"][0]["cancellationLimitDate"] is None