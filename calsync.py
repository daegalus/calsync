from __future__ import print_function

import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from homeassistant_api import Client
from dotenv import load_dotenv

load_dotenv()

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

HA_API_URL = os.environ.get("HA_API_URL", "")
HA_API_TOKEN = os.environ.get("HA_API_TOKEN", "")

hac = Client(
    HA_API_URL,
    HA_API_TOKEN,
)

def main():
    if HA_API_URL == "" or HA_API_TOKEN == "":
        print("Please set HA_URL and HA_TOKEN directly or in .env")
        return
    
    result = isBusy()
    if result:
        start, end, busy = result

        meeting_status = hac.get_entity(entity_id="input_select.meeting_status")
        if meeting_status:
            if busy:
                meeting_status.state.state = "In Meeting"
                if meeting_status.state.attributes["start_time"] == "" or meeting_status.state.attributes["start_time"] == None:
                    meeting_status.state.attributes["start_time"] = start
                meeting_status.state.attributes["end_time"] = end
                meeting_status.update_state()
            else:
                meeting_status.state.state = "No Meeting"
                meeting_status.state.attributes["start_time"] = ""
                meeting_status.state.attributes["end_time"] = ""
                meeting_status.update_state()

def isBusy():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=59999, open_browser=False)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('calendar', 'v3', credentials=creds)

        # Call the Calendar API
        nowTime = datetime.datetime.utcnow()
        now = nowTime.isoformat() + 'Z'  # 'Z' indicates UTC time
        # print('Getting the upcoming 10 events')
        # events_result = service.events().list(calendarId='primary', timeMin=now,
        #                                       maxResults=10, singleEvents=True,
        #                                       orderBy='startTime').execute()
        # events = events_result.get('items', [])

        # if not events:
        #     print('No upcoming events found.')
        #     return

        # # Prints the start and name of the next 10 events
        # for event in events:
        #     start = event['start'].get('dateTime', event['start'].get('date'))
        #     print(start, event['summary'])

        free_busy = service.freebusy().query(body={
            "timeMin": now,
            "timeMax": (nowTime + datetime.timedelta(days=1)).isoformat() + 'Z',
            "timeZone": "America/Los_Angeles",
            "items": [{"id": "primary"}]
        }).execute()

        if not free_busy:
            print('No upcoming events found.')
            return
        
        event = free_busy['calendars']['primary']['busy'][0]
        nowTZ = datetime.datetime.now().astimezone()
        eventStart = datetime.datetime.fromisoformat(event['start'])
        eventStartAdj = eventStart.astimezone()
        if eventStartAdj.minute != 0 or eventStartAdj.minute != 30:
            if eventStartAdj.minute < 30:
                eventStartAdj = eventStartAdj.replace(minute=0)
            else:
                eventStartAdj = eventStartAdj.replace(minute=30)
        
        eventEnd = datetime.datetime.fromisoformat(event['end'])
        return tuple([eventStart.strftime("%I:%M %p"), eventEnd.strftime("%I:%M %p"), nowTZ > eventStart and nowTZ < eventEnd])
    
    except HttpError as error:
        print('An error occurred: %s' % error)

if __name__ == '__main__':
    main()