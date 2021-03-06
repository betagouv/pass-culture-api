from datetime import datetime
from datetime import timedelta
import logging

from redis import Redis

from pcapi import settings
from pcapi.algolia.usecase.orchestrator import delete_expired_offers
from pcapi.algolia.usecase.orchestrator import process_eligible_offers
from pcapi.connectors.redis import RedisBucket
from pcapi.connectors.redis import delete_offer_ids
from pcapi.connectors.redis import delete_offer_ids_in_error
from pcapi.connectors.redis import delete_venue_ids
from pcapi.connectors.redis import delete_venue_provider_currently_in_sync
from pcapi.connectors.redis import delete_venue_providers
from pcapi.connectors.redis import get_offer_ids
from pcapi.connectors.redis import get_offer_ids_in_error
from pcapi.connectors.redis import get_venue_ids
from pcapi.connectors.redis import get_venue_providers
from pcapi.connectors.redis import pop_offer_ids
from pcapi.repository import offer_queries
from pcapi.utils.converter import from_tuple_to_int


logger = logging.getLogger(__name__)


# FIXME (dbaty, 2021-04-28): remove when we're sure that the new
# version (`batch_indexing_offers_in_algolia_by_offer` below) works as
# intended. Also remove `get_offer_ids` and `delete_offer_ids`.
def legacy_batch_indexing_offers_in_algolia_by_offer(client: Redis) -> None:
    offer_ids = get_offer_ids(client=client)

    if len(offer_ids) > 0:
        logger.info("[ALGOLIA] processing %i offers...", len(offer_ids))
        process_eligible_offers(client=client, offer_ids=offer_ids, from_provider_update=False)
        delete_offer_ids(client=client)
        logger.info("[ALGOLIA] %i offers processed!", len(offer_ids))


def batch_indexing_offers_in_algolia_by_offer(client: Redis, stop_only_when_empty=False) -> None:
    """Reindex offers.

    If `stop_only_when_empty` is False (i.e. if called as a cron
    command), we pop from the queue at least once, and stop when there
    is less than REDIS_OFFER_IDS_CHUNK_SIZE in the queue (otherwise
    the cron job may never stop). It means that a cron job may run for
    a long time if the queue has many items. In fact, a subsequent
    cron job may run in parallel if the previous one has not finished.
    It's fine because they both pop from the queue.

    If `stop_only_when_empty` is True (i.e. if called from the
    `process_offers` Flask command), we pop from the queue and stop
    only when the queue is empty.
    """
    while True:
        # We must pop and not get-and-delete. Otherwise two concurrent
        # cron jobs could delete the wrong offers from the queue:
        # 1. Cron job 1 gets the first 1.000 offers from the queue.
        # 2. Cron job 2 gets the same 1.000 offers from the queue.
        # 3. Cron job 1 finishes processing the batch and deletes the
        #    first 1.000 offers from the queue. OK.
        # 4. Cron job 2 finishes processing the batch and also deletes
        #    the first 1.000 offers from the queue. Not OK, these are
        #    not the same offers it just processed!
        offer_ids = pop_offer_ids(client=client)
        if not offer_ids:
            break

        logger.info("[ALGOLIA] processing %i offers...", len(offer_ids))
        try:
            process_eligible_offers(client=client, offer_ids=offer_ids, from_provider_update=False)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Exception while reindexing offers, must fix manually",
                extra={
                    "exc": str(exc),
                    "offer_ids": offer_ids,
                },
            )
        logger.info("[ALGOLIA] %i offers processed!", len(offer_ids))

        left_to_process = client.llen(RedisBucket.REDIS_LIST_OFFER_IDS_NAME.value)
        if not stop_only_when_empty and left_to_process < settings.REDIS_OFFER_IDS_CHUNK_SIZE:
            break


def batch_indexing_offers_in_algolia_by_venue_provider(client: Redis) -> None:
    venue_providers = get_venue_providers(client=client)

    if len(venue_providers) > 0:
        delete_venue_providers(client=client)
        for venue_provider in venue_providers:
            venue_provider_id = venue_provider["id"]
            provider_id = venue_provider["providerId"]
            venue_id = int(venue_provider["venueId"])
            _process_venue_provider(
                client=client, provider_id=provider_id, venue_id=venue_id, venue_provider_id=venue_provider_id
            )


