from datetime import datetime
from typing import Iterable

from flask import current_app as app
from requests import Response

from pcapi import settings
from pcapi.utils.logger import logger

from ..models import MailResult
from .base import BaseBackend


def _add_template_debugging(message_data: dict) -> None:
    message_data["TemplateErrorReporting"] = {
        "Email": settings.DEV_EMAIL_ADDRESS,
        "Name": "Mailjet Template Errors",
    }


class MailjetBackend(BaseBackend):
    def _send(self, recipients: Iterable[str], data: dict) -> MailResult:
        data["To"] = ", ".join(recipients)

        if settings.MAILJET_TEMPLATE_DEBUGGING:
            messages_data = data.get("Messages")
            if messages_data:
                for message_data in messages_data:
                    _add_template_debugging(message_data)
            else:
                _add_template_debugging(data)

        try:
            response = app.mailjet_client.send.create(data=data)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Error trying to send e-mail with Mailjet: %s", exc)
            return MailResult(
                sent_data=data,
                successful=False,
            )

        successful = response.status_code == 200
        if not successful:
            logger.warning("Got %d return code from Mailjet: content=%s", response.status_code, response.content)

        return MailResult(
            sent_data=data,
            successful=successful,
        )

    def create_contact(self, email: str) -> Response:
        data = {"Email": email}
        return app.mailjet_client.contact.create(data=data)

    def update_contact(self, email: str, *, birth_date: datetime, department: str) -> Response:
        birth_timestamp = int(datetime(birth_date.year, birth_date.month, birth_date.day).timestamp())

        data = {
            "Data": [
                {"Name": "date_de_naissance", "Value": birth_timestamp},
                {"Name": "département", "Value": department},
            ]
        }
        return app.mailjet_client.contactdata.update(id=email, data=data)

    def add_contact_to_list(self, email: str, list_id: str) -> Response:
        data = {
            "IsUnsubscribed": "false",
            "ContactAlt": email,
            "ListID": list_id,
        }
        return app.mailjet_client.listrecipient.create(data=data)


class ToDevMailjetBackend(MailjetBackend):
    """A backend where the recipients are overriden.

    This is the backend that should be used on testing and staging
    environments.
    """

    def _inject_html_test_notice(self, recipients, data):
        if "Html-part" not in data:
            return
        notice = (
            f"<p>This is a test (ENV={settings.ENV}). "
            f"In production, this email would have been sent to {', '.join(recipients)}</p>"
        )
        data["Html-part"] = notice + data["Html-part"]

    def send_mail(self, recipients: Iterable[str], data: dict) -> MailResult:
        self._inject_html_test_notice(recipients, data)
        recipients = [settings.DEV_EMAIL_ADDRESS]
        return super().send_mail(recipients=recipients, data=data)

    def create_contact(self, email: str) -> Response:
        email = settings.DEV_EMAIL_ADDRESS
        return super().create_contact(email)

    def update_contact(self, email: str, **kwargs) -> Response:
        email = settings.DEV_EMAIL_ADDRESS
        return super().update_contact(email, **kwargs)

    def add_contact_to_list(self, email: str, *args, **kwargs) -> Response:
        email = settings.DEV_EMAIL_ADDRESS
        return super().add_contact_to_list(email, *args, **kwargs)