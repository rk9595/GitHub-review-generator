# Description: This is the main file for the Flask application. It will be used to run the Flask application.
from dotenv import load_dotenv
import requests
from flask import Flask, request, render_template, send_file, Response
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os
import csv
import io
from app.schemas import ContributionsSchema
from app.utils import create_session, get_repositories, get_pull_requests_for_repo, generate_intervals


load_dotenv()

app = Flask(__name__)

GITHUB_ACCESS_TOKEN = os.getenv('GITHUB_TOKEN')



def generate_report(username, session, repositories, duration_months=6, specific_repo=None):
    """Generate a report for the specified repositories and duration."""
    intervals = generate_intervals(duration_months)
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

@app.route('/api/repositories/<username>')
def get_user_repositories(username):
    session = create_session(GITHUB_ACCESS_TOKEN)
    repositories = get_repositories(username, session)
    return {'repositories': repositories}

@app.route('/api/contributions', methods=['POST'])
def generate_csv():
    schema = ContributionsSchema()
    errors = schema.validate(request.form)
    if errors:
        return {'errors': errors}, 400
    
    username = request.form['username']
    duration_months = int(request.form['duration_months'])
    specific_repo = request.form.get('repo')
    
    
    try:
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

    except Exception as e:
        return {'error': str(e)}, 500


if __name__ == '__main__':
    app.run(debug=True)