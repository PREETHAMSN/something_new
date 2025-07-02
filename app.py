from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, jsonify
import pandas as pd
import pandas as pd
from jira import JIRA
import json
import urllib3
from tqdm import tqdm  # For progress bar
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
app = Flask(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
print("here before app starts")
app = Flask(__name__)
print("here after app starts")
# File path to your Excel file

mapping_df = pd.read_excel("CET-CORE.xlsx")
mapping_df['PLATFORM'] = mapping_df['PLATFORM'].astype(str).str.strip().str.upper()
platform_to_corecet = dict(zip(mapping_df['PLATFORM'], mapping_df['CORE-CET']))


# JIRA configuration
token = "ODc4NDQzNTI2MTI4OghLCU8T4lrpVrkuqcfYMlM5vd6F"
jira_server = "https://jira.gtie.dell.com"
tracked_names = ["P_Hota", "Mohanraj_Chinnasamy", "Sakthi_Kumar", 
                 "Santhoshkumar_Kannap", "Aparajitha_Rajapur", "Nithyasri_Arava","Darshan_M2","Prakyat_Shetty","Prajna_Harish"]

# Create a JIRA instance
jira = JIRA(options={'server': jira_server, 'verify': False}, token_auth=token)

dataset_files = {
    "2025": "updated_final_excel_with_comments.xlsx",
    "2020-2025": "updated_excel.xlsx"
}

engineer_email_map ={

    "Mohanraj_Chinnasamy": "Mohanraj.Chinnasamy@lell.com",
    "P_Hota": "P_Hota@Dell.com",
    "Prakyat_Shetty": "Prakyat.Shetty@lell.com",
    "Santoshkumar_Kannap": "Santhoshkumar_Kannap@lell.com",
    "Darshan_M2": "Darshan.M3@lell.com",
    "Nithyasri_Arava": "Nithyasri.Arava@lell.com",
    "Prajna_Harish": "Prajna.Harish@lell.com",
    "Ganesh_Karthikeyan": "Ganesh.Karthikeyan@lell.com",
    "Karrthik_C_R": "Karrthik_C_R@lell.com",
    "Ram_Yerra":"Ram.Yerra@lell.com"
}



def get_file_path(dataset):
    return dataset_files.get(dataset, dataset_files["2025"])

def get_jql_query():
    # Get today's date and the date 3 days ago in the format YYYY-MM-DD
    today = datetime.now().strftime('%Y-%m-%d')
    three_days_ago = (datetime.now() - timedelta(days=25)).strftime('%Y-%m-%d')
    print(f"Today's date: {today}")
    print(f"Date 3 days ago: {three_days_ago}")
    return f"""
    project = JIT AND
    issuetype = Defect AND
    status IN (Review,Submit,Clarify,Analyze,Verify,Closed,Draft,Cancelled) AND
    created >= {three_days_ago}
    ORDER BY "Created" DESC
    """

def search_issues(jql_query, start_at=0, max_results=1000):
    issues = []
    while True:
        print(f"Fetching issues starting at {start_at}")
        batch = jira.search_issues(jql_query, startAt=start_at, maxResults=max_results, json_result=True)
        fetched_issues = batch['issues']

        if not fetched_issues:  # Stop if no issues are returned
            print("No more issues found.")
            break

        issues.extend(fetched_issues)
        start_at += max_results

        if len(fetched_issues) < max_results:  # Stop if fewer issues than requested
            print("Fewer issues returned than requested. Ending search.")
            break

        if len(issues) >= 2000:  # Stop if we've collected enough issues
            print("Collected enough issues. Ending search.")
            break

    return issues[:2000]  # Limit to the top 1000 issues

def extract_relevant_fields(issue):
    Platform = issue["fields"].get("customfield_20012", "") 
    if isinstance(Platform, dict) and 'value' in Platform:
        plat = Platform['value'].strip().upper()
    else:
        plat = '-'

    core_cet_value = platform_to_corecet.get(plat, 'Unknown')

    Generation = issue["fields"].get("customfield_26554", "")
    if isinstance(Generation, dict) and 'value' in Generation:
        gen = Generation['value']
    else:
        gen = '-'

    Status = issue["fields"].get("status", "")
    if isinstance(Status, dict) and 'name' in Status:
        stat = Status['name']
    else:
        stat = '-'

    Issue_Manager = issue["fields"].get("customfield_19505", "")
    if isinstance(Issue_Manager, dict) and 'name' in Issue_Manager:
        im = Issue_Manager['name']
    else:
        im = '-'

    Assignee = issue["fields"].get("assignee", "")
    if isinstance(Assignee, dict) and 'name' in Assignee:
        ass = Assignee['name']
    else:
        ass = '-'

    Analyst = issue["fields"].get("customfield_18702", "")
    if isinstance(Analyst, dict) and 'name' in Analyst:
        ana = Analyst['name']
    else:
        ana = '-'
 

    created_date_raw = issue["fields"].get("created", "")
    created_date = ""
    if created_date_raw:
        created_date = created_date_raw.split("T")[0]

    comments_field = issue["fields"].get("comment", "")
    comments = []
    if comments_field and "comments" in comments_field:
        comments = [comment["body"] for comment in comments_field["comments"]]
    
    Component = issue["fields"].get("customfield_18711", "")
    if isinstance(Component, dict) and 'value' in Component:
        comp = Component['value']
    else:
        comp = ''



    Severity = issue["fields"].get("customfield_10005", "")
    if isinstance(Severity, dict) and 'value' in Severity:
        sev_full = Severity['value']
        sev = sev_full.split('-')[0].strip() if '-' in sev_full else sev_full.strip()
    else:
        sev = '-'
    
    names_in_fields = (
        any(name in (ass or "") for name in tracked_names) or
        any(name in (im or "") for name in tracked_names) or
        any(name in (ana or "") for name in tracked_names) or
        any(name in comment for comment in comments for name in tracked_names)
    )

    return {
        "JIT Number": issue["key"],
        "CORE-CET":core_cet_value,
        "Platform": plat,
        "Summary": issue["fields"]["summary"],  
        "Status": stat,
        # "Tracked Names Found": names_in_fields,
        "Technician":None,
        "Severity":sev,
        "Created Date": created_date,
        "RCE Assigned Date":None,
        "RCE Closed Date":None,
        "Component": comp,   
        "Root Cause": issue["fields"].get("customfield_15203", "-"),
        "Comments" : None,   
    }

def clean_illegal_characters(df):
    illegal_chars = {'\x00', '\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07', '\x08', '\x09', '\x0A', '\x0B', '\x0C', '\x0D', '\x0E', '\x0F', '\x10', '\x11', '\x12', '\x13', '\x14', '\x15', '\x16', '\x17', '\x18', '\x19', '\x1A', '\x1B', '\x1C', '\x1D', '\x1E'}
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].apply(lambda x: ''.join(c for c in x if c not in illegal_chars) if isinstance(x, str) else x)
    return df

