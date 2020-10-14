from enum import Enum
from typing import Dict, List

from pcapi.models import ApiErrors, OfferSQLEntity, StockSQLEntity


def check_stocks_are_editable_for_offer(offer: OfferSQLEntity) -> None:
    if offer.isFromProvider:
        api_errors = ApiErrors()
        api_errors.add_error('global', 'Les offres importées ne sont pas modifiables')
        raise api_errors


class LocalProviderNames(Enum):
    titelive = 'TiteLiveStocks'
    titeliveThings = 'TiteLiveThings'
    fnac = 'FnacStocks'
    libraires = 'LibrairesStocks'
    praxiel = 'PraxielStocks'


def _is_stocks_provider_generated_offer(local_class: str) -> bool:
    for local_provider in LocalProviderNames:
        if local_provider.value == local_class:
            return True
    return False


def check_stock_is_updatable(stock: StockSQLEntity) -> None:
    local_class = stock.offer.lastProvider.localClass if stock.offer.lastProvider else ''
    is_from_provider = stock.offer.isFromProvider is True

    if is_from_provider and _is_stocks_provider_generated_offer(local_class):
        api_errors = ApiErrors()
        api_errors.add_error('global', 'Les offres importées ne sont pas modifiables')
        raise api_errors

    if stock.isEventExpired:
        api_errors = ApiErrors()
        api_errors.add_error('global', 'Les événements passés ne sont pas modifiables')
        raise api_errors


def check_request_has_offer_id(request_data: dict) -> None:
    if 'offerId' not in request_data:
        raise ApiErrors({'offerId': ['Ce paramètre est obligatoire']})


def check_dates_are_allowed_on_new_stock(request_data: dict, offer: OfferSQLEntity) -> None:
    if offer.isThing:
        _forbid_dates_on_stock_for_thing_offer(request_data)
    else:
        if request_data.get('beginningDatetime', None) is None:
            raise ApiErrors({'beginningDatetime': ['Ce paramètre est obligatoire']})

        if request_data.get('bookingLimitDatetime', None) is None:
            raise ApiErrors({'bookingLimitDatetime': ['Ce paramètre est obligatoire']})


def check_dates_are_allowed_on_existing_stock(request_data: dict, offer: OfferSQLEntity) -> None:
    if offer.isThing:
        _forbid_dates_on_stock_for_thing_offer(request_data)
    else:
        if 'beginningDatetime' in request_data and request_data['beginningDatetime'] is None:
            raise ApiErrors({'beginningDatetime': ['Ce paramètre est obligatoire']})

        if 'bookingLimitDatetime' in request_data and request_data['bookingLimitDatetime'] is None:
            raise ApiErrors({'bookingLimitDatetime': ['Ce paramètre est obligatoire']})


def _forbid_dates_on_stock_for_thing_offer(request_data: dict) -> None:
    if 'beginningDatetime' in request_data:
        raise ApiErrors(
            {'global': [
                "Impossible de mettre une date de début si l'offre ne porte pas sur un événement"
            ]})


def check_only_editable_fields_will_be_updated(stock_updated_fields: List, stock_editable_fields: List) -> None:
    fields_to_update_are_editable = set(stock_updated_fields).issubset(stock_editable_fields)
    if not fields_to_update_are_editable:
        api_errors = ApiErrors()
        api_errors.status_code = 400
        api_errors.add_error('global', 'Pour les offres importées, certains champs ne sont pas modifiables')
        raise api_errors


def get_only_fields_with_value_to_be_updated(existing_stock_data: Dict, new_stock_data: Dict) -> List:
    stock_related_keys = set(existing_stock_data).intersection(set(new_stock_data))
    filtered_existing_stock_data = {key: existing_stock_data[key] for key in stock_related_keys}
    filtered_new_stock_data = {key: new_stock_data[key] for key in stock_related_keys}
    fields_with_changed_data = [key for key in stock_related_keys if
                                filtered_new_stock_data[key] != filtered_existing_stock_data[key]]
    return fields_with_changed_data