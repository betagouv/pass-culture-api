from flask import flash
from flask import redirect
from flask import request
from flask import url_for
from flask_admin import expose
from flask_admin.form import SecureForm
from flask_login import current_user
from markupsafe import Markup
import wtforms
import wtforms.validators

import pcapi.core.users.api as users_api
import pcapi.core.users.constants as users_constants
from pcapi.models.user_sql_entity import UserSQLEntity


class SuspensionForm(SecureForm):
    reason = wtforms.SelectField(
        "Raison de la suspension",
        choices=(("", "---"),) + users_constants.SUSPENSION_REASON_CHOICES,
        validators=[wtforms.validators.InputRequired()],
    )


class UnsuspensionForm(SecureForm):
    pass  # empty form, only has the CSRF token field


def _action_links(view, context, model, name):
    if model.isActive:
        url = url_for(".suspend_user_view")
        text = "Suspendre&hellip;"
    else:
        url = url_for(".unsuspend_user_view")
        text = "Réactiver&hellip;"

    return Markup(f'<a href="{url}?user_id={model.id}">{text}</a>')


class SuspensionMixin:
    """Provide links in the "actions" column to suspend or unsuspend any
    user with a confirmation form.
    """

    @property
    def column_formatters(self):
        formatters = super().column_formatters
        formatters.update(actions=_action_links)
        return formatters

    @property
    def user_list_url(self):
        return url_for(".index_view")

    @expose("suspend", methods=["GET", "POST"])
    def suspend_user_view(self):
        user_id = request.args["user_id"]
        user = UserSQLEntity.query.get(user_id)

        if request.method == "POST":
            form = SuspensionForm(request.form)
            if form.validate():
                flash(f"Le compte de l'utilisateur {user.email} ({user.id}) a été suspendu.")
                users_api.suspend_account(user, form.data["reason"], current_user)
                return redirect(self.user_list_url)
        else:
            form = SuspensionForm()

        context = {
            "cancel_link_url": self.user_list_url,
            "user": user,
            "form": form,
        }
        return self.render("admin/confirm_suspension.html", **context)

    @expose("unsuspend", methods=["GET", "POST"])
    def unsuspend_user_view(self):
        user_id = request.args["user_id"]
        user = UserSQLEntity.query.get(user_id)

        if request.method == "POST":
            form = UnsuspensionForm(request.form)
            if form.validate():
                flash(f"Le compte de l'utilisateur {user.email} ({user.id}) a été réactivé.")
                users_api.unsuspend_account(user, current_user)
                return redirect(self.user_list_url)
        else:
            form = UnsuspensionForm()

        context = {
            "cancel_link_url": self.user_list_url,
            "user": user,
            "form": form,
        }
        return self.render("admin/confirm_unsuspension.html", **context)