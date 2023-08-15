import argparse
import json
import logging
import os
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException


def setup_brevo_configuration(api_key_file):

    with open(api_key_file) as fp:
        api_key = fp.read()

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = api_key

    return configuration


def add_contacts_to_brevo(api_key_file, contact_data):
    configuration = setup_brevo_configuration(api_key_file)
    api_instance = sib_api_v3_sdk.ContactsApi(sib_api_v3_sdk.ApiClient(configuration))

    request_contact_import = sib_api_v3_sdk.RequestContactImport()
    request_contact_import.json_body = contact_data
    request_contact_import.list_ids = [10]  # 'Contacts' list ID = 8
    request_contact_import.email_blacklist = False
    request_contact_import.sms_blacklist = False
    request_contact_import.update_existing_contacts = True
    request_contact_import.empty_contacts_attributes = False

    try:
        api_response = api_instance.import_contacts(request_contact_import)

        logging.debug(json.dumps(api_response, indent=4))

    except ApiException as err:
        print(err)


def convert_contacts_to_brevo_api_format(google_contact_data):
    brevo_api_data = []

    headers = google_contact_data[0]
    firstname_index = headers.index('First name')
    lastname_index = headers.index('Last name')
    email_index = headers.index('Email address')
    sms_index = headers.index('Contact number')

    for row in google_contact_data[1:]:
        brevo_api_data.append({
            'FIRSTNAME': row[firstname_index],
            'LASTNAME': row[lastname_index],
            'SMS': row[sms_index],  # Conversion from '07XXX XXXXX' to 447XXXXXXXX is handled by the API
            'EMAIL': row[email_index],
        })

    logging.debug(json.dumps(brevo_api_data, indent=4))

    return brevo_api_data


def setup_google_auth(api_credentials_file, api_token_file):
    creds = None
    scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']

    if os.path.exists(api_token_file):
        creds = Credentials.from_authorized_user_file(api_token_file, scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(api_credentials_file, scopes)
            creds = flow.run_local_server(port=0)

        with open(api_token_file, 'w') as token:
            token.write(creds.to_json())

    return creds


def get_contacts_from_google_sheets(api_credentials_file, api_token_file):
    creds = setup_google_auth(api_credentials_file, api_token_file)

    try:
        contact_spreadsheet_id = '1cUJgnziGuh8-2EiCTikdZ3UeOV7s6claB4peIJGE2MI'  # Taken from URL
        client = build('sheets', 'v4', credentials=creds)

        sheet = client.spreadsheets()
        rows = []
        offset = 0

        while True:
            result = sheet \
                .values() \
                .get(spreadsheetId=contact_spreadsheet_id, range=f'Contacts!A{offset + 1}:L{offset + 100}') \
                .execute()
            values = result.get('values', [])

            rows += values

            if len(values) != 100:
                break

            offset += 100

        logging.debug(json.dumps(rows, indent=4))

    except HttpError as err:
        print(err)

    return rows


def parse_args(argv):
    parser = argparse.ArgumentParser()

    parser.add_argument('--brevo-api-key-file', help='Path to text file containing a Brevo API key')
    parser.add_argument('--google-api-credentials-file', help='Path to JSON file containing Google API credentials')
    parser.add_argument(
        '--google-api-token-file', 
        help='Path to JSON file containing Google API token, if this does not exist it will be created'
    )

    return parser.parse_args()


def main():
    log_level = os.environ.get('LOGLEVEL')

    if log_level is not None:
        logging.basicConfig(level=log_level)

    args = parse_args(sys.argv[1:])

    google_contact_data = get_contacts_from_google_sheets(
        args.google_api_credentials_file, 
        args.google_api_token_file
    )
    brevo_compatible_contact_data = convert_contacts_to_brevo_api_format(google_contact_data)
    add_contacts_to_brevo(args.brevo_api_key_file, brevo_compatible_contact_data)


if __name__ == '__main__':
    main()

# FYI https://developers.google.com/sheets/api/quickstart/python
