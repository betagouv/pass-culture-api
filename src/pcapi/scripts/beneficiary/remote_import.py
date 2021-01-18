from datetime import datetime
import re
from typing import Callable
from typing import Dict
from typing import List

from pcapi import settings
from pcapi.connectors.api_demarches_simplifiees import get_application_details
from pcapi.core.users.models import User
from pcapi.domain.beneficiary_pre_subscription.beneficiary_pre_subscription import BeneficiaryPreSubscription
from pcapi.domain.beneficiary_pre_subscription.beneficiary_pre_subscription_validator import get_beneficiary_duplicates
from pcapi.domain.demarches_simplifiees import get_closed_application_ids_for_demarche_simplifiee
from pcapi.domain.user_emails import send_activation_email
from pcapi.infrastructure.repository.beneficiary import beneficiary_pre_subscription_sql_converter
from pcapi.models import ApiErrors
from pcapi.models import ImportStatus
from pcapi.models.beneficiary_import import BeneficiaryImportSources
from pcapi.repository import repository
from pcapi.repository.beneficiary_import_queries import find_applications_ids_to_retry
from pcapi.repository.beneficiary_import_queries import is_already_imported
from pcapi.repository.beneficiary_import_queries import save_beneficiary_import_with_status
from pcapi.repository.user_queries import find_user_by_email
from pcapi.utils.logger import logger
from pcapi.utils.mailing import MailServiceException
from pcapi.utils.mailing import send_raw_email


def run(
    process_applications_updated_after: datetime,
    get_all_applications_ids: Callable[..., List[int]] = get_closed_application_ids_for_demarche_simplifiee,
    get_applications_ids_to_retry: Callable[..., List[int]] = find_applications_ids_to_retry,
    get_details: Callable[..., Dict] = get_application_details,
    already_imported: Callable[..., bool] = is_already_imported,
    already_existing_user: Callable[..., User] = find_user_by_email,
) -> None:
    procedure_id = settings.DMS_NEW_ENROLLMENT_PROCEDURE_ID
    logger.info(
        "[BATCH][REMOTE IMPORT BENEFICIARIES] Start import from Démarches Simplifiées for "
        "procedure = %s - Procedure %s",
        procedure_id,
        procedure_id,
    )
    applications_ids = get_all_applications_ids(procedure_id, settings.DMS_TOKEN, process_applications_updated_after)
    retry_ids = get_applications_ids_to_retry()

    logger.info(
        "[BATCH][REMOTE IMPORT BENEFICIARIES] %i new applications to process - Procedure %s",
        len(applications_ids),
        procedure_id,
    )
    logger.info(
        "[BATCH][REMOTE IMPORT BENEFICIARIES] %i previous applications to retry - Procedure %s",
        len(retry_ids),
        procedure_id,
    )

    for application_id in retry_ids + applications_ids:
        details = get_details(application_id, procedure_id, settings.DMS_TOKEN)
        try:
            pre_subscription = parse_beneficiary_information(details)
        except Exception as exc:  # pylint: disable=broad-except
            logger.info(
                "[BATCH][REMOTE IMPORT BENEFICIARIES] Application %s in procedure %s had errors and was ignored: %s",
                application_id,
                procedure_id,
                exc,
                exc_info=True,
            )
            error = f"Le dossier {application_id} contient des erreurs et a été ignoré - Procedure {procedure_id}"
            save_beneficiary_import_with_status(
                ImportStatus.ERROR,
                application_id,
                source=BeneficiaryImportSources.demarches_simplifiees,
                source_id=procedure_id,
                detail=error,
            )
            continue

        if already_existing_user(pre_subscription.email):
            _process_rejection(pre_subscription, procedure_id=procedure_id)
            continue

        if not already_imported(pre_subscription.application_id):
            process_beneficiary_application(
                pre_subscription=pre_subscription,
                retry_ids=retry_ids,
                procedure_id=procedure_id,
            )

    logger.info(
        "[BATCH][REMOTE IMPORT BENEFICIARIES] End import from Démarches Simplifiées - Procedure %s", procedure_id
    )


def process_beneficiary_application(
    pre_subscription: BeneficiaryPreSubscription,
    retry_ids: List[int],
    procedure_id: int,
) -> None:
    duplicate_users = get_beneficiary_duplicates(
        first_name=pre_subscription.first_name,
        last_name=pre_subscription.last_name,
        date_of_birth=pre_subscription.date_of_birth,
    )

    if not duplicate_users or pre_subscription.application_id in retry_ids:
        _process_creation(pre_subscription, procedure_id)
    else:
        _process_duplication(duplicate_users, pre_subscription, procedure_id)


