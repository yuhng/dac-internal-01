import type { ScoreInput } from '../api/types'

/** Sample jobs with CVs. Only the job is loaded into the form: scoring needs a CV uploaded as a PDF. */
export const SAMPLES: ScoreInput[] = [
  {
    title: 'Data Analyst',
    company: 'Northwind Retail',
    jd: `We are looking for a Data Analyst to join our Commercial Insights team at Northwind Retail. You will turn sales and customer data into actionable insights for merchandising and marketing stakeholders.

Responsibilities:
- Build and maintain dashboards in Tableau or Power BI
- Write efficient SQL queries to extract and transform data from our data warehouse
- Run A/B testing and statistical analysis to evaluate campaigns
- Automate recurring reports using Python (pandas)
- Present findings clearly to non-technical stakeholders

Requirements:
- 2+ years of experience in data analysis
- Strong SQL and Excel skills
- Experience with Python, pandas and data visualization
- Knowledge of statistics and A/B testing
- Familiarity with ETL pipelines and cloud data warehouses (BigQuery or Snowflake) is a plus
- Excellent communication and stakeholder management skills`,
    cv: `ALEX TAN
alex.tan@email.com | Singapore | linkedin.com/in/alextan

SUMMARY
Analytical graduate with 2 years experiance turning business data into insights. i enjoy  working with stakeholders to solve problems.

EXPERIENCE
Business Analyst, Harbourline Logistics (2023 – Present)
- responsible for creating weekly sales reports in Excel for the regional managment team
- Worked on a Power BI dashboard tracking delivery performance across 40 routes
- Wrote SQL queries to pull shipment data, reducing report preparation time by 30%
- helped with the migration of reports to a cloud data warehouse

Data Intern, Brightside Marketing (2022 – 2023)
- Was involved in analysing campaign results for 12 clients
- Built Python scripts using pandas to clean survey data
- Presented findings to account managers every month

EDUCATION
B.Sc. Business Analytics, National University of Singapore, 2022

SKILLS
Excel, SQL, Power BI, Python, pandas, Communication`,
  },
  {
    title: 'Data Scientist',
    company: 'Tidewater Insurance',
    jd: `Tidewater Insurance is looking for a Data Scientist to join our Pricing and Claims Analytics team. You will build machine learning models that help us price policies fairly and spot fraudulent claims earlier.

Responsibilities:
- Develop, validate and monitor predictive models for claims fraud and customer churn
- Write Python and SQL to explore large claims and policy datasets
- Design experiments and use statistical analysis to measure model impact
- Track experiments and deploy models with MLflow on Databricks
- Explain model results and limitations to underwriters and product managers

Requirements:
- 3+ years of experience building machine learning models in production
- Strong Python skills, including pandas and scikit-learn
- Solid grounding in statistics, hypothesis testing and model evaluation
- Experience with SQL and large datasets; PySpark is a strong plus
- Familiarity with cloud platforms (AWS or Azure) and Docker
- Experience with NLP or insurance data is a bonus`,
    cv: `PRIYA NAIR
priya.nair@email.com | Singapore | github.com/priyanair

SUMMARY
Data scientist with 3 years experiance building predictive models for retail banking. i enjoy turning messy data into models people trust.

EXPERIENCE
Data Scientist, Orchard Bank (2022 – Present)
- responsible for building a credit default model in Python with scikit-learn, improving recall by 18%
- Worked on a customer churn model now used by the retention team for 1.2 million customers
- Wrote SQL and PySpark jobs to prepare features from transaction data
- helped with deploying models as Docker containers on AWS

Analytics Intern, Lattice Research (2021 – 2022)
- Was involved in survey analysis for 8 clients using pandas
- Ran hypothesis tests and presented results to the research leads

EDUCATION
M.Sc. Statistics, National University of Singapore, 2021

SKILLS
Python, pandas, scikit-learn, SQL, PySpark, Docker, AWS, Statistics`,
  },
  {
    title: 'Data Engineer',
    company: 'Kestrel Mobility',
    jd: `Kestrel Mobility runs ride-hailing and delivery services across Southeast Asia. We are hiring a Data Engineer to build the pipelines that power our pricing, dispatch and finance reporting.

What you'll do:
- Design and build reliable batch and streaming data pipelines
- Orchestrate workflows with Airflow and model data with dbt
- Process large datasets with PySpark on Databricks and Delta Lake
- Manage cloud infrastructure on AWS with Terraform
- Set up CI/CD with GitHub Actions and monitor data quality

What we're looking for:
- 3+ years of experience as a data engineer
- Strong Python and SQL skills
- Hands-on experience with Airflow, dbt and PySpark
- Experience with PostgreSQL and a cloud data warehouse such as BigQuery
- Familiarity with Docker and infrastructure as code (Terraform)
- Experience with Kafka or other streaming tools is a plus`,
    cv: `DANIEL WONG
daniel.wong@email.com | Kuala Lumpur | github.com/danielwong

PROFILE
Data engineer with 4 years experiance building data platforms for e-commerce and fintech.

EXPERIENCE
Data Engineer, Paylane (2022 – Present)
- responsible for building Airflow pipelines that load 50 million payment events a day
- Worked on moving reporting tables from PostgreSQL to BigQuery, cutting query costs by 35%
- Built dbt models for finance reporting used by 6 teams
- helped with setting up GitHub Actions to test pipelines before deployment

Junior Data Engineer, Cartly (2020 – 2022)
- Was involved in writing Python ETL jobs for product and order data
- Containerised batch jobs with Docker and scheduled them on AWS

EDUCATION
B.Eng. Software Engineering, Universiti Teknologi Malaysia, 2020

SKILLS
Python, SQL, Airflow, dbt, PostgreSQL, BigQuery, Docker, AWS, GitHub Actions`,
  },
]
