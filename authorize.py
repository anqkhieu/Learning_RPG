import gspread
from oauth2client.service_account import ServiceAccountCredentials

def authorizeSheets():
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    if creds.access_token_expired: gc.login()
    gc = gspread.authorize(creds)
    return gc

def openSheet(name="None"):
    try:
        sh = gc.open("Learning RPG - Sheet")
    except:
        gc = authorizeSheets()
        sh = gc.open("Learning RPG - Sheet")

    if name != "None": sh = sh.worksheet(name)
    return sh
