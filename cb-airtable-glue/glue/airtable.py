"""Basic functions to connect to Airtable & read / write data"""

from itertools import zip_longest

import requests

from glue.constants import AIRTABLE_BASE, AIRTABLE_KEY


def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


def dt_format(dt):
    """Format date so all dates in airtable are the same"""
    if not dt:
        return None
    if isinstance(dt, str):
        return f"{dt[:19]}Z"
    return f"{dt.isoformat()[:19]}Z"


def diff_fields(obj, airtable):
    """check if a dict (`obj`) matches another dict representing an Airtable record (`airtable`), and if not, return True to indicate that the Airtable record needs to be updated"""
    for key, value in obj.items():
        # some massaging is necessary to account for empty fields in Airtable...
        if (
            (isinstance(value, list) and len(value) == 0)
            or (isinstance(value, str) and value.strip() == "")
            or (isinstance(value, bool) and not value)
        ):
            value = None
        # ...and datetimes
        elif (
            isinstance(value, str)
            and isinstance(airtable["fields"].get(key), str)
            and airtable["fields"].get(key).endswith(".000Z")
        ):
            value = f"{value[:19]}.000Z"
        if value != airtable["fields"].get(key):
            return True
    return False


def sync_table(records, table, id_field="ID", base=AIRTABLE_BASE):
    """Sync Airtable table with records from another system.

       Returns a dict that maps the primary key values from both systems to the Airtable record ID
    """
    airtable_records = load_table(base, table)
    airtable_pk_map = {
        r["fields"][id_field]: r for r in airtable_records if id_field in r["fields"]
    }
    # records from the other system that don't exist in Airtable
    records_to_create = [r for r in records if r[id_field] not in airtable_pk_map]
    # records that exist in both systems but have been modified in the other system
    records_to_update = [
        r
        for r in records
        if r[id_field] in airtable_pk_map
        and diff_fields(r, airtable_pk_map[r[id_field]])
    ]
    created_records = create_batch_records(base, table, records_to_create)
    for record in records_to_update:
        create_update_record(
            base, table, record, update_id=airtable_pk_map[record[id_field]]["id"]
        )
    record_id_map = {
        r["fields"][id_field]: r["id"]
        for r in airtable_records
        if id_field in r["fields"]
    }
    for record in created_records:
        if record.get("fields"):
            record_id_map[record["fields"][id_field]] = record["id"]
    return record_id_map


def load_table(base, table, formula=None, view=None, fields: list = None, max_records=None):
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


def create_batch_records(base, table, records):
    """Create records in batches of size 10 with Airtable's batch API"""
    req_url = f"https://api.airtable.com/v0/{base}/{table}"
    created_records = []
    for record_group in grouper(records, 10):
        res = requests.post(
            req_url,
            headers={"Authorization": f"Bearer {AIRTABLE_KEY}"},
            json={"records": [{"fields": rec} for rec in record_group if rec]},
        )
        res_data = res.json()
        created_records.extend(res_data.get("records", []))
    return created_records


def delete_batch_records(base, table, records):
    """Delete records in batches of size 10 with Airtable's batch API"""
    req_url = f"https://api.airtable.com/v0/{base}/{table}"
    for record_group in grouper(records, 10):
        requests.delete(
            req_url,
            headers={"Authorization": f"Bearer {AIRTABLE_KEY}"},
            params={"records[]": [rec["id"] for rec in record_group if rec]},
        )


def create_update_record(base, table, data, update_id=None):
    """Create or update an Airtable record based on whether update_id is set"""
    req = requests.patch if update_id else requests.post
    req_url = f"https://api.airtable.com/v0/{base}/{table}"
    if update_id:
        req_url += f"/{update_id}"
    res = req(
        req_url,
        headers={"Authorization": f"Bearer {AIRTABLE_KEY}"},
        json={"fields": data},
    )
    return res.json()


def get_record_by_formula(base, table, formula):
    """Returns first matching record by formula or None"""
    records = load_table(base, table, formula=formula, max_records=1)
    if len(records) > 0:
        return records[0]


def get_record_by_field(base, table, field, value):
    """Returns first matching record or None"""
    if isinstance(value, str):
        return get_record_by_formula(base, table, f'"{value}" = {{{field}}}')
    return get_record_by_formula(base, table, f"{field} = {value}")


def get_person_by_email(email):
    """
    Helper method for finding person across email fields
    Base → Table → View:
    CB CRM → People → all views
    """
    upper_email = email.upper()
    formula = """OR(
            "{e}" = UPPER(Email),
            "{e}" = UPPER({{Email 2}}),
            "{e}" = UPPER({{Email 3}})
        )""".format(
        e=upper_email
    )
    return get_record_by_formula(AIRTABLE_BASE, "People", formula)


def get_person_email_map():
    """
    Returns dictionary of records from People tab where Email field is not blank

    Creates key-value pair to map email to Person record ID for each email field (Email, Email 2, Email 3)
    and also creates additional pairs for all-lowercase versions of the email addresses
    """
    airtable_people = load_table(AIRTABLE_BASE, "People", formula="Email != BLANK()")
    airtable_people_map = {}
    for person in airtable_people:
        for email_field in ["Email", "Email 2", "Email 3"]:
            if person["fields"].get(email_field):
                airtable_people_map[person["fields"][email_field]] = person["id"]
                airtable_people_map[person["fields"]
                                    [email_field].lower()] = person["id"]
    return airtable_people_map
