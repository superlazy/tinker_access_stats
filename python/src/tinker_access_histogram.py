import urllib.request as req
import json
import time
import operator
import os
import boto3
from time import sleep
from datetime import datetime


def lambda_generate_stats(event, context):

    attempts = 0
    has_messages = False
    while attempts < 5 and not has_messages:
        token = os.environ['SLACK_BOT_TOKEN']
        history = get_machine_usage_history(slack_bot_token=token)
        summary = build_machine_usage_summary(messages=history['messages'])
        has_messages = len(history['messages']) > 0
        if not has_messages:
            print('Attempt ' + str(attempts) + ' failed to return messages')
            sleep(0.5)

    if not has_messages:
        print('No messages returned from Slack API')
        return

    bucket = 'tinker-access'
    key = 'tinker-access-stats.json'

    s3 = boto3.client('s3')
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(summary).encode()
    )

    s3 = boto3.resource('s3')
    object_acl = s3.ObjectAcl(bucket, key)
    object_acl.put(ACL='public-read')


def get_machine_usage_history(weeks=6, slack_bot_token=None, channel_id='C0K5VBMPS'):
    """
    Get the machine usage history from Slack for the last N days.  Make as many queries
    as necessary until the 'has_more' attribute in the response is false.
    :param weeks: {int} Retrieve history for the last N weeks
    :param slack_bot_token: {str} The slack bot access token (required)
    :param channel_id: {str} The #machine-usage channel ID (currently is C0K5VBMPS)
    :return: {dict} The slack API response as a dictionary
    """
    print('Token: ' + slack_bot_token)
    print('Channel: ' + channel_id)
    print('Weeks: ' + str(weeks))

    # verify that we have an access token
    if slack_bot_token is None:
        raise Exception('Parameter slack_bot_token is required')

    # build values for start and end times
    weeks //= 1  # integer number of weeks
    latest = time.time()
    oldest = latest - (weeks * 7 * 86400)

    # an array to hold messages
    messages = []

    # initialize parameters before loop
    has_more = True
    history = {}

    # count the failed requests
    error_bug_count = 0

    # continue to make requests to the slack api as long as there are more messages
    while has_more:
        # build the request url
        url = 'https://slack.com/api/channels.history' + \
                '?token=' + slack_bot_token + \
                '&channel=' + channel_id + \
                '&oldest=' + str(oldest) + \
                '&latest=' + str(latest)

        # make the request
        response = req.urlopen(url)
        if response.getcode() != 200:
            raise Exception('Error reading url: ' + url)

        # parse and return a successful response
        history = json.loads(response.read().decode('utf-8'))

        # check for errors returned from the response
        if not history['ok']:
            print('Request failed: ' + history['error'])
            exit(1)

        # add the messages to our array aggregate
        for message in history['messages']:
            messages.append(message)

        # set our flag to loop again or exit
        has_more = history['has_more']

        # if there are more messages, set the latest query time to the timestamp in the last message
        if has_more:
            latest = float(history['messages'][99]['ts'])

        # if there are no messages return, slack may have had an error
        # this happened several times during testing.  Slack bug or user error?
        if len(history['messages']) == 0:
            error_bug_count += 1
            if error_bug_count <= 10:
                has_more = True

        # Debug
        print('  Total messages: ' + str(len(messages)))

    # return the history message with our aggregated messages array
    history['messages'] = messages
    return history


def build_machine_usage_summary(messages=None, weeks=6):
    """"
    Build a usage summary from the messages
    :param messages: A list of messages to parse
    :return:
    """
    events = __get_machine_events(messages)
    events = __sort_and_clean_events(events)
    summary = __summarize_machine_usage(events, weeks)

    return summary


def __get_machine_events(messages):
    events = {}

    # parse all of the events and put them in an ordered dictionary indexed by machine
    for message in messages:
        # only consider messages from the tinker access slack bot
        if 'username' not in message or message['username'] != 'incoming-webhook':
            continue

        # parse some fields from the message
        timestamp = float(message['ts'])
        text = message['text']
        tokens = text.split(' is now ')
        machine = tokens[0]
        status = None
        if tokens[1].startswith('available'):
            status = 'available'
        elif tokens[1].startswith('in use'):
            status = 'in use'

        # make sure we found a valid status
        if status is None:
            print('Unable to parse valid status: ' + text)

        # create a new list for the machine before events are added
        if machine not in events:
            events[machine] = []

        # add the new event
        events[machine].append({'time': timestamp, 'status': status})

    return events


def __sort_and_clean_events(events):
    """
    Sort and clean the events
    :param events: Raw list of events
    :return: A sorted and QC'd list of events
    """
    # sort the array for each machine
    for machine in events.keys():
        events[machine].sort(key=operator.itemgetter('time'))

    # convert timestamps to a naive Mountain Time Zone
    for machine in events.keys():
        for event in events[machine]:
            # TODO: Standard Time vs. Daylight Saving Time
            event['time'] = event['time'] - (6 * 3600)

    # clean up the data - make sure there are not multiple consecutive and
    # identical statuses (i.e., 'in use' and 'available' should alternate)
    for machine in events.keys():
        i = 0
        while i < len(events[machine]) - 1:
            if events[machine][i]['status'] == events[machine][i+1]['status']:
                events[machine].pop(i)  # I'll gladly pay you Tuesday for a hamburger today
                i -= 1
            i += 1

    # first status in each event list should be an 'in use'
    for machine in events.keys():
        if events[machine][0]['status'] != 'in use':
            events[machine].pop(0)

    return events


def __summarize_machine_usage(events, weeks):
    """
    Create a data structure that can be used to easily create usage histograms
    :param events: List of events
    :return:
    """
    # create an empty summary structure
    days_of_week_to_string = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    summary = {}
    for machine in events.keys():
        summary[machine] = {}
        for day in days_of_week_to_string:
            summary[machine][day] = [0] * 24

    intervals = {}
    for machine in events.keys():
        intervals[machine] = []
        for i in range(0, len(events[machine]) - 1, 2):
            start = events[machine][i]
            end = events[machine][i+1]
            start_dt = datetime.utcfromtimestamp(start['time'])
            duration = end['time'] - start['time']
            interval = {'start': start_dt, 'duration': duration}
            intervals[machine].append(interval)

    for machine in intervals.keys():
        for interval in intervals[machine]:
            day_of_week = interval['start'].weekday()
            seconds = interval['duration'] // 1
            hour = interval['start'].hour
            seconds_to_end_of_first_hour = 3600 - (interval['start'].timestamp() % 3600)
            if seconds > seconds_to_end_of_first_hour:
                summary[machine][days_of_week_to_string[day_of_week]][hour] += seconds_to_end_of_first_hour
                seconds -= seconds_to_end_of_first_hour
                hour += 1
                if hour >= 24:
                    hour = 0
                    day_of_week = (day_of_week + 1) % 7

            while seconds > 0:
                if seconds >= 3600:
                    summary[machine][days_of_week_to_string[day_of_week]][hour] += 3600
                    seconds -= 3600
                else:
                    summary[machine][days_of_week_to_string[day_of_week]][hour] += seconds
                    seconds = 0
                hour += 1
                if hour >= 24:
                    hour = 0
                    day_of_week = (day_of_week + 1) % 7

    # adjust seconds to fractional time used
    max_seconds = 3600 * weeks
    for machine in summary.keys():
        for day in summary[machine].keys():
            for hour in range(24):
                summary[machine][day][hour] /= max_seconds
                summary[machine][day][hour] = (summary[machine][day][hour] * 100 // 1) / 100

    summary['updated'] = int(datetime.now().timestamp())

    return summary
