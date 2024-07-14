# Description: This is the main file for the Flask application. It will be used to run the Flask application.
from dotenv import load_dotenv
import requests
from flask import Flask, json, jsonify, request, render_template, send_file, Response
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os
import csv
import io
import logging
import json
# from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import requests_cache
from app.schemas import ContributionsSchema
import openai
from app.swagger import spec, swaggerui_blueprint, SWAGGER_URL
from app.utils import create_session, generate_intervals, get_pull_requests_for_repo, get_repositories
import psycopg2
import redis


load_dotenv()

app = Flask(__name__)

app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)
# print(SWAGGER_URL)
logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)


GITHUB_ACCESS_TOKEN = os.getenv('GITHUB_TOKEN')
openai.api_key = os.getenv('OPENAI_API_KEY')

conn= psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)

curr=conn.cursor()
print("Connected to the database", curr)

try:
    curr.execute("SELECT 1")
    print("Successfully connected to the database")
except psycopg2.Error as e:
    print("Failed to connect to the database")
    print(e)
    
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST'),
    port=os.getenv('REDIS_PORT'),
    password=os.getenv('REDIS_PASSWORD')
)
model_path = "lama"
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForSeq2SeqLM.from_pretrained(model_path)
print("Model loaded successfully", model)

requests_cache.install_cache('github_cache', backend='redis', expire_after=1800, connection=redis_client)


def generate_report(username, session, repositories, duration_months=6, specific_repo=None):
    """Generate a report for the specified repositories and duration."""
    intervals = generate_intervals(duration_months)
    all_pull_requests = []

    start_date, end_date = intervals[0]
    interval_description = f"#Interval: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n"

    logging.info(f"Generating report for {username} with duration of {duration_months} months")
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
    
    logger.info(f"Generated report for {username} with duration of {duration_months} months")
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
        # print (repositories)
        csv_content = generate_report(username, session, repositories, duration_months, specific_repo)
        print (csv_content)
        filename = f'{username}_github_contributions_report.csv'
        if specific_repo:
            filename = f'{username}_{specific_repo}_github_contributions_report.csv'

        response = Response(csv_content, mimetype='text/csv')
        response.headers.set('Content-Disposition', 'attachment', filename=filename)
        return response

    except Exception as e:
        return jsonify({'error': str(e)}), 500



# Description: This endpoint generates a summary of the contributions for a given user using LLM.
# @app.route('/api/contribution-summary', methods=['POST'])
# def generate_contribution_summary():
#     schema = ContributionsSchema()
#     errors = schema.validate(request.form)
#     if errors:
#         return {'errors': errors}, 400

#     username = request.form['username']
#     duration_months = int(request.form['duration_months'])
#     specific_repo = request.form.get('repo')
#     intervals=generate_intervals(duration_months)
#     start_date, end_date = intervals[0]
#     interval_description = f"#Interval: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n"
#     try:
#         #check if the contribution data is in the cache
#         cached_data= redis_client.get(username)
#         if cached_data:
#             cached_data_json=json.loads(cached_data.decode('utf-8'))
#             summary= generate_summary(cached_data_json)
#             print ("cachedsummary",summary)
#             return jsonify({'summary': summary})
        
#         #Check if the contribution data is in the database
#         curr.execute("SELECT * FROM contributions WHERE username=%s", (username,))
#         result=curr.fetchone()
#         if result:
#             contribution_data=result[0]
#             #store the data in the cache
#             redis_client.set(username, json.dumps(contribution_data))
            
#         #If the data is not in the cache or database, fetch the data from the GitHub APIs
#         session = create_session(GITHUB_ACCESS_TOKEN)
#         repositories = get_repositories(username, session)
#         contribution_data={
#             'total_prs':0,           
#             'merged_prs':0,
#             'lines_added':0,
#             'lines_deleted':0,
#             'pr_details':[]
        
#         }
#         # print (contribution_data)
        
#         batch_size = 10

#         for repo in repositories:
#             repo_name = repo['name']
#             if specific_repo and repo_name != specific_repo:
#                 continue
#             pull_requests = get_pull_requests_for_repo(username, repo_name, session, start_date)
#             for i in range(0, len(pull_requests), batch_size):
#                 batch_size_pull_requests = pull_requests[i:i + batch_size]
#                 print("Batch size: ", len(batch_size_pull_requests))
                
#                 for pr in batch_size_pull_requests:
#                     # print (pr['additions'])
#                     pr_merged_at = datetime.strptime(pr['merged_at'], '%Y-%m-%dT%H:%M:%SZ')
#                     if start_date <= pr_merged_at <= end_date:
#                         contribution_data['merged_prs']+=1
#                         contribution_data['lines_added']+=pr.get('additions',0)
#                         # contribution_data['lines_deleted']+=pr['deletions',0]
#                         contribution_data['pr_details'].append({
#                             'title': pr['title'],
#                             'body': pr.get('body', 'No description provided'),
#                             # 'lines_added': pr['additions'],
#                             # 'lines_deleted': pr['deletions']
#                         })
#         #Store the contribution data in the database
#         curr.execute("INSERT INTO contributions (username, data) VALUES (%s, %s)", (username, json.dumps(contribution_data)))
#         conn.commit()
#         #Store the contribution data in the cache
#         redis_client.set(username, json.dumps(contribution_data))
#         # print (contribution_data)
#         # return jsonify(contribution_data)
#         summary= generate_summary(contribution_data)
#         print ("summary",summary)
#         # return "Summary generated successfully"
        
#         return jsonify({'summary': summary})

#     except Exception as e:
#         return jsonify({'error': str(e)}), 500
    
    


# def generate_summary(contribution_data):
#     prompt = f"Please summarize the following contributions for a software developer:\n\n"
#     prompt += f"PR Details: \n"
#     for pr in contribution_data['pr_details']:
#         prompt += f"Title: {pr['title']}\n"
#         prompt += f"Description: {pr['body']}\n"
#     prompt += "Summary:"

#     inputs = tokenizer(prompt, return_tensors="pt", max_length=1024, truncation=True)
#     summary_ids = model.generate(inputs["input_ids"], num_beams=4, max_length=100, early_stopping=True)
#     summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)

#     return summary
      

    
    
@app.route('/api/swagger.json')
def swagger_spec():
    return jsonify(spec.to_dict())

if __name__ == '__main__':
    app.run(debug=True)