def fetch_comments(jira_instance, jit_number):
    try:
        issue = jira_instance.issue(jit_number)
        comments = issue.fields.comment.comments
        return [{"body": comment.body, "created": comment.created} for comment in comments]
    except Exception as e:
        print(f"Error fetching comments for {jit_number}: {e}")
        return []

def find_tracked_names_in_comments(comments, tracked_names):
    found_names = [name for name in tracked_names if name in comments]
    return ", ".join(found_names) if found_names else "-"
## send new jits via email ............new placeholded
def send_new_jits_email(df_new_rows):
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    import smtplib

    # Convert DataFrame to HTML table
    html_table = df_new_rows.to_html(index=False, border=1)

    # Email content
    html_content = f"""
    <html>
      <body>
        <p><strong>New JITs have been added:</strong></p>
        {html_table}
      </body>
    </html>
    """

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"[JIT Update] {len(df_new_rows)} new JIT(s) added"
    msg['From'] = "DoNotReply@dell.com"
    msg['To'] = "preetham.sn@dell.com"  # Replace with mohan's address address

    msg.attach(MIMEText(html_content, 'html'))

    try:
        with smtplib.SMTP('smtp.dell.com', 587) as server:
            server.starttls()
            server.login("<svc_prddam123@apac.dell.com>", "e45_N?avT~+pog3jXw6KI78y")
            server.send_message(msg)
        print("✅ New JIT addition email sent.")
    except Exception as e:
        print(f"❌ Failed to send new JIT email: {e}")



