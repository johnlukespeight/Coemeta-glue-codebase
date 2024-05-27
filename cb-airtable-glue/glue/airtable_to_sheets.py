"""Syncs Airtable tables to a Google Sheet, replicating table names as the sheet (spreadsheet tab) name.

Requires: 
    - a Google Sheet key (id)
    - GCP Service Account credential file
    - Airtable base key (id)
    - Airtable API key

TODO: move these details to README
Google Sheet keys can be found by opening the Google Sheet in a browser, and looking at the URL. 
It is the string of characters after the "/d/" and before the "/edit" in the URL. 
    - E.g. https://docs.google.com/spreadsheets/d/1ZNzkDFMbu3WDoxtH8PbOT2lkZnebrduvwOqY_tNBBc8/edit#gid=0
      Key  = "1ZNzkDFMbu3WDoxtH8PbOT2lkZnebrduvwOqY_tNBBc8"

The gspread_pandas package is used to write to Google Sheets. 
It requires a Google Cloud Platform Service Account credential file (or other method) to authenticate with Google Sheets.
See https://gspread-pandas.readthedocs.io/en/latest/configuration.html for more information.

    - GCP Service Account credential files can be found by opening the Google Cloud Platform console, 
      navigating to the IAM & Admin section, & clicking on "Service Accounts". 
      See https://cloud.google.com/iam/docs/creating-managing-service-accounts for more information.

Airtable base keys can be found by opening the Airtable base in a browser & looking at the URL.
It will be the string of characters starting with "app" between two slashes.
    - E.g. https://airtable.com/appEWbZQUnzpOo2wC/tblpMnEuwM9JV7reR/viwtzMrXHm9aQ5d87?blocks=hide
      Key = "appEWbZQUnzpOo2wC"

Airtable tables & views can be referred to by name, or by ID (seen in URL above).

Airtable API keys can be found by opening the Airtable base in a browser & clicking on the "Help" menu in the top right corner.
Click on "API documentation", then click on "Authentication". 
"""

import pandas as pd
import os
import json
import gspread_pandas as gsp
from glue.airtable import load_table
#how do i import the load_table function from airtable.py?


def load_table(base, table, formula=None, view=None, fields: list = None, max_records=None):
    #Load all records from Airtable table with optional formula filter
    offset = ""
    has_offset = True
    records = []

    while has_offset:
        url = f"https://api.airtable.com/v0/{base}/{table}?pageSize=100"
        if max_records:
            url += f"&maxRecords={max_records}"
        if view:
            url += f"&view={view}"
        if formula:
            url += f"&filterByFormula={formula}"
        if fields:
            # convoluted code to accomplish URL encoding of field names supplied to function as a list, 
            # as well as strange query parameter syntax required by Airtable API, see following links:
            # - https://airtable.com/developers/web/api/list-records#query-fields
            # - https://community.airtable.com/t5/development-apis/using-the-quot-fields-quot-query-parameter-in-appgyver/td-p/67817
            # - https://codepen.io/airtable/full/MeXqOg
            url += "&fields%5B%5D="+"&fields%5B%5D=".join(list(map(requests.utils.quote, fields))) 
        if offset:
            url += f"&offset={offset}"
        res = requests.get(url, headers={"Authorization": f"Bearer {AIRTABLE_KEY}"})
        data = res.json()
        records.extend(data["records"])
        if "offset" in data:
            offset = data["offset"]
        else:
            has_offset = False
    return records

from glue.constants import AIRTABLE_BASE, CRM_BASE_SYNC_SHEET_KEY, DOCS_SUPERBASE, DOCS_SUPERBASE_SYNC_SHEET_KEY

from itertools import zip_longest
import requests

AIRTABLE_BASE = "appRkVGbRa896QESw"
CRM_BASE_SYNC_SHEET_KEY = "1QjmmlrXlKyNf3GZUSgeVNi0fxRVbhtwlIVhK8qvR7ns"
AIRTABLE_KEY = (
    "patNepFl5zIBWAv6U.e005573596a8d51b665687907e6b61fecdd83525d3d0506f2d7cc5a414d5577c"
)

# load google service account credentials from local JSON file
gsp_config = gsp.conf.get_config(
    conf_dir="C:\\Users\\johnl\\Desktop\\Software Development\\Coemeta\\cb-airtable-glue",
    file_name="coemeta-random-service-account.json",
)


