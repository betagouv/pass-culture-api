import logging
from time import sleep

from redis import Redis

from pcapi import settings
from pcapi.connectors.redis import add_venue_provider_currently_in_sync
from pcapi.connectors.redis import delete_venue_providers
from pcapi.connectors.redis import get_number_of_venue_providers_currently_in_sync
from pcapi.connectors.redis import get_venue_providers
from pcapi.connectors.scalingo_api import ScalingoApiException
from pcapi.connectors.scalingo_api import run_process_in_one_off_container


logger = logging.getLogger(__name__)


ALGOLIA_WAIT_TIME_FOR_AVAILABLE_WORKER = 60


def process_multi_indexing(client: Redis) -> None:
    venue_providers_to_process = get_venue_providers(client=client)
    delete_venue_providers(client=client)
    sync_worker_pool = settings.ALGOLIA_SYNC_WORKERS_POOL_SIZE

    while len(venue_providers_to_process) > 0:
        venue_provider = venue_providers_to_process[0]
        venue_providers_currently_in_sync = get_number_of_venue_providers_currently_in_sync(client=client)
        has_remaining_slot_in_pool = sync_worker_pool - venue_providers_currently_in_sync > 0

        if has_remaining_slot_in_pool:
            venue_providers_to_process.pop(0)
            _run_indexing(client=client, venue_provider=venue_provider)
        else:
            sleep(ALGOLIA_WAIT_TIME_FOR_AVAILABLE_WORKER)


def _run_indexing(client: Redis, venue_provider: dict) -> None:
    venue_provider_id = venue_provider["id"]
    provider_id = venue_provider["providerId"]
    venue_id = venue_provider["venueId"]

    run_algolia_venue_provider_command = (
        f"python src/pcapi/scripts/pc.py process_venue_provider_offers_for_algolia "
        f"--provider-id {provider_id} "
        f"--venue-provider-id {venue_provider_id} "
        f"--venue-id {venue_id}"
    )
    try:
        container_id = run_process_in_one_off_container(run_algolia_venue_provider_command)
        add_venue_provider_currently_in_sync(
            client=client, container_id=container_id, venue_provider_id=venue_provider_id
        )
        logger.info(
            "[ALGOLIA][Worker] Indexing offers from VenueProvider %s in container %s", venue_provider_id, container_id
        )
    except ScalingoApiException as error:
        logger.exception(
            "[ALGOLIA][Worker] Error indexing offers from VenueProvider %s with errors: %s",
            venue_provider_id,
            error,
        )