def find_tracked_names_and_earliest_date(comments, tracked_names):
    found_names = set()  # To store unique tracked names
    earliest_date = None  # To track the earliest date
    for comment in comments:
        body = comment["body"]
        created = comment["created"]
        # Check if any tracked name is in this comment
        for name in tracked_names:
            if name in body:
                found_names.add(name)
                # Parse the creation timestamp and extract the date
                comment_date = datetime.strptime(created, "%Y-%m-%dT%H:%M:%S.%f%z").date()
                # Update earliest_date if this is the first match or earlier
                if earliest_date is None or comment_date < earliest_date:
                    earliest_date = comment_date
    # Return the names as a comma-separated string and the date in "YYYY-MM-DD" format
    return (
        ", ".join(found_names) if found_names else "-",
        earliest_date.isoformat() if earliest_date else "-"
    )


def process_excel(df,file_path):
    try:
        existing_df = pd.read_excel(file_path)
        print("excel found")
    except FileNotFoundError:
        print("Excel file not found. Creating a new one.")
        existing_df = pd.DataFrame()
   
    final_columns = [ "Issue Number",
        "JIT Number", "CORE-CET",
        "Platform", "Summary", "Status", "RCE Assigned Engineer", "Technician", "Severity", "Created Date", "RCE Assigned Date", "RCE Closed Date",
        "Component", "Root Cause", "Comments"
    ]

    for col in final_columns:
        if col not in df.columns:
            df[col] = None

    df = df[final_columns]
   
    tracked_names_column = []
    assigned_dates_column= []
    for jit_number in df["JIT Number"]:
        if pd.isna(jit_number):
            tracked_names_column.append("-")
            assigned_dates_column.append("-")
            continue
        print(f"Fetching comments for JIT Number: {jit_number}")
        comments = fetch_comments(jira, jit_number)
        tracked_names_found,earliest_date = find_tracked_names_and_earliest_date(comments, tracked_names)
        
        tracked_names_column.append(tracked_names_found)
        assigned_dates_column.append(earliest_date)
        
    df["RCE Assigned Engineer"]= tracked_names_column
    df["RC Assigned Date"] = assigned_dates_column
  

    df_filtered = df[df["RCE Assigned Engineer"] != "-"]
    #df_filtered.to_excel("new_jits.xlsx",index=False)
    print("\nNewly fetched data to be added:")
    print(df_filtered)
    


    # ✅ Track new JITs added
    if "JIT Number" in existing_df.columns:
        new_jits_df = df_filtered[~df_filtered["JIT Number"].isin(existing_df["JIT Number"])]
        print("the new jits added are:",new_jits_df)
        
    else:
        new_jits_df = df_filtered.copy()

    updated_df = pd.concat([new_jits_df, existing_df], ignore_index=True)

    for col in final_columns:
        if col not in updated_df.columns:
            updated_df[col] = None

    updated_df = updated_df[final_columns]
    updated_df.to_excel(file_path, index=False)
    print(f"Processed Excel updated and saved to {file_path}")

    # ✅ Send email only if new JITs were added
    if not new_jits_df.empty:
        send_new_jits_email(new_jits_df)
    new_jits_df=new_jits_df[final_columns]
    
    existing_df = pd.read_excel('updated_excel.xlsx')

    # Update the DataFrame with new data
    updated_df = pd.concat([existing_df, new_jits_df])

    # Write the updated DataFrame back to the Excel file
    updated_df.to_excel('updated_excel.xlsx', index=False)

        
    new_jits_df["RCE Assigned Engineer"]="-" #this is so that this column RCE be empty so that 
                                            #manager can assign any engineer
                                        # then only this column will be filled by assigned engineer name
    New_jits_df=pd.read_excel("new_jits.xlsx")
    up_df=pd.concat([New_jits_df,new_jits_df],ignore_index=True)
    up_df.to_excel("new_jits.xlsx",index=False)
    return new_jits_df
