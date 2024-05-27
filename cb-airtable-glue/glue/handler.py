"""
Contains functions needed for a lot of the backend processes completed by 
other functions in the gluecode, such as setting up webhooks, 
callback authorizations, and scripts to complete scheduled jobs. 
Also functions which sync data from other systems with Airtable.
"""

import json
import os
from datetime import datetime, timedelta

import pytz
import sentry_sdk
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

from glue.donorbox import sync_donorbox, sync_additional_donation_transaction_data
from glue.google import create_yamm_google_sheet, standuply_contact_webhook  # noqa
from glue.integrations import (
    add_one_time_donor_to_mailchimp,
    link_transactions,
    membership_donor_slack,
)
from glue.mailchimp import handle_subscribe, handle_unsubscribe, sync_open_rate
from glue.newsletters import update_newsletters
from glue.operations import sync_leave_balance
from glue.quickbooks import (
    get_quickbooks_auth_url,
    sync_bills,
    update_quickbooks_auth_ssm,
)
from glue.square import sync_square
from glue.stripe import create_update_charge, sync_stripe
from glue.paypal import sync_paypal
from glue.airtable_to_sheets import sync_tables_to_sheets

sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"), integrations=[AwsLambdaIntegration()])


def donorbox_cron(event, context):
    sync_donorbox()
    sync_additional_donation_transaction_data(date_from=datetime.now() - timedelta(days=3),
                                              date_to=datetime.now())


def mailchimp_cron(event, context):
    sync_open_rate()


def mailchimp_webhook(event, context):
    data = json.loads(event["body"])
    if data["type"] == "subscribe":
        handle_subscribe(data)
    elif data["type"] == "unsubscribe":
        handle_unsubscribe(data)
    return {"statusCode": 200, "body": ""}


# added sync_paypal invocation here because this stripe_cron seems to be handling syncing for all 3rd party payment processors.
# TODO rename stripe_cron for clarity.


def stripe_cron(event, context):
    sync_square()
    sync_paypal(start_date=(datetime.now() - timedelta(days=2)),
                end_date=datetime.now())
    sync_stripe(since=datetime.now() - timedelta(days=2))


def stripe_webhook(event, context):
    data = json.loads(event["body"])
    if data["type"] == "charge.succeeded":
        charge = data["data"]["object"]
        create_update_charge(charge)
        add_one_time_donor_to_mailchimp(charge)
    return {"statusCode": 200, "body": ""}


def slack_standup_cron(event, context):
    weekly_standup_report()


def slack_member_donor_cron(event, context):
    membership_donor_slack()


def maintenance_cron(event, context):
    link_transactions()
    sync_tables_to_sheets()


def leave_cron(event, context):
    sync_leave_balance()


def newsletter_analytics_cron(event, context):
    update_newsletters()


def quickbooks_oauth(event, context):
    return {
        "statusCode": "301",
        "headers": {"Location": get_quickbooks_auth_url()},
        "body": json.dumps({}),
    }


def quickbooks_oauth_callback(event, context):
    print(event)
    update_quickbooks_auth_ssm(event)
    return {"statusCode": "200", "body": json.dumps({"message": "Success"})}


def quickbooks_cron(event, context):
    tz = pytz.timezone("America/Chicago")
    utc_now = tz.localize(datetime.now()).astimezone(pytz.utc)
    #sync_bills(modified_since=utc_now - timedelta(hours=24)) #### temporarily deprecated Dec 2022 per Eli & Harry, pending functionality updates


def google_sheets_yamm_post(event, context):
    data = json.loads(event["body"])
    sheet_data = create_yamm_google_sheet(data["name"], data["records"])
    return {
        "statusCode": "200",
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": True,
            "Content-Type": "application/json",
        },
        "body": json.dumps(sheet_data),
    }


# def standuply_contact_webhook(event, context):
#     return standuply_contact_tracing(event)
