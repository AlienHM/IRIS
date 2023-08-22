from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os
import pandas as pd
import openai
import json
import csv
import PyPDF2

openai.organization = "org-ZY4FHfi1GWcbT3ZNFZ84BVDw"
openai.api_key = "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"

def extract_text_from_pdf(file):  # sourcery skip: use-join
    reader = PyPDF2.PdfReader(file)
    text = ''
    for page in reader.pages:
        text += page.extract_text()
    return text


app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'db/cv_database.db')

# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db/user_base.db' # or your own path
db = SQLAlchemy(app)

class Cv(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    job_title = db.Column(db.String(200))
    # store the results JSON as a string
    result = db.Column(db.Text)

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        f = request.files['file']
        extracted_text = extract_text_from_pdf(f)
        job_desc = request.form['jobdesc']

        extract_data_query = """Get data from given CV and return json format with these columns:[Şəxsi məlumat(Personal Information), Ad, Əlaqə Məlumatları, Profil(Profile), İş Təcrübəsi(Job Experience),Təhsil(Education), Bacarıqlar(Skills), Sertifikatlar(Certifications)], if there is no information about column, put 0 
CV:"""+ extracted_text
        
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k-0613",
            messages=[{"role":"user", "content":extract_data_query}]
        )

        json_cv_data = completion["choices"][0]["message"]['content']

        json_cv_data = json_cv_data.replace('\n', '')

        compare_query = """Assume the role of a professional recruiter and evaluate the provided öhdəliklər(job responsibilities) and tələblər(requirements) against the candidate's CV that is also provided. Compare CV and Job responsibilities and requirements that is this person suits this job or do not suit completely, or maybe suits partly. To evaluate use this evaluation system: Very Low, Low, Moderate, High, Very High. Provide feedback and elaborate on the reasons for the assigned value, explaining why you believe the candidate merits such a value with just one line. After all, return result as this json format: {"name": "John Doe", title: "Data Scientist", responsibilities_value": n, "requirements_value": m, "explanation": explanation_text}' 
        This is job vacancy:""" + job_desc + """
        And this is candidate informations:""" + json_cv_data

        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k-0613",
            messages=[{"role":"user", "content":compare_query}]
        )

        result = completion["choices"][0]["message"]['content']

        result_json = json.loads(result)
        cv = Cv(name=result_json['name'], job_title=result_json['title'], result=result)
        db.session.add(cv)
        db.session.commit()
        return redirect(url_for('results', cv_id=cv.id))
    cVs = Cv.query.all()
    return render_template('index.html', cvs=cVs)

@app.route('/results/<int:cv_id>')
def results(cv_id):
    cv = Cv.query.get(cv_id)
    if not cv:
        return "CV not found", 404
    result_json = json.loads(cv.result)
    return render_template('result.html', filename=cv.name, responsibilities_value=result_json['responsibilities_value'], requirements_value=result_json['requirements_value'], explanation=result_json['explanation'], title=result_json['title'])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

