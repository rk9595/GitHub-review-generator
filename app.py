# Description: This is the main file for the Flask application. It will be used to run the Flask application.
from dotenv import load_dotenv
import requests
from flask import Flask, request, render_template
import os

load_dotenv()

app = Flask(__name__)

GITHUB_ACCESS_TOKEN = os.getenv('GITHUB_TOKEN')


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_summary():
    username = request.form['username']
    url = f'https://api.github.com/users/{username}/repos'
    headers = {
        'Authorization': f'token {GITHUB_ACCESS_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    response = requests.get(url, headers=headers)
    print(response.json())
    
    if response.status_code == 200:
        pull_requests= response.json()
        return pull_requests
    else:
        return "Error fetching pull requets"

if __name__ == '__main__':
    app.run(debug=True)