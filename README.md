# QtoINS

QtoINS is a data exploration project that lets users interact with CSV files through natural language.

This repository includes:

- a React frontend in `data_prompt`
- a Flask backend in `server4`

## Overview

With QtoINS, you can:

1. Upload a CSV file.
2. Ask questions about the data in plain English.
3. Review ambiguity suggestions when the system needs clarification.
4. Generate charts and insights.
5. Refine the chart or insight if needed.

## Project Structure

```text
QtoINS/
├── README.md
├── data_prompt/   # frontend
└── server4/       # backend
```

## Getting Started

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

Open a new terminal and run:

```bash
cd data_prompt
npm install
npm start
```

The frontend runs at `http://localhost:3000`.

## Usage

1. Open the frontend in your browser.
2. Click **Upload** and select a CSV file.
3. Wait for the file summary to appear in the chat area.
4. Enter a question about your data, for example:

```text
Show sales by region
Compare revenue by year
Compare the rating for comedy movies in recent years?
```

5. If the system detects ambiguous terms, choose the recommended options.
6. Click **Run Next Two Steps** to generate charts and insights.
7. Use the chart or insight editing actions to refine the result if needed.


