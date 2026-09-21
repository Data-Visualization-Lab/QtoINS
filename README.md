This repository contains the supplementary materials and code for the QtoINS project.

## System Evaluation

All files related to Section 6 System Evaluation are stored in the `systemevaluate` folder:

- **evaluate1**: Contains CSV files of experimental dataset and results (evaluate1_result.csv) for "Human Query to Target Data" component.
- **evaluate2**: Contains CSV files of results for the "Human Query and Target Data to Charts" component. `evaluation2_result.csv` includes results based on the NLV dataset (https://nlvcorpus.github.io.) as well as Task 1 from our comparative usability study. `result.csv` contains the ablation test results.
- **evaluate3**: Contains CSV files of results (ratings_summary.csv) for "Charts to Insights" component. The chartID in ratings_summary.csv corresponds to the charts located in the `charts` folder under the same directory, and index.html together with server.py contains the code we used to conduct Prolific online study.

## Fine-tuning Dataset

- **Fine-tuning_Dataset**: Specifically used for the "Human Query and Target Data to Charts" component and includes the file `keys.csv`. `keys.csv` contains five columns: (1) key (original key from VisEval), (2) database name, (3) our merged runnable SQL statements based on VisEval's fragments of SQL, (4) our generated runnable Vega-Lite JSON file, (5) our labeled natural language queries.

We did not include VisEval's (DOI: 10.1109/TVCG.2024.3456320) original database data, as the target data was directly retrieved using SQL queries.

---

## Setup Guide
All code is included in the `Code` Folder and  `server` Folder.

### Environment Setup

#### Replace API Keys

1. Navigate to the `function` directory and `app.py` fileand replace the existing **OpenAI API key** with your personal key.

> **Important Note:** Our function for converting human queries and target data into charts leverage OpenAI's GPT-4o fine-tuned model. Thus, using our provided fine-tuned model yields better results than the standard GPT-4o model. However, if necessary, you may update the model reference to standard GPT-4o in `visualrecommendation.py`.

---

### Starting the Backend Service

1. Open your terminal and navigate to the backend server directory:
  
   cd server
  

2. Verify your Python environment is version **3.12.4**.

3. Install required Python packages:
  
   pip install -r requirements.txt
 

4. Ensure Flask framework is installed (update if already present):
  
   pip install -U Flask


5. Launch the Flask backend service:
  
   python app.py


---

### Starting the Frontend Service

1. In your terminal, navigate to the frontend directory:
   
   cd data_prompt


2. Install necessary frontend dependencies:
  
   npm install


3. Run the frontend application:

   npm start


4. Access the application via your web browser at:

   http://127.0.0.1:3000
