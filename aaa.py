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
            <button type="submit" class="w-full bg-blue-600 text-white py-3 rounded-lg shadow-lg hover:bg-blue-700 transition duration-300">Submit</button>
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
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head>
<body class="bg-gradient-to-r from-blue-500 to-purple-600 min-h-screen flex items-center justify-center p-4">
    <div class="container mx-auto bg-white p-8 md:p-16 shadow-2xl rounded-lg max-w-3xl">
        <h1 class="text-4xl font-bold text-center text-gray-800 mb-8">Enter Your Details</h1>
        <form action="/jobs" method="POST" class="space-y-6">
            <div>
                <label class="block text-lg font-semibold text-gray-700">Name:</label>
                <input type="text" name="name" required class="w-full mt-2 p-3 border border-gray-300 rounded-lg">
            </div>
            <div>
                <label class="block text-lg font-semibold text-gray-700">Email:</label>
                <input type="email" name="email" required class="w-full mt-2 p-3 border border-gray-300 rounded-lg">
            </div>
            <div>
                <label class="block text-lg font-semibold text-gray-700">Phone:</label>
                <input type="text" name="phone" required class="w-full mt-2 p-3 border border-gray-300 rounded-lg">
            </div>
            <button type="submit" class="w-full bg-blue-600 text-white py-3 rounded-lg shadow-lg hover:bg-blue-700 transition duration-300">Save and Continue</button>
        </form>
    </div>
</body>
</html>'''

JOBS_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Job Opportunities</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head>
<body class="bg-gradient-to-r from-blue-500 to-purple-600 min-h-screen p-4">
    <div class="container mx-auto bg-white p-8 md:p-16 shadow-2xl rounded-lg max-w-6xl">
        <h1 class="text-4xl font-bold text-center text-gray-800 mb-8">Job and Internship Opportunities</h1>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div>
                <h2 class="text-2xl font-semibold text-gray-700 mb-4">Job Suggestions</h2>
                <ul class="space-y-4">
                    {% for job in job_suggestions %}
                        <li class="bg-gray-100 p-4 rounded-lg shadow-md">
                            <span class="text-lg font-medium text-gray-700">{{ job }}</span>
                            <button onclick="fillApplication('{{ job }}')" class="ml-4 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition duration-300">Apply</button>
                        </li>
                    {% endfor %}
                </ul>
            </div>
            <div>
                <h2 class="text-2xl font-semibold text-gray-700 mb-4">Internships</h2>
                <ul class="space-y-4">
                    {% for internship in internships %}
                        <li class="bg-gray-100 p-4 rounded-lg shadow-md">
                            <span class="text-lg font-medium text-gray-700">{{ internship.title }} at {{ internship.company }}</span>
                            <a href="{{ internship.link }}" target="_blank" class="ml-4 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition duration-300">View</a>
                            <button onclick="fillApplication('{{ internship.title }}')" class="ml-4 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition duration-300">Apply</button>
                        </li>
                    {% endfor %}
                </ul>
            </div>
        </div>
        <form id="applyForm" action="/apply" method="POST" class="hidden">
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
    </div>
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

if __name__ == '__main__':
    app.run(debug=True)