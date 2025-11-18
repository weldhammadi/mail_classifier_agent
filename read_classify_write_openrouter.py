
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from collections import defaultdict
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer  # can swap with LexRank, Luhn, etc.
import base64
import re
import time
import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import requests
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Simple local read_file function
def read_file(path, encoding="utf-8"):
    with open(path, encoding=encoding) as f:
        return f.read()
load_dotenv()
# ---------------- LLM CONFIG ----------------
client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENAI_API_KEY"),
)

# ---------------- CONFIG ----------------
SHEET_NAME = None
SHEET_ID = "1KxmEfDlo5Wyzy5F8jd-pq8ARPWti1z2PEFdtlQbiUQU"

# Map category names to worksheet/tab IDs (replace the numbers with your actual worksheet IDs from Google Sheets)
CATEGORY_TAB_IDS = {
    "Problème technique informatique": 1,  # Replace 0 with the actual gid for this tab
    "Demande administrative": 2,  # Replace with actual gid
    "Problème d’accès / authentification": 3,  # Replace with actual gid
    "Demande de support utilisateur": 4,  # Replace with actual gid
    "Bug / Dysfonctionnement": 5  # Replace with actual gid
}

# Gmail API scopes
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Sheets API scopes
SHEETS_SCOPE = ["https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"]

SERVICE_ACCOUNT_FILE = 'agents\\sheet-writer.json'

# ---------------- GMAIL FUNCTIONS ----------------
def get_gmail_service():
    """Authenticate and return Gmail service"""
    creds = None
    # If you already have token.json from OAuth flow
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', GMAIL_SCOPES)
    # Otherwise do OAuth flow manually
    if not creds or not creds.valid:
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file('agents\\credentials.json', GMAIL_SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    service = build('gmail', 'v1', credentials=creds)
    return service

def list_message_ids(service, query='in:inbox'):
    """List all message IDs matching a query"""
    messages = []
    request = service.users().messages().list(userId='me', q=query, maxResults=500)
    while request:
        response = request.execute()
        messages.extend(response.get('messages', []))
        request = service.users().messages().list_next(request, response)
    return messages

def get_message(service, msg_id):
    """Fetch and parse Gmail message"""
    message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
    headers = message['payload'].get('headers', [])
    subject = next((h['value'] for h in headers if h['name']=='Subject'), '')
    body = get_body_from_payload(message['payload'])
    return {'subject': subject, 'body': body}

def get_body_from_payload(payload):
    """Extract plain text body from payload"""
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body']['data']
                return base64.urlsafe_b64decode(data).decode('utf-8')
            elif 'parts' in part:
                return get_body_from_payload(part)
    else:
        if payload['mimeType'] == 'text/plain':
            data = payload['body']['data']
            return base64.urlsafe_b64decode(data).decode('utf-8')
    return ""

# ---------------- CLASSIFICATION FUNCTIONS ----------------








def classify_and_summarize_with_llm(subject, body):
    context_text = read_file("agents/context.txt")
    prompt_text = read_file("agents/prompt.txt")
    completion = client.chat.completions.create(

        extra_body={
            "provider": {
                "sort": "throughput"
            }
        },
        model="tngtech/deepseek-r1t2-chimera:free",
        messages=[
            {
                "role": "system",
                "content": context_text,
            },
            {
                "role": "user",
                "content": f'{prompt_text}\n\nEmail subject: "{subject}" Email body: "{body}"',
            }
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    text = completion.choices[0].message.content.strip()
    try:
        result = json.loads(text)
        return result["category"], result["urgency"], result["summary"]
    except Exception as e:
        print("LLM JSON parse error:", e)
        # fallback
        return "Demande de support utilisateur", "Anodine", body[:200]







# ---------------- GOOGLE SHEETS FUNCTIONS ----------------
# ---------------- GOOGLE SHEETS FUNCTIONS ----------------
def get_spreadsheet(sheet_id=SHEET_ID, sheet_name=SHEET_NAME):
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SHEETS_SCOPE)
    client = gspread.authorize(creds)
    try:
        if sheet_id:
            spreadsheet = client.open_by_key(sheet_id)
        else:
            spreadsheet = client.open(sheet_name)
    except gspread.SpreadsheetNotFound:
        spreadsheet = client.create(sheet_name)
    return spreadsheet

def get_sheet_by_name(spreadsheet, sheet_name):
    """
    Get a worksheet by name. If it doesn't exist, create it.
    """
    try:
        sheet = spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=sheet_name, rows="1000", cols="3")
        sheet.append_row(["Sujet", "Urgence", "Synthèse"])
    return sheet

def write_tickets(spreadsheet, rows_by_category, batch_delay=1):
    """
    Writes tickets into sheets named by category.
    Automatically creates sheets if they don't exist.
    """
    for category, rows in rows_by_category.items():
        sheet = get_sheet_by_name(spreadsheet, category)
        sheet.append_rows(rows)
        time.sleep(batch_delay)  # to avoid quota limits


# ---------------- MAIN PIPELINE ----------------
if __name__ == '__main__':
    # Connect to Gmail
    service = get_gmail_service()
    messages = list_message_ids(service, query='in:inbox')
    print(f"{len(messages)} emails found.")
    
    # Collect tickets per category
    rows_by_category = defaultdict(list)
    total = len(messages[:10])
    for idx, m in enumerate(messages[:10], 1):
        print(f"Mail {idx} of {total}...")
        email_data = get_message(service, m['id'])
        category, urgency, summary = classify_and_summarize_with_llm(email_data['subject'], email_data['body'])
        rows_by_category[category].append([email_data['subject'], urgency, summary])
        print(f"Processed: {email_data['subject']} → {category} ({urgency})")
    
    # Open or create spreadsheet
    spreadsheet = get_spreadsheet(SHEET_ID, SHEET_NAME)
    
    # Write tickets in batch
    write_tickets(spreadsheet, rows_by_category)
    
    print("All tickets processed and written successfully!")