def sync_airtable_to_sheets(
    gspread_config: dict,
    spreadsheet_key: str,
    base: str,
    table: str,
    view: str = None,
    fields: list = None,
) -> None:
    """Pulls records from an Airtable table & writes them to a Google Sheet tab, using the table name.
    Will create a new tab on the designated Google Sheet if it does not already exist.

    Depends on Pandas & Gspread Pandas libraries to write to Google Sheets, as well as internal load_table() function from this codebase.

    Args:
        gspread_config (gspread_pandas.conf.Config): gspread_pandas authentication config object.
        spreadsheet_key (str): Google Sheet key (ID for Spreadsheet tab, can be found in URL)
        base (str): Airtable base key (ID found in URL, begins with "app...")
        table (str): Airtable table name (can be display name or ID found in URL)
        view (str, optional): Airtable view name (can be display name or ID found in URL). Defaults to None.
        fields (list, optional): List of field names or IDs to include from table. Defaults to None, which returns all fields

    Returns:
        None or Exception: None if successful, Exception if error
    """

    try:
        # load Airtable table
        df = load_table(base=base, table=table, view=view, fields=fields)

        # Convert the records to a pandas dataframe
        df = pd.DataFrame(df)

        # Unnest the 'fields' column into individual columns
        df = pd.json_normalize(df["fields"])

        # Sort df columns to preserve order when replacing sheet (otherwise looker studio connection breaks)
        df = df.reindex(sorted(df.columns), axis=1)

        # create gspread object using gspread config established prior (see: https://gspread-pandas.readthedocs.io/en/latest/configuration.html for more information.),
        # using the Airtable table name as the "sheet" name (i.e. the spreadsheet tab), & creating it if it doesn't exist
        spread = gsp.Spread(
            config=gspread_config,
            spread=spreadsheet_key,
            sheet=table,
            create_sheet=True,
        )

        # write the dataframe to the Google Sheet, replacing the current data if the sheet (tab) already exists
        spread.df_to_sheet(df, replace=1)

    except Exception as e:
        print(f"Error: {e}")
        raise e


# map / dicts of Airtable tables with optional views & fields to sync to Google Sheet TODO: move to constants.py ?
# CB CRM base
# crm_tables_to_sync = {"CB CRM Base Metadata": {},
#    }


def sync_tables_to_sheets() -> None:
    """Syncs all tables in tables_to_sync list to Google Sheet.

    Args: none

    Returns:
        None or Exception: None if successful, Exception if error
    """

    # iterate through dicts to sync tables to the Google Sheet:
    for t in crm_tables_to_sync:
        try:
            sync_airtable_to_sheets(
                gspread_config=google_credentials_obj,
                spreadsheet_key=CRM_BASE_SYNC_SHEET_KEY,
                base=AIRTABLE_BASE,
                table=t,
                view=crm_tables_to_sync[t].get("view"),
                fields=crm_tables_to_sync[t].get("fields"),
            )

        except Exception as e:
            print(f"Error: {e}")
            raise e

    for t in docs_tables_to_sync:
        try:
            sync_airtable_to_sheets(
                gspread_config=google_credentials_obj,
                spreadsheet_key=DOCS_SUPERBASE_SYNC_SHEET_KEY,
                base=DOCS_SUPERBASE,
                table=t,
                view=docs_tables_to_sync[t].get("view"),
                fields=docs_tables_to_sync[t].get("fields"),
            )

        except Exception as e:
            print(f"Error: {e} when syncing {t}")
            raise e


# copied over from airtable.py for ease
def load_table(
    base, table, formula=None, view=None, fields: list = None, max_records=None
):
    """Load all records from Airtable table with optional formula filter"""
    offset = ""
    has_offset = True
    records = []

    while has_offset:
        url = f"https://api.airtable.com/v0/{base}/{table}?pageSize=100"
        if max_records:
            url += f"&maxRecords={max_records}"
        if view:
            url += f"&view={view}"
        if formula:
            url += f"&filterByFormula={formula}"
        if fields:
            # convoluted code to accomplish URL encoding of field names supplied to function as a list,
            # as well as strange query parameter syntax required by Airtable API, see following links:
            # - https://airtable.com/developers/web/api/list-records#query-fields
            # - https://community.airtable.com/t5/development-apis/using-the-quot-fields-quot-query-parameter-in-appgyver/td-p/67817
            # - https://codepen.io/airtable/full/MeXqOg
            url += "&fields%5B%5D=" + "&fields%5B%5D=".join(
                list(map(requests.utils.quote, fields))
            )
        if offset:
            url += f"&offset={offset}"
        res = requests.get(url, headers={"Authorization": f"Bearer {AIRTABLE_KEY}"})
        data = res.json()
        records.extend(data["records"])
        if "offset" in data:
            offset = data["offset"]
        else:
            has_offset = False
    return records

#Version 2

# Define a dictionary to store table information
tables_to_sync = {
    "CB CRM Base Metadata": {"view": None, "fields": None},
    # Add more tables as needed (would need to be hard coded, maybe annoying, but an idea)
}

# Modify the sync_tables_to_sheets function to use the tables_to_sync dictionary
def sync_tables_to_sheets() -> None:
    """Syncs all tables in tables_to_sync dictionary to Google Sheet."""
    try:
        # Iterate through the tables in tables_to_sync
        for table, info in tables_to_sync.items():
            sync_airtable_to_sheets(gspread_config=google_credentials_obj, 
                                    spreadsheet_key=CRM_BASE_SYNC_SHEET_KEY, 
                                    base=AIRTABLE_BASE, 
                                    table=table, 
                                    view=info.get("view"), 
                                    fields=info.get("fields"))
    except Exception as e:
        print(f"Error: {e}")
        raise e

# Call sync_tables_to_sheets() to sync all tables defined in tables_to_sync
sync_tables_to_sheets()

"""# example usage for individual / ad hoc run:
sync_airtable_to_sheets(
    gspread_config=gsp_config,
    spreadsheet_key=CRM_BASE_SYNC_SHEET_KEY,
    base=AIRTABLE_BASE,
    table="CB CRM Base Metadata",
    view=None,
)"""
