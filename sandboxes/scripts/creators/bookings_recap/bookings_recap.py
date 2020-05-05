from datetime import timedelta, datetime

from models import EventType, ThingType
from repository import repository
from tests.model_creators.generic_creators import create_user, create_deposit, create_offerer, create_venue, \
    create_stock, create_booking, create_user_offerer
from tests.model_creators.specific_creators import create_offer_with_event_product, create_offer_with_thing_product


def save_bookings_recap_sandbox():
    yesterday = datetime.utcnow() - timedelta(days=1)
    today = datetime.utcnow()

    beneficiary1 = create_user(
        public_name='Riri Duck',
        first_name='Riri',
        last_name='Duck',
        email='riri.duck@example.com',
    )
    beneficiary2 = create_user(
        public_name='Fifi Brindacier',
        first_name='Fifi',
        last_name='Brindacier',
        email='fifi.brindacier@example.com',
    )
    beneficiary3 = create_user(
        public_name='LouLou Duck',
        first_name='Loulou',
        last_name='Duck',
        email='loulou.duck@example.com',
    )

    create_deposit(beneficiary1)
    create_deposit(beneficiary2)
    create_deposit(beneficiary3)

    pro = create_user(
        public_name='Balthazar Picsou',
        first_name='Balthazar',
        last_name='Picsou',
        email='balthazar.picsou@example.com',
        can_book_free_offers=False
    )
    offerer = create_offerer(
        siren='645389012',
    )
    user_offerer = create_user_offerer(user=pro, offerer=offerer)
    venue1 = create_venue(offerer, name='Cinéma Le Monde Perdu', siret='64538901265877')
    venue2 = create_venue(offerer, name='Librairie Atlantis', siret='64538901201379')
    venue3 = create_venue(offerer, name='Théatre Mordor', siret='64538954601379')

    offer1_venue3 = create_offer_with_event_product(
        venue=venue2,
        event_name='Danse des haricots',
        event_type=EventType.SPECTACLE_VIVANT,
    )
    stock_1_offer1_venue3 = create_stock(
        offer=offer1_venue3,
        quantity=44
    )

    offer1_venue1 = create_offer_with_event_product(
        venue=venue1,
        event_name='Jurassic Park',
        event_type=EventType.CINEMA,
        is_duo=True,
    )
    stock_1_offer1_venue1 = create_stock(
        offer=offer1_venue1,
        beginning_datetime=yesterday,
        quantity=None
    )

    offer2_venue1 = create_offer_with_event_product(
        venue=venue1,
        event_name='Matrix',
        event_type=EventType.CINEMA,
        is_duo=False,
    )
    stock_1_offer2_venue1 = create_stock(
        offer=offer2_venue1,
        beginning_datetime=today,
        quantity=None
    )

    offer1_venue2 = create_offer_with_thing_product(
        venue=venue2,
        thing_name='Fondation',
        thing_type=ThingType.LIVRE_EDITION,
        extra_data={'ISBN': '9788804119135'}
    )
    stock_1_offer1_venue2 = create_stock(
        offer=offer1_venue2,
        quantity=42
    )

    booking1_beneficiary1 = create_booking(
        user=beneficiary1,
        stock=stock_1_offer1_venue1,
        date_created=datetime(2020, 3, 18, 14, 56, 12, 0)
    )
    booking2_beneficiary1 = create_booking(
        user=beneficiary1,
        stock=stock_1_offer2_venue1,
        date_created=datetime(2020, 4, 22, 9, 17, 12, 0)
    )
    booking1_beneficiary2 = create_booking(
        user=beneficiary2,
        stock=stock_1_offer1_venue1,
        date_created=datetime(2020, 3, 18, 12, 18, 12, 0)
    )
    booking2_beneficiary2 = create_booking(
        user=beneficiary2,
        stock=stock_1_offer1_venue2,
        date_created=datetime(2020, 4, 12, 14, 31, 12, 0),
        is_cancelled=True
    )
    booking1_beneficiary3 = create_booking(
        user=beneficiary3,
        stock=stock_1_offer2_venue1,
        date_created=datetime(2020, 1, 4, 19, 31, 12, 0),
        is_cancelled=True,
        is_used=True
    )
    booking2_beneficiary3 = create_booking(
        user=beneficiary3,
        stock=stock_1_offer1_venue2,
        date_created=datetime(2020, 3, 21, 22, 9, 12, 0),
        is_cancelled=True
    )

    booking3_beneficiary1 = create_booking(
        user=beneficiary1,
        stock=stock_1_offer1_venue3,
        date_created=datetime(2020, 4, 12, 14, 31, 12, 0)
        )
    booking3_beneficiary2 = create_booking(
        user=beneficiary2,
        stock=stock_1_offer1_venue3,
        date_created=datetime(2020, 4, 12, 19, 31, 12, 0),
        is_used=True
    )
    booking3_beneficiary3 = create_booking(
        user=beneficiary3,
        stock=stock_1_offer1_venue3,
        date_created=datetime(2020, 4, 12, 22, 9, 12, 0)
    )

    repository.save(
        pro,
        booking1_beneficiary1, booking2_beneficiary1,
        booking1_beneficiary2, booking2_beneficiary2,
        booking1_beneficiary3, booking2_beneficiary3,
        booking3_beneficiary1, booking3_beneficiary2,
        booking3_beneficiary3, user_offerer
    )
