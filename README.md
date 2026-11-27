# Airtel Telecom Analytics

A data analysis project, Semester 3 OJT: Airtel subscriber data.

## The question
We are losing nearly one subscriber in four. Which of the things
we could do about it actually works?

## Data
airtel.db, 112.85 MiB, received <date>. Not in this repository.
Six tables. Row counts: filled in at 0.2 G.
## Setup
Written in Step 8.

## Streamlit deployment

Use `dashboard/app.py` as the Streamlit entry point. The repository includes
the source CSV files needed by the dashboard; on first start, the app builds
the local SQLite database automatically. Install dependencies with:

```bash
pip install -r requirements.txt
streamlit run dashboard/app.py
```

## Progress
- Step 0: environment, repository and data receipt