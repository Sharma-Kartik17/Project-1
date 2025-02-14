from flask import Flask, request, render_template_string
import os
import PyPDF2
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup

app = Flask(__name__)

# Create necessary directories
if not os.path.exists('uploads'):
    os.makedirs('uploads')

# Load job listings from CSV
def load_job_listings():
    """Load job listings from a CSV file."""
    df = pd.read_csv('./job_listings.csv')  # Adjust the path to your CSV file
    return df

# Internship scraping from Internshala
def fetch_internships(query):
    """Fetch internships based on skills from Internshala."""
    url = f"https://internshala.com/internships/keywords-{query.replace(' ', '-')}"
    
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        internships = []
        listings = soup.find_all('div', class_='internship_meta')

        for listing in listings[:10]:  # Limit to top 10 internships
            try:
                title = listing.find('h3').get_text(strip=True)
                company_tag = listing.find('a', class_='link_display_like_text')
                company = company_tag.get_text(strip=True) if company_tag else "N/A"
                link = "https://internshala.com" + listing.find('a')['href']
                internships.append({'title': title, 'company': company, 'link': link})
            except AttributeError:
                continue  # Skip any listings with missing data

        return internships

    except Exception:
        return []

# LinkedIn job scraping
def fetch_linkedin_jobs(query):
    """Fetch jobs based on skills from LinkedIn."""
    url = f"https://www.linkedin.com/jobs/search/?keywords={query.replace(' ', '%20')}"
    
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.content, 'html.parser')
        jobs = []
        listings = soup.find_all('div', class_='result-card')

        for listing in listings[:10]:  # Limit to top 10 jobs
            try:
                title = listing.find('h3', class_='result-card__title').get_text(strip=True)
                company = listing.find('h4', class_='result-card__subtitle').get_text(strip=True)
                link = listing.find('a', class_='result-card__full-card-link')['href']
                jobs.append({'title': title, 'company': company, 'link': link})
            except AttributeError:
                continue  # Skip incomplete listings

        return jobs

    except Exception:
        return []

# Extract skills from resume
def parse_resume(file):
    """Extract skills from the uploaded resume."""
    skills = set()
    with open(file, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text = page.extract_text()
            skills.update(re.findall(r'\b(?:Python|Java|HTML|CSS|JavaScript|Machine Learning)\b', text, re.IGNORECASE))
    return skills

# Get job suggestions
def get_job_suggestions(skills):
    """Get job suggestions based on skills."""
    job_listings = load_job_listings()
    suggestions = []
    
    for _, row in job_listings.iterrows():
        required_skills = row['Required_Skills'].split(', ')
        if any(skill.strip() in required_skills for skill in skills):
            suggestions.append(row['Job_Title'])

    return suggestions[:10]
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
        <h1 class="text-4xl font-bold text-center text-gray-800 mb-8">Find Internships Based on Your Resume</h1>
        <form action="/" method="POST" enctype="multipart/form-data" class="space-y-6">
            <div>
                <label for="resume" class="block text-lg font-semibold text-gray-700">Upload Your Resume (PDF)</label>
                <input type="file" name="resume" class="w-full mt-2 p-3 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-400" required>
            </div>
            <button type="submit" class="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-bold py-3 rounded-lg shadow-lg transition duration-300 transform hover:scale-105">Find Internships</button>
        </form>

        {% if internships or linkedin_jobs or job_suggestions %}
        <div class="grid grid-cols-1 md:grid-cols-2 gap-10 mt-10">
            <div>
                <h2 class="text-2xl font-semibold text-gray-800 text-center mb-4">Top Internship Opportunities</h2>
                <ul class="space-y-4">
                    {% for internship in internships %}
                    <li class="bg-blue-500 text-white p-4 rounded-lg shadow-lg transition duration-300 transform hover:scale-105">
                        <div>
                            <strong class="text-lg">{{ internship.title }}</strong>
                            {% if internship.company != "N/A" %}
                                <span class="block text-sm">at {{ internship.company }}</span>
                            {% endif %}
                        </div>
                        <a href="{{ internship.link }}" target="_blank" class="text-blue-200 underline mt-2 block">View Details</a>
                    </li>
                    {% endfor %}
                </ul>
            </div>
            <div>
                <h2 class="text-2xl font-semibold text-gray-800 text-center mb-4">LinkedIn Job Suggestions</h2>
                <ul class="space-y-4">
                    {% for job in linkedin_jobs %}
                    <li class="bg-green-500 text-white p-4 rounded-lg shadow-lg transition duration-300 transform hover:scale-105">
                        <strong class="text-lg">{{ job }}</strong>
                    </li>
                    {% endfor %}
                </ul>
            </div>
        </div>
        <a href="/" class="mt-8 block text-center bg-gray-400 hover:bg-gray-500 text-white font-bold py-2 rounded-lg transition duration-300">Try Again</a>
        {% endif %}
    </div>
</body>
</html>'''

@app.route('/', methods=['GET', 'POST'])
def index():
    internships, linkedin_jobs, job_suggestions = None, None, []

    if request.method == 'POST':
        resume_file = request.files['resume']
        resume_path = os.path.join('uploads', resume_file.filename)
        resume_file.save(resume_path)

        resume_skills = parse_resume(resume_path)
        skill_query = ' '.join(resume_skills)

        internships = fetch_internships(skill_query)
        linkedin_jobs = fetch_linkedin_jobs(skill_query)
        job_suggestions = get_job_suggestions(resume_skills)

        os.remove(resume_path)

    return render_template_string(HTML_TEMPLATE, internships=internships, linkedin_jobs=linkedin_jobs, job_suggestions=job_suggestions)

if __name__ == '__main__':
    app.run(debug=True)#