def parse_beneficiary_information(application_detail: Dict) -> BeneficiaryPreSubscription:
    dossier = application_detail["dossier"]

    information = {
        "last_name": dossier["individual"]["nom"],
        "first_name": dossier["individual"]["prenom"],
        "civility": dossier["individual"]["civilite"],
        "email": dossier["email"],
        "application_id": dossier["id"],
    }

    for field in dossier["champs"]:
        label = field["type_de_champ"]["libelle"]
        value = field["value"]

        if "Veuillez indiquer votre département" in label:
            information["department"] = re.search("^[0-9]{2,3}|[2BbAa]{2}", value).group(0)
        if label == "Quelle est votre date de naissance":
            information["birth_date"] = datetime.strptime(value, "%Y-%m-%d")
        if label == "Quel est votre numéro de téléphone":
            information["phone"] = value
        if label == "Quel est le code postal de votre commune de résidence ?":
            space_free = str(value).strip().replace(" ", "")
            information["postal_code"] = re.search("^[0-9]{5}", space_free).group(0)
        if label == "Veuillez indiquer votre statut":
            information["activity"] = value

    return BeneficiaryPreSubscription(
        first_name=information["first_name"],
        last_name=information["last_name"],
        civility=information["civility"],
        email=information["email"],
        application_id=information["application_id"],
        date_of_birth=information["birth_date"],
        phone_number=information["phone"],
        postal_code=information["postal_code"],
        activity=information["activity"],
        raw_department_code=information["department"],
        address=None,
        city=None,
        source=BeneficiaryImportSources.demarches_simplifiees,
        source_id=None,
    )


def _process_creation(pre_subscription: BeneficiaryPreSubscription, procedure_id: int) -> None:
    new_beneficiary = beneficiary_pre_subscription_sql_converter.to_model(pre_subscription, import_details=False)
    try:
        repository.save(new_beneficiary)
    except ApiErrors as api_errors:
        logger.warning(
            "[BATCH][REMOTE IMPORT BENEFICIARIES] Could not save application %s, because of error: %s - Procedure %s",
            pre_subscription.application_id,
            api_errors,
            procedure_id,
        )
    else:
        logger.info(
            "[BATCH][REMOTE IMPORT BENEFICIARIES] Successfully created user for application %s - Procedure %s",
            pre_subscription.application_id,
            procedure_id,
        )
        save_beneficiary_import_with_status(
            ImportStatus.CREATED,
            pre_subscription.application_id,
            source=BeneficiaryImportSources.demarches_simplifiees,
            source_id=procedure_id,
            user=new_beneficiary,
        )
        try:
            send_activation_email(new_beneficiary, send_raw_email)
        except MailServiceException as mail_service_exception:
            logger.exception(
                "Email send_activation_email failure for application %s - Procedure %s : %s",
                pre_subscription.application_id,
                procedure_id,
                mail_service_exception,
            )


def _process_duplication(
    duplicate_users: List[User], pre_subscription: BeneficiaryPreSubscription, procedure_id: int
) -> None:
    number_of_beneficiaries = len(duplicate_users)
    duplicate_ids = ", ".join([str(u.id) for u in duplicate_users])
    message = f"{number_of_beneficiaries} utilisateur(s) en doublon {duplicate_ids} pour le dossier {pre_subscription.application_id} - Procedure {procedure_id}"
    logger.warning("[BATCH][REMOTE IMPORT BENEFICIARIES] Duplicate beneficiaries found : %s", message)
    save_beneficiary_import_with_status(
        ImportStatus.DUPLICATE,
        pre_subscription.application_id,
        source=BeneficiaryImportSources.demarches_simplifiees,
        source_id=procedure_id,
        detail=f"Utilisateur en doublon : {duplicate_ids}",
    )


def _process_rejection(pre_subscription: BeneficiaryPreSubscription, procedure_id: int) -> None:
    save_beneficiary_import_with_status(
        ImportStatus.REJECTED,
        pre_subscription.application_id,
        source=BeneficiaryImportSources.demarches_simplifiees,
        source_id=procedure_id,
        detail="Compte existant avec cet email",
    )
    logger.warning(
        "[BATCH][REMOTE IMPORT BENEFICIARIES] Rejected application %s because of already existing email - Procedure %s",
        pre_subscription.application_id,
        procedure_id,
    )
