"""File holding a list of constant variables used throughout the gluecode"""

import os

AIRTABLE_KEY = os.getenv("AIRTABLE_KEY")
AIRTABLE_BASE = os.getenv("AIRTABLE_BASE") # "CB CRM" base

SOCIAL_BASE = os.getenv("SOCIAL_BASE")
EDITORIAL_BASE = os.getenv("EDITORIAL_BASE", "applK7WF1q53lIBhH")

# TODO: move to SSM parameter store
OPERATIONS_BASE = "appSHhUCnbzLYR2TW"
DOCS_SUPERBASE = "appcbqSzBInSVG4Kz"

CRM_BASE_SYNC_SHEET_KEY = "1qHvosNC3KYzLeGWshkPJ6_b50bBftDijpF2MpRbE0Ec" # "1ZNzkDFMbu3WDoxtH8PbOT2lkZnebrduvwOqY_tNBBc8"
DOCS_SUPERBASE_SYNC_SHEET_KEY = "1igbGvZ4RZbAPlBeRWeSilRFpr5x5J0oc-dbbA1-DxWI"

NEWSLETTER_LIST_ID = "b23151cc2f"

RECURRING_DONOR_CATEGORY_ID = "f8d632e55e"

MAILCHIMP_ID_INTEREST_MAP = {
    "ac958076c3": "City Bureau Update",
    "7eacddfd78": "City Bureau Notebook",
    "3936ae61e2": "Web Sign Ups",
    "602a3decd0": "Town Halls",
    "1d2a94bf4d": "Web Donation",
    "38fec59b53": "Documenters.org",
    "01aed1222a": "City Scrapers",
    "39767edd06": "Public Newsroom",
    "5944760519": "Bronze",
    "29653575ba": "Silver",
    "460159aa24": "Gold",
    "8bbbdc23df": "Recurring",
    "d60bfcd272": "hasmyaldermanbeenindicted.com",
}

MAILCHIMP_INTEREST_ID_MAP = {v: k for k, v in MAILCHIMP_ID_INTEREST_MAP.items()}

DONOR_MAILCHIMP_INTERESTS = {
    "Bronze": "5944760519",
    "Silver": "29653575ba",
    "Gold": "460159aa24",
    "Recurring": "8bbbdc23df",
}