#manager_dashboard feature function , not for fetching 
 
    

def update_excel(dataset="2025"):
    file_path = get_file_path(dataset)
    jql_query = get_jql_query()
    print("Searching for issues...")
    issues = search_issues(jql_query)
    print(f"Found {len(issues)} issues.")

    # Extract relevant fields
    all_issues = [extract_relevant_fields(issue) for issue in tqdm(issues, desc="Processing Issues")]

    # Convert to DataFrame
    df_issues = pd.DataFrame(all_issues)

    df_issues = clean_illegal_characters(df_issues)

    # Process and save to final Excel file
    new_jits_df=process_excel(df_issues,file_path)
    print("Excel Update Completed")
    New_jits_df=pd.read_excel("new_jits.xlsx")
    up_df=pd.concat([New_jits_df,new_jits_df],ignore_index=True)
    up_df.to_excel("new_jits.xlsx",index=False)
    print("manager_dashboard updated")
    return new_jits_df

update_excel(dataset="2025")
# Schedule the update_excel function to run every day at 8 AM
scheduler = BackgroundScheduler()
scheduler.add_job(update_excel, 'interval', hours=1)
scheduler.add_job(update_excel, 'cron',hour=18, minute=16)
print("Scheduler started successfully")
print("hello")

def fetch_jit_details(jit_number):
    try:
        issue = jira.issue(jit_number)
        fields = issue.fields
        
        platform = fields.customfield_20012.value if fields.customfield_20012 else "-"
        core = platform_to_corecet.get(platform.strip().upper(), 'Unknown')
        component = fields.customfield_18711.value if fields.customfield_18711 else "-"
        # severity = fields.customfield_10005.value if fields.customfield_10005 else "-"
        root_cause = fields.customfield_15203 if fields.customfield_15203 else "-"
        status = fields.status.name if fields.status else "-"
        created_date = fields.created.split("T")[0] if fields.created else "-"
        if fields.customfield_10005 and fields.customfield_10005.value:
            sev_full = fields.customfield_10005.value
            severity = sev_full.split('-')[0].strip() if '-' in sev_full else sev_full.strip()
        else:
            severity = "-"
        # Fetch comments to find RCE Assigned Engineer
        comments = issue.fields.comment.comments if issue.fields.comment else []
        rce_assigned_engineer = ", ".join([name for name in tracked_names if any(name in comment.body for comment in comments)]) or "-"
    
        
        return {
            "JIT Number": issue.key,
            "CORE-CET": core,
            "Platform": platform,
            "Summary": fields.summary,
            "Status": status,
            "RCE Assigned Engineer": rce_assigned_engineer,
            "technician": None,
            "Severity": severity,
            "Created Date": created_date,    
            "Component": component,
            "Root Cause": root_cause,
        }
    except Exception as e:
        print(f"Error fetching JIT details: {e}")
        return None
app = Flask(__name__)

print("fetched jit detailes")
 
 
    
