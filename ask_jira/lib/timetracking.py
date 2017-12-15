from __future__ import print_function
import sys
from pprint import pprint

from dateutil.parser import parse

from jira.exceptions import JIRAError

from .workdays import WorkdaysFromSeconds

def get_field_map(jira):
    """
    Returns a dictionary mapping user friendly field name -> field id.
    """
    allfields = jira.fields()
    nameMap = {field['name']:field['id'] for field in allfields}
    return nameMap

def sum_timetracking_for_jql(jira, query):
    issues = jira.search_issues(query,
                                maxResults=1000,
                                fields="aggregatetimeestimate,aggregatetimespent,aggregatetimeoriginalestimate")
    total_planned = sum(issue.fields.aggregatetimeoriginalestimate
                        if issue.fields.aggregatetimeoriginalestimate else 0
                        for issue in issues)
    total_spent = sum(issue.fields.aggregatetimespent
                      if issue.fields.aggregatetimespent else 0
                      for issue in issues)
    total_remaining = sum(issue.fields.aggregatetimeestimate
                          if issue.fields.aggregatetimeestimate else 0
                          for issue in issues)
    return {
        "original estimate": WorkdaysFromSeconds(total_planned),
        "time spent": WorkdaysFromSeconds(total_spent),
        "time remaining": WorkdaysFromSeconds(total_remaining),
    }

def sum_assigned_hours_by_user_for_jql(jira, query, verbose=False, assignee_field=None):
    assignee_field = assignee_field or 'Assignee'
    if verbose:
        print('Using assignee field:', assignee_field)
    nameMap = get_field_map(jira)
    issues = jira.search_issues(query, maxResults=1000)
    user_to_hours = {} # {name: hours}
    for issue in issues:
        assignee = getattr(issue.fields, nameMap[assignee_field])
        #assignee_formal_name = None
        assignee_username = None
        if assignee:
            #assignee_formal_name = unicode(assignee)
            assignee_username = assignee.name
        total_planned = issue.fields.aggregatetimeoriginalestimate or 0
        user_to_hours.setdefault(assignee_username, 0)
        user_to_hours[assignee_username] += WorkdaysFromSeconds(total_planned).hours

    if None in user_to_hours and not user_to_hours[None]:
        del user_to_hours[None]

    return user_to_hours

def auto_assign_issues_for_jql(jira, query, verbose=True, assignee_field=None, assignable_users=None):
    """
    Automatically assigns issues that are unassigned, trying to balance the total work load among all users.
    """
    assignee_field = assignee_field or 'Assignee'
    if verbose:
        print('Using assignee field:', assignee_field)
    nameMap = get_field_map(jira)

    if assignable_users:
        assignable_users = (assignable_users or '').split(',')
    if not assignable_users:
        raise Exception('No users specified to assign to.')
    if verbose:
        print('assignable_users:', assignable_users)

    assignable_users_set = set(assignable_users)
    user_hours = sum_assigned_hours_by_user_for_jql(jira, query, verbose=verbose, assignee_field=assignee_field)
    user_hours.pop(None, None)
    for assignable_user in assignable_users:
        user_hours.setdefault(assignable_user, 0)
    for username in list(user_hours.keys()):
        if username not in assignable_users_set:
            del user_hours[username]
    if verbose:
        print('user hours:')
        pprint(user_hours, indent=4)

    query += ' AND "%s" IS EMPTY' % assignee_field
    issues = jira.search_issues(query, maxResults=1000)
    i = 0
    total = len(list(issues))
    for issue in issues:
        i += 1
        total_planned = WorkdaysFromSeconds(issue.fields.aggregatetimeoriginalestimate or 0).hours
        
        # Find user with the least amount of hours.
        winner = min((_hours, _username) for _username, _hours in user_hours.items())[-1]
        if verbose:
            print('Assigning issue %s to %s (%i of %i)...' % (issue, winner, i, total))
        user_hours[winner] += total_planned
        
        issue.update(fields={nameMap[assignee_field]: {'name': winner}})

def sum_worklogs_by_user_for_jql(jira, query, start_date=None, end_date=None, verbose=False):
    
    user_worklog_hours = {} # {username: hours}
    
    issues = jira.search_issues(query,
                                maxResults=1000,
                                fields="aggregatetimeestimate,aggregatetimespent,aggregatetimeoriginalestimate")
    total = len(list(issues))
    i = 0
    for issue in issues:
        i += 1
        if verbose:
            sys.stdout.write('\rProcessing issue %s (%i of %i %.2f%%)...' % (issue.key, i, total, float(i)/total*100))
            sys.stdout.flush()
        worklogs = jira.worklogs(issue.key)
        for worklog in worklogs:
            if verbose:
                print()
                print('worklog.id:', worklog)
                print('worklog.author:', worklog.author.name)
                print('worklog.created:', parse(worklog.created))

            worklog_started = parse(worklog.started).date()
            if verbose:
                print('worklog.started:', worklog_started)
            if worklog_started < start_date or worklog_started >= end_date:
                if verbose:
                    print('skipping out-of-range date')
                continue
            
            worklog_hours = worklog.timeSpentSeconds*(1/60.)*(1/60.)
            user_worklog_hours.setdefault(worklog.author.name, 0)
            user_worklog_hours[worklog.author.name] += worklog_hours

    if verbose:
        print
    return user_worklog_hours

def set_story_points_from_hours(jira, query, verbose=False):
    """
    Finds all issues with estimated hours and no story points, and sets story points to the total number of hours.
    """
    query += ' AND originalEstimate IS NOT EMPTY AND "Story Points" IS EMPTY'
    issues = jira.search_issues(query, maxResults=1000)
    nameMap = get_field_map(jira)
    total = len(list(issues))
    i = 0
    error_issues = set()
    for issue in issues:
        i += 1
        if verbose:
            sys.stdout.write('\rProcessing issue %s (%i of %i %.2f%%)...' % (issue.key, i, total, float(i)/total*100))
            sys.stdout.flush()
        #print issue
        original_estimate = getattr(issue.fields, nameMap['Original Estimate']) or 0 # in seconds
        #print('original_estimate:', original_estimate)
        estimated_hours = original_estimate*(1/60.)*(1/60.)
        #print 'estimated_hours:', estimated_hours
        story_points = getattr(issue.fields, nameMap['Story Points'])
        #print 'story_points:', story_points
        if story_points is None and estimated_hours:
            if verbose:
                print('Setting story points to %s...' % estimated_hours)
            try:
                issue.update(fields={nameMap['Story Points']: estimated_hours})
            except JIRAError as exc:
                print('Unable to update story points: %s' % exc)
                error_issues.add(issue.key)
    if error_issues:
        print('\nUpdates could not be made on the following issues: %s' % (', '.join(sorted(error_issues)),), file=sys.stderr)
