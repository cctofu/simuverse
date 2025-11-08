# 🌌 Simuverse
AI-Powered Simulation for Pre-Market Product Validation

## ⚙️ Setup
### 📋 Requirements
- **Python** ≥ 3.10  
- **Node.js** ≥ 18.0  
- **npm** ≥ 9.0  

### 🔑 Setting up API keys:
Create a `.env` file in the base directory `./`. Add your openai api key to the file in the format:
```python
OPENAI_API_KEY="<your_api_key_here>"
```
This is required to be able to run the `./backend/` stage and and `./preprocess/` stage.

### 📦 Installing dependencies:
This project uses a `requirements.txt` file to list all the Python packages needed to run the code.
There are two common ways to install these dependencies — using **pip** or creating a **Conda environment**.
🧠 **Option 1: Install directly with pip**
If you’re using a simple Python setup (no Conda), follow these steps:
1. Make sure you have Python installed.
   Check with:
   ```bash
   python --version
   ```
2. Install all required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
This command install all the dependencies needed from the `requirements.txt` file.
🧪 **Option 2: Create a Conda environment using `requirements.txt`**
If you use **Anaconda** or **Miniconda**, you can create an isolated environment that includes all the dependencies in `requirements.txt`.
**Step 1 — Create a new environment:**
```bash
conda create -n myenv python=3.10
```
Replace `myenv` with the name you want for your environment (e.g., `project_env`).
**Step 2 — Activate the environment:**
```bash
conda activate myenv
```
**Step 3 — Install dependencies from `requirements.txt`:**
```bash
pip install -r requirements.txt
```
✅ **Verify Installation**
To confirm everything installed correctly, run:
```bash
pip list
```
You should see all the dependencies listed from your `requirements.txt` file.

### 🔄 Preprocess
The Preprocess stage downloads the dataset [`LLM-Digital-Twin/Twin-2K-500`](https://huggingface.co/datasets/LLM-Digital-Twin/Twin-2K-500) from huggingface and processes the data by adding dimensionality that will later be used within the backend for retrieval.

To run the preprocess stage, run the command:
```bash
bash ./run_preprocess.sh
```
This will run all three files involved in the preprocessing stage

### 🎨 Frontend
To host the frontend locally, run the command:
```bash
bash ./run_frontend.sh
```

### 🚀 Backend
To host the backend api locally, run the command:
```bash
bash ./run_backend.sh
```

### 📄 License
This project is proprietary and all rights are reserved.  
No permission is granted to copy, modify, or distribute this code without explicit authorization from the author.

### 📊 Dataset Reference
This project uses the open dataset [LLM-Digital-Twin/Twin-2K-500](https://huggingface.co/datasets/LLM-Digital-Twin/Twin-2K-500) hosted on Hugging Face for persona generation and simulation.
All rights and attributions for the dataset belong to the original authors.