@app.route("/add_row", methods=["POST"])      
def add_row():
    data = request.get_json()
    jit_number = data.get("jit_number")
    dataset = data.get("dataset", "2025")
    file_path = get_file_path(dataset)
    if not jit_number:
        return jsonify({"success": False, "message": "JIT Number is required."})

    try:
        df = pd.read_excel(file_path)
        if jit_number in df["JIT Number"].astype(str).values:
            return jsonify({"success": False, "message": "JIT Number already exists in the Excel file."})
    except FileNotFoundError:
        df = pd.DataFrame()
    
    jit_details = fetch_jit_details(jit_number)
    if not jit_details:
        return jsonify({"success": False, "message": "JIT Number not found."})

    try:
        final_columns = [
    "JIT Number", "CORE-CET","Platform", "Summary", "Status", "RCE Assigned Engineer", "Technician",
     "Severity", "Created Date", "RCE Assigned Date", "RCE Closed Date",
    "Component", "Root Cause", "Comments"
    ]
        for col in final_columns:
            if col not in jit_details:
                jit_details[col] = None 
        new_row = pd.DataFrame([jit_details])[final_columns]
        df = pd.concat([new_row, df], ignore_index=True)
        df.to_excel(file_path, index=False)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
print("add row opt")

@app.route("/", methods=["GET", "POST"])
def index():
    # Read the Excel file
    dataset = request.args.get("dataset", default="2025")
    file_path = get_file_path(dataset)

    
    df = pd.read_excel(file_path)

    # Get the current page from the request arguments (default to page 1)
    page = request.args.get("page", default=1, type=int)
    rows_per_page = 25

    # Handle search functionality
    search_jit = request.args.get("search_jit")
    highlighted_row = None
    search_page = None

    if search_jit:
    # Check if the JIT Number exists in the DataFrame
        search_result = df[df["JIT Number"].astype(str) == search_jit]
        if not search_result.empty:
        # Highlight the row if found
            highlighted_row = search_result.index[0]
        # Determine the page where the highlighted row is located
            search_page = (highlighted_row // rows_per_page) + 1

        # If the row is on a different page, redirect to that page
            if search_page != page:
                return redirect(url_for("index", page=search_page, search_jit=search_jit))

        # Move the highlighted row to the top of the DataFrame for the current page
        df = pd.concat([search_result, df.drop(index=search_result.index)], ignore_index=True)

    else:
        print(f"JIT Number {search_jit} not found in the DataFrame")

    # Calculate total pages
    total_pages = (len(df) + rows_per_page - 1) // rows_per_page

    # Slice the DataFrame for the current page
    start = (page - 1) * rows_per_page
    end = start + rows_per_page
    paginated_df = df.iloc[start:end]

    # Add row indices for rendering
    data = [{"index": idx, **row} for idx, row in paginated_df.iterrows()]
    columns = df.columns.tolist()

    # Specify which columns should be editable
    editable_columns = [ "RCE Assigned Date", "RCE Closed Date", "Root Cause", "RCE Assigned Engineer","Technician","Comments","CORE-CET"]

    return render_template(
        "table.html",
        data=data,
        columns=columns,
        editable_columns=editable_columns,
        page=page,
        total_pages=total_pages,
        search_jit=search_jit,
        highlighted_row=highlighted_row
    )

@app.route("/save", methods=["POST"])
def save():
    dataset = request.args.get("dataset", "2025")
    file_path = get_file_path(dataset)
    df = pd.read_excel(file_path)

    editable_string_columns = ["Technician", "RCE Assigned Engineer", "RCE Assigned Date", "RCE Closed Date", "Root Cause", "CORE-CET", "Comments"]
    for col in editable_string_columns:
        if col in df.columns:
            df[col] = df[col].astype(object)

    edited_rows = []

    for index, row in df.iterrows():
        row_updated = False
        engineer_changed = False
        changed_engineers = set()

        # Get new engineers dynamically
        new_engineers = set()
        engineer_inputs_found = False  # track if any engineer field was present

        i = 1
        while True:
            input_name = f"RCE Assigned Engineer_{i}_{index}"
            if input_name not in request.form:
                break  # stop when form has no more of these inputs

            value = request.form.get(input_name, "").strip()
            if value:
                new_engineers.add(value)
                engineer_inputs_found = True  # found actual input
            i += 1

# Only compare and update if engineer fields were submitted for this row
        if engineer_inputs_found:
            old_engineer_str = df.at[index, "RCE Assigned Engineer"]
            old_engineers = set()
            if pd.notna(old_engineer_str):
                old_engineers = set(map(str.strip, old_engineer_str.split(",")))

            if old_engineers != new_engineers:
                df.at[index, "RCE Assigned Engineer"] = ",".join(new_engineers)
                changed_engineers = new_engineers - old_engineers  # ✅ only new ones
                row_updated = True
                engineer_changed = True    
        # Update other editable fields
        for column in df.columns:
            if column == "RCE Assigned Engineer":
                continue

            input_name = f"{column}_{index}"
            if input_name in request.form:
                new_value = request.form[input_name]
                if str(df.at[index, column]) != new_value:
                    df.at[index, column] = new_value
                    row_updated = True

        if row_updated:
            edited_rows.append((df.iloc[index], engineer_changed, changed_engineers))

    df.to_excel(file_path, index=False)

    # Send email to new engineers only
    emails_to_jits = {}

    for row, engineer_changed, changed_engineers in edited_rows:
        if engineer_changed:
            for eng in changed_engineers:
                email = engineer_email_map.get(eng.strip())
                if email:
                    emails_to_jits.setdefault(email, []).append(row)

# Send one email per engineer with all assigned JITs
    for email, rows in emails_to_jits.items():
        send_bulk_assignment_email(email, rows)

    return redirect(url_for("index"))

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
print("save opt")

def send_bulk_assignment_email(to_email, rows):
    if not rows:
        return

    headers = rows[0].index.tolist()

    html_rows = ""
    for row in rows:
        html_rows += "<tr>" + "".join(f"<td>{row[col]}</td>" for col in headers) + "</tr>"

    html_body = f"""
    <html>
      <body>
        <p>You have been assigned to the following JIT issues:</p>
        <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; font-family: Arial;">
          <thead style="background-color: #f2f2f2;">
            <tr>{''.join(f'<th>{col}</th>' for col in headers)}</tr>
          </thead>
          <tbody>
            {html_rows}
          </tbody>
        </table>
      </body>
    </html>
    """

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"[JIT Assignment] {len(rows)} new issue(s) assigned"
    msg['From'] = "DoNotReply@dell.com"
    msg['To'] = to_email
    msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP('smtp.dell.com', 587) as server:
            server.starttls()
            server.login("<svc_prddam123@apac.dell.com>", "e45_N?avT~+pog3jXw6KI78y")
            server.send_message(msg)
        print(f"✅ Email sent to {to_email} with {len(rows)} JIT(s)")
    except Exception as e:
        print(f"❌ SMTP send failed to {to_email}: {e}")
print("send mail")

## old placeholder of send_new_jits_mail funciton................

print("final mail")
@app.route("/download")
def download():
    # Send the Excel file to the user
    dataset = request.args.get("dataset", "2025")
    file_path = get_file_path(dataset)
    return send_file(file_path, as_attachment=True)

@app.route("/search_jit", methods=["GET"])
def search_jit():
    search_jit = request.args.get("search_jit", "").strip()
    if not search_jit:
        return jsonify({"success": False, "message": "JIT Number is required."})

    try:
        dataset = request.args.get("dataset", "2025")
        file_path = get_file_path(dataset)
        df = pd.read_excel(file_path)
        rows_per_page = 25  # Adjust based on your pagination

        # Convert all JIT Numbers to string for proper comparison
        df["JIT Number"] = df["JIT Number"].astype(str)
        search_jit = str(search_jit)  # Ensure search query is also a string

        # Locate the JIT Number in the DataFrame
        search_result = df[df["JIT Number"] == search_jit]
        if search_result.empty:
            return jsonify({"success": False, "message": "JIT Number not found."})

        highlighted_row = search_result.index[0]
        search_page = (highlighted_row // rows_per_page) + 1

        return jsonify({"success": True, "page": search_page})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
print("search jits")

@app.route("/delete_engineer")
def delete_engineer():
    index = request.args.get("index", type=int)
    dataset = request.args.get("dataset", "2025")
    file_path = get_file_path(dataset)

    try:
        df = pd.read_excel(file_path)
        if 0 <= index < len(df):
            # Save a single space so the template renders one blank dropdown
            df.at[index, "RCE Assigned Engineer"] = " "
            df.to_excel(file_path, index=False)
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": "Invalid row index"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
print("delete opt")

@app.route("/delete_row")
def delete_row():
    index = request.args.get("index", type=int)
    dataset = request.args.get("dataset", "2025")
    file_path = get_file_path(dataset)
    try:
        df = pd.read_excel(file_path)
        if 0 <= index < len(df):
            df.at[index, "RCE Assigned Engineer"] = ","  
            df.to_excel(file_path, index=False)
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": "Invalid row index"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
print("delete row opt")
@app.route("/add_engineer")
def add_engineer():
    index = request.args.get("index", type=int)
    engineer = request.args.get("engineer", "").strip()
    dataset = request.args.get("dataset", "2025")
    file_path = get_file_path(dataset)

    if not engineer:
        return jsonify({"success": False, "message": "No engineer provided."})

    try:
        df = pd.read_excel(file_path)
        if 0 <= index < len(df):
            current = df.at[index, "RCE Assigned Engineer"]
            existing_engineers = set(map(str.strip, str(current).split(","))) if pd.notna(current) else set()

            if engineer in existing_engineers:
                return jsonify({"success": False, "message": "Engineer already assigned."})

            existing_engineers.add(engineer)
            df.at[index, "RCE Assigned Engineer"] = ",".join(existing_engineers)
            df.to_excel(file_path, index=False)

            email = engineer_email_map.get(engineer)
            if email:
                send_bulk_assignment_email(email, df.iloc[index])

            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": "Invalid row index"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
print("right now i am above main")

# File paths
first_excel_path = "new_jits.xlsx"  # Replace with the path to your first Excel file (30 issues)
second_excel_path = "updated_excel.xlsx"  # Replace with the path to your fully populated Excel file
output_excel_path = "new_jits.xlsx"  # Output file path (can overwrite first_excel_path if desired)

# Read both Excel files
first_df = pd.read_excel(first_excel_path)
second_df = pd.read_excel(second_excel_path)

# Ensure "JIT Number" is treated as a string in both DataFrames to avoid type mismatches
first_df["JIT Number"] = first_df["JIT Number"].astype(str)
second_df["JIT Number"] = second_df["JIT Number"].astype(str)

# Merge the DataFrames to update "RCE Assigned Date"
# Keep all rows from first_df (left join) and only update "RCE Assigned Date" where there's a match
merged_df = first_df.merge(
    second_df[["JIT Number", "RCE Assigned Date"]],  # Select only the columns needed from second_df
    on="JIT Number",
    how="left",  # Keep all rows from first_df
    suffixes=("", "_second")  # Avoid column name conflicts
)

# Update "RCE Assigned Date" in first_df with values from second_df where available
# If there's no match, keep the original value (likely None or empty)
merged_df["RCE Assigned Date"] = merged_df["RCE Assigned Date_second"].where(
    merged_df["RCE Assigned Date_second"].notna(),
    merged_df["RCE Assigned Date"]
)

# Drop the temporary column from the merge
merged_df = merged_df.drop(columns=["RCE Assigned Date_second"])

# Ensure the column order matches the original first_df
merged_df = merged_df[first_df.columns]

# Save the updated DataFrame to the output file
merged_df.to_excel(output_excel_path, index=False)
print(f"Updated Excel file saved to {output_excel_path}")

if __name__ == "__main__":
    from werkzeug.serving import is_running_from_reloader

    if not is_running_from_reloader():
        # Start scheduler only in the original process
        #scheduler.start()
        print("Scheduler started successfully")
    app.run(debug=True)