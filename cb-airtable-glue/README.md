# Airtable Glue

Glue code to connect different services City Bureau uses into a single Airtable CRM.

## Notes

- Based on update and/or sync pattern
- Pulling into multiple different tables

## SSM Parameters

All of the configuration values are stored in AWS SSM. Some of these values may be more externally relevant than others. They can be found and modified in AWS under Systems Manager and Parameter Store in the us-east-1 (default) region. In particular, QuickBooks credentials need to be occasionally refreshed, and the emails that will be contacted when this needs to happen are in:

- `/prod/lambda/airtableGlue/sns/alert/email`
- `/prod/lambda/airtableGlue/sns/quickbooks/email`

## Development

```shell
npm i
pipenv sync --dev
```
