#!/usr/bin/env python
# pylint: disable=wrong-import-position
from __future__ import print_function

import sys
import pprint
import argparse
import inspect
import datetime

sys.path.append('..')

from ask_jira.lib import timetracking
from ask_jira.lib import subissues
from ask_jira.lib import export_import
from ask_jira.lib import google_calendar
from ask_jira.utils.smart_argparse_formatter import SmartFormatter
from ask_jira.lib.core import get_jira

# helpers

def _make_jql_argument_parser(parser):
    parser.add_argument("jql", help="the JQL query used in the command")
    parser.add_argument('--verbose', default=False, action='store_true', help='If given, shows extra status information.')
    parser.add_argument('--assignee-field', help='The field name to use to read assignee user.')
    parser.add_argument('--assignable-users', help='A comma delimited list of users that can be assigned to.')
    return parser

def _make_jql_date_range_argument_parser(parser):
    parser.add_argument("jql", help="the JQL query used in the command")
    parser.add_argument("start_date", type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d').date(), help="the start date to filter results by")
    parser.add_argument("end_date", type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d').date(), help="the end date to filter results by")
    parser.add_argument('--verbose', default=False, action='store_true', help='If given, shows extra status information.')
    return parser

# commands

def projects(jira, args):
    """List available JIRA projects"""
    projects = jira.projects()
    print("Available JIRA projects:")
    pprint.pprint([project.name for project in projects])

def fields(jira, args):
    """List available JIRA field names and IDs"""
    print("Available JIRA fields (name, id):")
    pprint.pprint([(field['name'], field['id']) for field in jira.fields()])

def sum_timetracking_for_jql(jira, args):
    """Sum original estimate, time spent
    and time remaining for all issues that match the given JQL query"""
    results = timetracking.sum_timetracking_for_jql(jira, args.jql)
    pprint.pprint(results)

sum_timetracking_for_jql.argparser = _make_jql_argument_parser

def sum_assigned_hours_by_user_for_jql(jira, args):
    """
    Sums all hours assigned to each user.
    """
    results = timetracking.sum_assigned_hours_by_user_for_jql(jira, args.jql, verbose=args.verbose, assignee_field=args.assignee_field)
    pprint.pprint(results)

sum_assigned_hours_by_user_for_jql.argparser = _make_jql_argument_parser

def auto_assign_issues_for_jql(jira, args):
    """
    Auto assigns issues to users.
    """
    timetracking.auto_assign_issues_for_jql(jira, args.jql, verbose=args.verbose, assignee_field=args.assignee_field, assignable_users=args.assignable_users)

auto_assign_issues_for_jql.argparser = _make_jql_argument_parser

def sum_worklogs_by_user_for_jql(jira, args):
    """Sum original estimate, time spent
    and time remaining by user for all worklogs that match the given JQL query"""
    results = timetracking.sum_worklogs_by_user_for_jql(jira, args.jql, args.start_date, args.end_date, verbose=args.verbose)
    pprint.pprint(results)

sum_worklogs_by_user_for_jql.argparser = _make_jql_date_range_argument_parser

def set_story_points_from_hours(jira, args):
    timetracking.set_story_points_from_hours(jira, args.jql, verbose=args.verbose)

set_story_points_from_hours.argparser = _make_jql_argument_parser

def list_epics_stories_and_tasks_for_jql(jira, args):
    """Print a Markdown-compatible tree of epics,
    stories and subtasks that match the given JQL query"""
    results = subissues.list_epics_stories_and_tasks(jira, args.jql)
    print(results)

list_epics_stories_and_tasks_for_jql.argparser = _make_jql_argument_parser

def export_import_issues_for_jql(jira, args):
    """Export issues from one JIRA instance
    to another with comments and attachments"""
    import exportimportconfig # pylint: disable=import-error
    exported_issues = export_import.export_import_issues(jira,
            exportimportconfig, args.jql)
    print('Successfully imported', exported_issues)

export_import_issues_for_jql.argparser = _make_jql_argument_parser

def import_worklogs_from_google_calendar(jira, args):
    """Import worklog entries from Google Calendar
    to corresponding JIRA tasks"""
    import worklogconfig # pylint: disable=import-error
    hours = google_calendar.import_worklogs(jira, worklogconfig,
            args.calendar, args.fromdate, args.todate)
    print('Logged', hours, 'hours')

def _import_worklogs_argument_parser(parser):
    parser.add_argument("calendar", help="the calendar name to import "
            "worklogs from")
    parser.add_argument("fromdate", help="import date range start, "
            "in yyyy-mm-dd format")
    parser.add_argument("todate", help="import date range end, "
            "in yyyy-mm-dd format")
    return parser

import_worklogs_from_google_calendar.argparser = _import_worklogs_argument_parser

# main

def _main():
    command_name, command = _get_command()
    args = _parse_command_specific_arguments(command_name, command)
    jira = get_jira()
    command(jira, args)

# helpers

def _make_main_argument_parser():
    parser = argparse.ArgumentParser(formatter_class=SmartFormatter)
    parser.add_argument("command", help="R|the command to run, available " +
            "commands:\n{0}".format(_list_local_commands()))
    return parser

def _get_command():
    argparser = _make_main_argument_parser()
    def print_help_and_exit():
        argparser.print_help()
        sys.exit(1)
    if len(sys.argv) < 2:
        print_help_and_exit()
    command_name = sys.argv[1]
    if not command_name[0].isalpha():
        print_help_and_exit()
    if command_name not in globals():
        print("Invalid command: {0}\n".format(command_name), file=sys.stderr)
        print_help_and_exit()
    command = globals()[command_name]
    return command_name, command

def _list_local_commands():
    sorted_globals = list(globals().items())
    sorted_globals.sort()
    commands = [(var, obj.__doc__) for var, obj in sorted_globals
        if not var.startswith('_')
           and inspect.isfunction(obj)]
    return "\n".join("'{0}': {1}".format(name, doc) for name, doc in commands)

def _parse_command_specific_arguments(command_name, command):
    if not hasattr(command, 'argparser'):
        return None
    parser = argparse.ArgumentParser()
    parser.add_argument("command", help=command_name)
    command_argparser = command.argparser(parser)
    return command_argparser.parse_args()

if __name__ == "__main__":
    _main()
