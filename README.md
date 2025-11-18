# 📧 AI Email Classifier → Google Sheets

This project automatically reads your Gmail inbox, classifies each email
using a Groq LLM, generates a summary, then writes the results into a
Google Sheet.\
Each category is written into its own sheet tab, created automatically
if missing.

------------------------------------------------------------------------

## 🚀 Features

-   Fetch emails from Gmail API\
-   Classify emails using **Groq LLM**\
-   Generate structured JSON: **category, urgency, summary**\
-   Auto‑create Google Sheet + tabs\
-   Write each ticket into its correct sheet\
-   Fully customizable prompt and system context\
-   Local `.env` configuration\
-   Supports batch writing and rate‑limit protection

------------------------------------------------------------------------

## 📂 Project Structure

    /agents
      ├── context.txt
      ├── prompt.txt
      ├── sheet-writer.json   (Google service account)
      ├── credentials.json    (OAuth Gmail)
    read_classify_write_groq.py
    README.md
    .env
    token.json

------------------------------------------------------------------------

## 🔑 Requirements

-   Python 3.10+
-   Groq API Key\
-   Google Cloud service account (Sheets + Drive enabled)\
-   Gmail OAuth credentials (`credentials.json`)

------------------------------------------------------------------------

## ⚙️ Installation

``` bash
git clone <your-repo-url>
cd your-project
pip install -r requirements.txt
```

Create a `.env` file:

    GROQ_API_KEY=your_key_here

------------------------------------------------------------------------

## ▶️ Run the script

``` bash
python read_classify_write_groq.py
```

The script will: 1. Connect to Gmail\
2. Fetch your emails\
3. Classify + summarize them using Groq\
4. Write results into your Google Sheet

------------------------------------------------------------------------

## 🧠 Customizing Classification

Edit the 2 prompt files:

-   `agents/context.txt` → System prompt\
-   `agents/prompt.txt` → User instruction

------------------------------------------------------------------------

## 🤝 Contributing

Pull requests welcome!

------------------------------------------------------------------------

## 📜 License

MIT License
