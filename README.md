# QtoINS

This repository is the code for the QtoINS project.


It includes:

- a React frontend in `data_prompt`
- a Flask backend in `server4`

## What It Does

1. Upload a CSV file
2. Ask a question about the data in plain English
3. Review ambiguity suggestions if the system asks for clarification
4. Generate charts and insights
5. Optionally refine the chart or insight

## Project Structure

```text
qtoINS/
├── README.md
├── data_prompt/   # frontend
└── server4/       # backend
```

## How to Run

### 1. Start the backend

```bash
cd server4
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install flask pandas numpy duckdb sqlglot sql-metadata sqlparse scipy python-dateutil editdistance altair vl-convert-python regex torch sentence-transformers openai
python app.py
```

The backend runs at `http://127.0.0.1:5000`.

### 2. Start the frontend

Open a new terminal:

```bash
cd data_prompt
npm install
npm start
```

The frontend runs at `http://localhost:3000`.

## How to Use

1. Open the frontend in your browser.
2. Click **Upload** and choose a CSV file.
3. Wait for the file summary to appear in the chat area.
4. Type a question about your data, for example:

```text
Show sales by region
Compare revenue by year
Compare the rating for comedy movies in recent years?
```

5. If the system finds ambiguous terms, choose the recommended options.
6. Click **Run Next Two Steps** to generate the chart and insights.
7. Use the chart or insight editing actions if you want to refine the result.


- `POST /api/changeinsight`

## Notes

- Upload CSV files only.
- The frontend is configured to send requests to the local Flask server.
- The backend entry file is `server4/app.py`.
