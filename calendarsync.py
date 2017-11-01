#!/usr/bin/env python

from urllib.request import urlopen
import urllib
import sys
import re
import yaml
import icalendar
import caldav

def sync(config_file):
    config = yaml.load(open(config_file))
    cd_client = caldav.DAVClient(config['caldav']['url'],
                                 None,
                                 config['caldav']['username'],
                                 config['caldav']['password'])
    cd_principal = cd_client.principal()
    cd_calendars = cd_principal.calendars()

    cd_calendar = None
    for c in cd_calendars:
        display_name = c.get_properties([caldav.objects.dav.DisplayName(),])
        display_name = display_name['{DAV:}displayname']
        if display_name == config['caldav']['calendar']:
            cd_calendar = c

    if cd_calendar is None:
        print('Could not find calendar "{}".'.format(config['caldav']['calendar']))
        exit(-1)

    with urlopen(config['ical']['url']) as f:
        ical_calendar = icalendar.Calendar.from_ical(f.read())

    cd_events = list(get_caldav_events(cd_calendar))
    ical_events = list(get_ical_events(ical_calendar))

    events_to_add = [event for event in ical_events if event not in cd_events]
    events_to_remove = [event for event in cd_events if event not in ical_events]

    for e in cd_calendar.events():
        component = icalendar.Event.from_ical(e.data).subcomponents[0]
        event = strip_ical(component.to_ical())
        if event in events_to_remove:
            print('Deleting event "{}".'.format(component.get('summary')))
            e.delete()

    for e in events_to_add:
        vcal = b'BEGIN:VCALENDAR\r\nVERSION:2.0\r\n' + e + b'END:VCALENDAR\r\n'
        summary = re.search(b'SUMMARY:(.+)\r\n', e).group(1).decode("utf-8")
        print('Adding event "{}".'.format(summary))
        cd_calendar.add_event(vcal)

    print("Finished")

def strip_empty_lines(string):
    pass

def get_caldav_events(calendar):
    events = calendar.events()
    for e in events:
        yield strip_ical(icalendar.Event.from_ical(e.data).subcomponents[0].to_ical())

def get_ical_events(calendar):
    for component in calendar.walk(name = 'VEVENT'):
        yield strip_ical(component.to_ical())

def strip_ical(event):
    # event = re.sub(b'\r\nSTATUS:.*\r\n', b'\r\n', event)
    event = re.sub(b'\r\nDTSTAMP:.*\r\n', b'\r\n', event)
    event = re.sub(b'\r\nBEGIN:VALARM.*END:VALARM\r\n', b'\r\n', event, 0, re.DOTALL)
    return event

if __name__ == "__main__":
    if len(sys.argv) > 1:
        sync(sys.argv[1])
    else:
        sync('config.yaml')
