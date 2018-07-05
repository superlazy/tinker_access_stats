from tinker_access_histogram import *
import os


def test_get_machine_usage_history():
    # read the slack token from a file not in version control
    slack_bot_token = open(os.environ['HOME'] + '/.ssh/slack_bot_tinker_access_stats').read().strip()

    # get the history of the channel
    history = get_machine_usage_history(slack_bot_token=slack_bot_token)

    f = open('/tmp/1-week-sample.json', 'w')
    f.write(json.dumps(history))
    f.close()

    # make sure the request was successful
    assert(history['ok'])
    assert(len(history['messages']) > 0)


def test_build_machine_usage_summary():
    # get the history of the channel from a sample resource file
    f = open('../test-resources/6-week-sample.json', 'r')
    history = json.loads(f.read())

    if history['ok']:
        summary = build_machine_usage_summary(messages=history['messages'])
        print(json.dumps(summary))


if __name__ == '__main__':
    # test_get_machine_usage_history()
    test_build_machine_usage_summary()
    # lambda_generate_stats(None, None)
