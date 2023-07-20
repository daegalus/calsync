#!/usr/bin/env python
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
    
    result = getSchedule()
    if result:
        schedule, busy = result

        meeting_status = hac.get_entity(entity_id="input_select.meeting_status")
        if meeting_status:
            if busy:
                meeting_status.state.state = "In Meeting"
            else:
                meeting_status.state.state = "No Meeting"
            
            if len(schedule) > 0:
                meeting_status.state.attributes["start_time"] = schedule[0]["start"]
                meeting_status.state.attributes["end_time"] = schedule[0]["end"]
                meeting_status.state.attributes["summary"] = schedule[0]["summary"]
                meeting_status.state.attributes["schedule"] = schedule
            else:
                meeting_status.state.attributes["start_time"] = ""
                meeting_status.state.attributes["end_time"] = ""
                meeting_status.state.attributes["summary"] = ""
                meeting_status.state.attributes["schedule"] = []
            meeting_status.update_state()
    
def getSchedule():
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
        nowPST = datetime.datetime.now()
        endOfWorkDayPST = nowPST.replace(hour=17, minute=0, second=0, microsecond=0)
        endOfWorkDayUTC = endOfWorkDayPST.astimezone(datetime.timezone.utc).isoformat()
        print('Getting the upcoming 10 events for the day')
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              timeMax=endOfWorkDayUTC,
                                              maxResults=10, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        ha_events = []
        busy = False
        if not events:
            print('No upcoming events found.')
            return [], busy

        # Prints the start and name of the next 10 events within the workday.
        for event in events:
            attendees = event.get('attendees', [])
            for attendee in attendees:
                if attendee['email'] == 'yulian@unity3d.com' and attendee['responseStatus'] == 'accepted':
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    end = event['end'].get('dateTime', event['end'].get('date'))
                    nowTZ = nowTime.astimezone()
                    eventStart = datetime.datetime.fromisoformat(start).astimezone()
                    eventEnd = datetime.datetime.fromisoformat(end).astimezone()

                    print(start, end, event['summary'])
                    ha_events.append({'start': eventStart.strftime("%I:%M %p"), 'end': eventEnd.strftime("%I:%M %p"), 'summary': event['summary']})

                    

                    if eventStart <= nowTZ and eventEnd > nowTZ:
                        busy = True

        print("ha_events", ha_events)
        return ha_events, busy

    
    except HttpError as error:
        print('An error occurred: %s' % error)

if __name__ == '__main__':
    main()