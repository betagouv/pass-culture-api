from flask import request

from pcapi.flask_app import public_api
from pcapi.validation.routes.bank_informations import check_demarches_simplifiees_webhook_payload
from pcapi.validation.routes.bank_informations import check_demarches_simplifiees_webhook_token
from pcapi.workers.bank_information_job import bank_information_job


# @debt api-migration
@public_api.route("/bank_informations/venue/application_update", methods=["POST"])
def update_venue_demarches_simplifiees_application():
    check_demarches_simplifiees_webhook_token(request.args.get("token"))
    check_demarches_simplifiees_webhook_payload(request)
    application_id = request.form["dossier_id"]
    bank_information_job.delay(application_id, "venue")
    return "", 202


# @debt api-migration
@public_api.route("/bank_informations/offerer/application_update", methods=["POST"])
def update_offerer_demarches_simplifiees_application():
    check_demarches_simplifiees_webhook_token(request.args.get("token"))
    check_demarches_simplifiees_webhook_payload(request)
    application_id = request.form["dossier_id"]
    bank_information_job.delay(application_id, "offerer")
    return "", 202
