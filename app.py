from flask import Flask, request, render_template_string, session
import os
import PyPDF2
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Create necessary directories
os.makedirs('uploads', exist_ok=True)
os.makedirs('applications', exist_ok=True)

# Load job listings from CSV
def load_job_listings():
    df = pd.read_csv('./job_listings.csv')  # Adjust the path to your CSV file
    return df

# Fetch internships
def fetch_internships(query):
    url = f"https://internshala.com/internships/keywords-{query.replace(' ', '-')}"
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        internships = []
        listings = soup.find_all('div', class_='internship_meta')
        for listing in listings[:10]:
            try:
                title = listing.find('h3').get_text(strip=True)
                company_tag = listing.find('a', class_='link_display_like_text')
                company = company_tag.get_text(strip=True) if company_tag else "N/A"
                link = "https://internshala.com" + listing.find('a')['href']
                internships.append({'title': title, 'company': company, 'link': link})
            except AttributeError:
                continue
        return internships
    except Exception as e:
        print(f"Error fetching internships: {e}")
        return []

# Extract skills from resume
def parse_resume(file):
    skills = set()
    with open(file, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text = page.extract_text()
            skills.update(re.findall(r'\b(?:Python|Java|HTML|CSS|JavaScript|Machine Learning)\b', text, re.IGNORECASE))
    return skills

# Get job suggestions
def get_job_suggestions(skills):
    job_listings = load_job_listings()
    suggestions = []
    for _, row in job_listings.iterrows():
        required_skills = row['Required_Skills'].split(', ')
        if any(skill.strip() in required_skills for skill in skills):
            suggestions.append(row['Job_Title'])
    return suggestions[:10]

# HTML Template
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Internship Finder</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head>
<body class="bg-gradient-to-r from-blue-500 to-purple-600 min-h-screen flex items-center justify-center p-4">
    <div class="container mx-auto bg-white p-8 md:p-16 shadow-2xl rounded-lg max-w-3xl">
        <h1 class="text-4xl font-bold text-center text-gray-800 mb-8">Upload Your Resume</h1>
        <form action="/details" method="POST" enctype="multipart/form-data" class="space-y-6">
            <div>
                <label class="block text-lg font-semibold text-gray-700">Upload Your Resume (PDF)</label>
                <input type="file" name="resume" required class="w-full mt-2 p-3 border border-gray-300 rounded-lg">
            </div>
            <button type="submit" class="w-full bg-blue-600 text-white py-3 rounded-lg shadow-lg">Submit</button>
        </form>
    </div>
</body>
</html>'''

DETAILS_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enter Details</title>
</head>
<body>
    <h2>Fill in Your Details</h2>
    <form action="/jobs" method="POST">
        <label>Name:</label><input type="text" name="name" required><br>
        <label>Email:</label><input type="email" name="email" required><br>
        <label>Phone:</label><input type="text" name="phone" required><br>
        <button type="submit">Save and Continue</button>
    </form>
</body>
</html>'''

JOBS_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Job Opportunities</title>
</head>
<body>
    <h2>Job and Internship Opportunities</h2>
    <ul>
        {% for job in job_suggestions %}
            <li>{{ job }} <button onclick="fillApplication('{{ job }}')">Apply</button></li>
        {% endfor %}
    </ul>
    <h2>Internships</h2>
    <ul>
        {% for internship in internships %}
            <li>{{ internship.title }} at {{ internship.company }} <a href="{{ internship.link }}" target="_blank">View</a>
            <button onclick="fillApplication('{{ internship.title }}')">Apply</button></li>
        {% endfor %}
    </ul>
    <form id="applyForm" action="/apply" method="POST">
        <input type="hidden" name="job_title" id="job_title">
        <input type="hidden" name="name" value="{{ user_details.name }}">
        <input type="hidden" name="email" value="{{ user_details.email }}">
        <input type="hidden" name="phone" value="{{ user_details.phone }}">
    </form>
    <script>
        function fillApplication(title) {
            document.getElementById('job_title').value = title;
            document.getElementById('applyForm').submit();
        }
    </script>
</body>
</html>'''

@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/details', methods=['POST'])
def details():
    resume_file = request.files['resume']
    resume_path = os.path.join('uploads', resume_file.filename)
    resume_file.save(resume_path)
    session['resume_skills'] = list(parse_resume(resume_path))
    os.remove(resume_path)
    return render_template_string(DETAILS_TEMPLATE)

@app.route('/jobs', methods=['POST'])
def jobs():
    session['user_details'] = request.form.to_dict()
    skills = session.get('resume_skills', [])
    return render_template_string(JOBS_TEMPLATE, 
                                  job_suggestions=get_job_suggestions(skills),
                                  internships=fetch_internships(' '.join(skills)),
                                  user_details=session['user_details'])

@app.route('/apply', methods=['POST'])
def apply():
    return f"Application submitted for {request.form['job_title']} by {request.form['name']}!"

if __name__ == '__main__':  # ✅ Corrected this line
    app.run(debug=True)