def batch_indexing_offers_in_algolia_by_venue(client: Redis) -> None:
    venue_ids = get_venue_ids(client=client)

    if len(venue_ids) > 0:
        for venue_id in venue_ids:
            page = 0
            has_still_offers = True

            while has_still_offers:
                offer_ids_as_tuple = offer_queries.get_paginated_offer_ids_by_venue_id(
                    limit=settings.ALGOLIA_OFFERS_BY_VENUE_CHUNK_SIZE, page=page, venue_id=venue_id
                )
                offer_ids_as_int = from_tuple_to_int(offer_ids_as_tuple)

                if len(offer_ids_as_int) > 0:
                    logger.info("[ALGOLIA] processing offers for venue %s from page %s...", venue_id, page)
                    process_eligible_offers(client=client, offer_ids=offer_ids_as_int, from_provider_update=False)
                    logger.info("[ALGOLIA] offers for venue %s from page %s processed!", venue_id, page)
                else:
                    has_still_offers = False
                    logger.info("[ALGOLIA] processing of offers for venue %s finished!", venue_id)
                page += 1
        delete_venue_ids(client=client)


def batch_indexing_offers_in_algolia_from_database(
    client: Redis, ending_page: int = None, limit: int = 10000, starting_page: int = 0
) -> None:
    page_number = starting_page
    has_still_offers = True

    while has_still_offers:
        if ending_page:
            if ending_page == page_number:
                break

        offer_ids_as_tuple = offer_queries.get_paginated_active_offer_ids(limit=limit, page=page_number)
        offer_ids_as_int = from_tuple_to_int(offer_ids=offer_ids_as_tuple)

        if len(offer_ids_as_int) > 0:
            logger.info("[ALGOLIA] processing offers of database from page %s...", page_number)
            process_eligible_offers(client=client, offer_ids=offer_ids_as_int, from_provider_update=False)
            logger.info("[ALGOLIA] offers of database from page %s processed!", page_number)
        else:
            has_still_offers = False
            logger.info("[ALGOLIA] processing of offers from database finished!")
        page_number += 1


def batch_deleting_expired_offers_in_algolia(client: Redis, process_all_expired: bool = False) -> None:
    page = 0
    has_still_offers = True
    one_day_before_now = datetime.utcnow() - timedelta(days=1)
    two_days_before_now = datetime.utcnow() - timedelta(days=2)
    arbitrary_oldest_date = datetime(2000, 1, 1)
    from_date = two_days_before_now if not process_all_expired else arbitrary_oldest_date

    while has_still_offers:
        expired_offer_ids_as_tuple = offer_queries.get_paginated_offer_ids_given_booking_limit_datetime_interval(
            limit=settings.ALGOLIA_DELETING_OFFERS_CHUNK_SIZE,
            page=page,
            from_date=from_date,
            to_date=one_day_before_now,
        )
        expired_offer_ids_as_int = from_tuple_to_int(offer_ids=expired_offer_ids_as_tuple)

        if len(expired_offer_ids_as_int) > 0:
            logger.info("[ALGOLIA] processing deletion of expired offers from page %s...", page)
            delete_expired_offers(client=client, offer_ids=expired_offer_ids_as_int)
            logger.info("[ALGOLIA] expired offers from page %s processed!", page)
        else:
            has_still_offers = False
            logger.info("[ALGOLIA] deleting expired offers finished!")
        page += 1


def batch_processing_offer_ids_in_error(client: Redis):
    offer_ids_in_error = get_offer_ids_in_error(client=client)
    if len(offer_ids_in_error) > 0:
        process_eligible_offers(client=client, offer_ids=offer_ids_in_error, from_provider_update=False)
        delete_offer_ids_in_error(client=client)


def _process_venue_provider(client: Redis, provider_id: str, venue_provider_id: int, venue_id: int) -> None:
    has_still_offers = True
    page = 0
    try:
        while has_still_offers is True:
            offer_ids_as_tuple = offer_queries.get_paginated_offer_ids_by_venue_id_and_last_provider_id(
                last_provider_id=provider_id,
                limit=settings.ALGOLIA_OFFERS_BY_VENUE_PROVIDER_CHUNK_SIZE,
                page=page,
                venue_id=venue_id,
            )
            offer_ids_as_int = from_tuple_to_int(offer_ids_as_tuple)

            if len(offer_ids_as_tuple) > 0:
                logger.info(
                    "[ALGOLIA] processing offers for (venue %s / provider %s) from page %s...",
                    venue_id,
                    provider_id,
                    page,
                )
                process_eligible_offers(client=client, offer_ids=offer_ids_as_int, from_provider_update=True)
                logger.info(
                    "[ALGOLIA] offers for (venue %s / provider %s) from page %s processed",
                    venue_id,
                    provider_id,
                    page,
                )
                page += 1
            else:
                has_still_offers = False
                logger.info(
                    "[ALGOLIA] processing of offers for (venue %s / provider %s) finished!", venue_id, provider_id
                )
    except Exception as error:  # pylint: disable=broad-except
        logger.exception(
            "[ALGOLIA] processing of offers for (venue %s / provider %s) failed! %s",
            venue_id,
            provider_id,
            error,
        )
    finally:
        delete_venue_provider_currently_in_sync(client=client, venue_provider_id=venue_provider_id)
