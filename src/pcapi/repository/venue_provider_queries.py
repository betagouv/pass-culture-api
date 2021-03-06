from sqlalchemy import not_

from pcapi.core.providers.models import VenueProvider


def get_active_venue_providers_for_specific_provider(provider_id: int) -> list[VenueProvider]:
    return (
        VenueProvider.query.filter(VenueProvider.providerId == provider_id).filter(VenueProvider.isActive == True).all()
    )


def get_venue_providers_to_sync(provider_id: int) -> list[VenueProvider]:
    return (
        VenueProvider.query.filter(VenueProvider.isActive == True)
        .filter(VenueProvider.providerId == provider_id)
        .filter(VenueProvider.syncWorkerId.is_(None))
        .all()
    )


def get_venue_provider_by_id(venue_provider_id: int) -> VenueProvider:
    return VenueProvider.query.get(venue_provider_id)


def get_nb_containers_at_work() -> int:
    return VenueProvider.query.filter(not_(VenueProvider.syncWorkerId.is_(None))).count()
