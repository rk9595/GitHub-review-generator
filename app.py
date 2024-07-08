# Description: This is the main file for the Flask application. It will be used to run the Flask application.
from dotenv import load_dotenv
import requests
from flask import Flask, request, render_template, send_file, Response
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os
import csv
import io


load_dotenv()

app = Flask(__name__)

GITHUB_ACCESS_TOKEN = os.getenv('GITHUB_TOKEN')

def create_session(token):
    """Create a new HTTP session with the provided token."""
    session = requests.Session()
    session.headers.update({'Authorization': f'token {token}'})
    return session

def fetch_all_pages(url, session):
    """Fetch all pages of data from a paginated API."""
    all_data = []
    while url:
        response=session.get(url)
        if response.status_code ==200:
            all_data.extend(response.json())
            if 'next' in response.links:
                url = response.links['next']['url']
            else:
                break
        else:
            print(f"Failed to fetch data :{response.status_code}")
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
    return [pr for pr in pull_requests if pr['merged_at']and datetime.strptime(pr['merged_at'], '%Y-%m-%dT%H:%M:%SZ') >= start_date]

def generate_intervels(duration_months=6):
    """Generate interval from 'duration_months' ago to today."""
    end_date = datetime.now()
    start_date = end_date - relativedelta(months=duration_months)
    return [(start_date, end_date)]

def generate_report(username, session, repositories, duration_months=6, specific_repo=None):
    """Generate a report for the specified repositories and duration."""
    intervals = generate_intervels(duration_months)
    all_pull_requests = []

    start_date, end_date = intervals[0]
    interval_description = f"#Interval: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n"

    for repo in repositories:
        repo_name = repo['name']
        if specific_repo and repo_name != specific_repo:
            continue
        pull_requests = get_pull_requests_for_repo(username, repo_name, session, start_date)

        for pr in pull_requests:
            pr_merged_at = datetime.strptime(pr['merged_at'], '%Y-%m-%dT%H:%M:%SZ')
            if start_date <= pr_merged_at <= end_date:
                all_pull_requests.append({
                    'Repository': repo_name,
                    'Pull Request': pr['title'],
                    'Date Merged at': pr['merged_at'],
                    'Description': pr.get('body', 'No description provided')
                })

    csv_data = io.BytesIO()
    text_wrapper = io.TextIOWrapper(csv_data, encoding='utf-8', newline='', write_through=True)
    csv_writer = csv.writer(text_wrapper)
    csv_writer.writerow([interval_description])
    headers = ['Repository', 'Pull Request', 'Date Merged at', 'Description']
    csv_writer.writerow(headers)

    for pr in all_pull_requests:
        csv_writer.writerow([pr['Repository'], pr['Pull Request'], pr['Date Merged at'], pr['Description']])

    text_wrapper.flush()  # Ensure all data is written to the underlying BytesIO object
    csv_data.seek(0)
    return csv_data.getvalue()
        

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generatecsv', methods=['POST'])
def generate_csv():
    username = request.form['username']
    duration_months = int(request.form['duration_months'])
    specific_repo = request.form.get('repo')
    
    session = create_session(GITHUB_ACCESS_TOKEN)
    repositories = get_repositories(username, session)
    csv_content = generate_report(username, session, repositories, duration_months, specific_repo)
    
    filename = f'{username}_github_contributions_report.csv'
    if specific_repo:
        filename = f'{username}_{specific_repo}_github_contributions_report.csv'
    
    # Create a Flask Response object that can send the correct CSV content
    response = Response(csv_content, mimetype='text/csv')
    response.headers.set('Content-Disposition', 'attachment', filename=filename)
    return response


if __name__ == '__main__':
    app.run(debug=True)