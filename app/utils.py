# Description: This file contains utility functions for fetching data from the GitHub API.
import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time

def create_session(token):
    """Create a new HTTP session with the provided token."""
    session = requests.Session()
    session.headers.update({'Authorization': f'token {token}'})
    return session

def fetch_all_pages(url, session):
    """Fetch all pages of data from a paginated API."""
    all_data = []
    while url:
        response = session.get(url)
        if response.status_code == 200:
            all_data.extend(response.json())
            if 'next' in response.links:
                url = response.links['next']['url']
            else:
                break
        elif response.status_code == 403:
            print("API rate limit exceeded. Please wait for a minute and try again.")
            time.sleep(60)
            continue
        elif response.status_code == 404:
            print("Failed to fetch data:User not found.")
            break
        else:
            print(f"Failed to fetch data: {response.status_code}")
            break
    return all_data

def get_repositories(username, session):
    """Fetch all repositories for a given user."""
    url = f'https://api.github.com/users/{username}/repos?type=all&sort=updated&direction=desc&per_page=100'
    return fetch_all_pages(url, session)

def get_pull_requests_for_repo(username, repo_name, session, start_date):
    """Fetch all closed pull requests for a given repository."""
    url = f'https://api.github.com/repos/{username}/{repo_name}/pulls?state=closed&sort=updated&direction=desc&per_page=100'
    pull_requests = fetch_all_pages(url, session)
    return [pr for pr in pull_requests if pr['merged_at'] and datetime.strptime(pr['merged_at'], '%Y-%m-%dT%H:%M:%SZ') >= start_date]

def generate_intervals(duration_months=6):
    """Generate interval from 'duration_months' ago to today."""
    end_date = datetime.now()
    start_date = end_date - relativedelta(months=duration_months)
    return [(start_date, end_date)]