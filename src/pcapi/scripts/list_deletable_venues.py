# import csv
# from io import StringIO
# from typing import List

# from sqlalchemy.orm import joinedload
# from sqlalchemy.orm.query import Query

# from pcapi.core.offerers.models import Venue
# from pcapi.models.offerer import Offerer
# from pcapi.utils.human_ids import humanize


# CSV_HEADER = [
#     "Nom structure",
#     "SIREN",
#     "ID structure humanisé",
#     "Code postal structure",
#     "Nom lieu",
#     "SIRET",
#     "ID lieu humanisé",
#     "Département lieu",
# ]


# def _format_offerer_without_venues(offerer: Offerer) -> List:
#     return [offerer.name, offerer.siren, humanize(offerer.id), offerer.postalCode, "", "", ""]


# def _format_offerer_with_venues(offerer: Offerer) -> List[List]:
#     rows = []
#     for venue in offerer.managedVenues:
#         rows.append(
#             [
#                 offerer.name,
#                 offerer.siren,
#                 humanize(offerer.id),
#                 offerer.postalCode,
#                 venue.name,
#                 venue.siret,
#                 humanize(venue.id),
#                 venue.departementCode,
#             ]
#         )
#     return rows


# def get_base_query(min_id: int) -> Query:
#     return Offerer.query.filter(
#         Offerer.id > min_id,
#     )


# def get_ids_query(min_id: int) -> Query:
#     return get_base_query(min_id).order_by(Offerer.id).with_entities(Offerer.id)


# def fill_csv(batch_size: int = 1000) -> None:
#     item_count = get_ids_query(0).count()
#     print(f"{item_count} offerers to check")
#     if item_count == 0:
#         return
#     modified_sum = 0
#     min_id = 0
#     item_ids = get_ids_query(min_id).limit(batch_size).all()
#     max_id = item_ids[-1][0]
#     with open("deletable_venues.csv", "w", newline="") as csvfile:
#         writer = csv.writer(csvfile, delimiter=";", quotechar="|", quoting=csv.QUOTE_MINIMAL)
#         writer.writerow(CSV_HEADER)
#         while item_ids:
#             offerers = get_base_query(min_id).filter(Offerer.id <= max_id).all()
#             for offerer in offerers:
#                 if len(offerer.managedVenues) == 0:
#                     writer.writerow(_format_offerer_without_venues(offerer))
#                     continue
#                 if offerer.nOffers > 0:
#                     continue
#                 writer.writerows(_format_offerer_with_venues(offerer))
#             item_ids = get_ids_query(max_id).limit(batch_size).all()
#             print(f"{len(offerers)} offerers checked out")
#             modified_sum += len(offerers)
#             if len(item_ids) == 0:
#                 break
#             min_id, max_id = max_id, item_ids[-1][0]
#     print(f"{modified_sum} offerers checked out")
