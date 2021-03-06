import logging

from pcapi.scripts.payment.batch_steps import generate_new_payments


logger = logging.getLogger(__name__)


def create_industrial_payments():
    logger.info("create_industrial_payments")

    pending_payments, not_processable_payments = generate_new_payments()

    logger.info("created %d payments", len(pending_payments + not_processable_payments))
