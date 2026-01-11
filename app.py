import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, flash, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import mysql.connector as mysql
import pandas, openpyxl
from datetime import datetime
from io import BytesIO

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Where to send users if they aren't logged in


class User(UserMixin):
    def __init__(self, id):
        self.id = id

# This callback is used to reload the user object from the user ID stored in the session
@login_manager.user_loader
def load_user(user_id):
    # In a real app, you would fetch the user from MySQL here
    # return User.get(user_id)
    return User(user_id)


# Custom Filter for Indian Number Formatting
def format_indian(value):
    if value is None:
        value = 0
    value = float(value)
    # Convert to string with 2 decimal places
    s = "{:.2f}".format(value)
    # Split the number (12345) and the decimal (.00)
    num, dec = s.split('.')
    
    # Logic to add commas for Lakhs/Crores
    if len(num) <= 3:
        return s
    
    # The last 3 digits are standard (Hundreds)
    last_three = num[-3:]
    # The rest are the thousands/lakhs
    remaining = num[:-3]
    
    # Add a comma every 2 digits for the remaining part (Indian Style)
    # This magic logic reverses the string, chunks by 2, and joins them
    import re
    remaining = re.sub(r"(\d)(?=(\d{2})+(?!\d))", r"\1,", remaining)
    
    return f"{remaining},{last_three}.{dec}"

# Register the filter so Jinja knows it exists
app.jinja_env.filters['inr_format'] = format_indian

mysql_con = mysql.connect(
	host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
	)
if mysql_con.is_connected():
    print("Connected Successfully to Database!")
else:
    print("Database connection error")
mysql_con.autocommit=True
cursor = mysql_con.cursor()

# Your simplified database (List)
customers = set()
contacts = set()
items = set()
cursor.execute("SELECT Customer, Contact, Item FROM bill_details")
for data in cursor.fetchall():
    cust_name = data[0]
    contact = data[1]
    item = data[2]

    if cust_name:        
        customers.add(cust_name)
    if contact:
        contacts.add(contact)
    if item:
        items.add(item)
customers=list(customers)
contacts = list(contacts)
items = list(items)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Verify password (SIMULATED for now)
        if username == "admin" and password == "admin@123":
            user = User(id=username)
            login_user(user)  # This logs them in!
            
            # Redirect to the page they tried to visit, or home
            next_page = request.args.get('next')
            return redirect(next_page or '/')
            
        flash("Invalid credentials")
        
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    cursor.execute("SELECT SUM(`Invoiced amount`), SUM(`Recieved amount`), SUM(`Balance amount`) FROM bill_details")
    summary_data = cursor.fetchone()
    
    total_invoiced = summary_data[0]
    total_recieved = summary_data[1]
    total_balance = summary_data[2]

    # Fetch last invoice no.
    cursor.execute("SELECT `Id` FROM bill_details ORDER BY `Id` DESC LIMIT 1")
    new_invoice_no = int(cursor.fetchone()[0])+1
    

    if request.method == 'POST':
        # Get what the user typed/selected
        new_customer = request.form['customer_name']
        new_contact = request.form['contact_name']
        new_item = request.form['item_name']
        new_date = request.form['invoice_date']
        new_note = request.form['note']
        # Get Numbers (Handle empty strings safely)
        new_inv_amt = request.form['invoiced_amount'] or 0
        new_rec_amt = request.form['received_amount'] or 0
        new_tds1 = request.form['tds_1'] or 0
        new_tds2 = request.form['tds_2'] or 0
        
        # Calculate new balance for the database (Optional, or calculate on read)
        new_balance = float(new_inv_amt) - float(new_rec_amt) - float(new_tds1) - float(new_tds2)
        
        # LOGIC: Check if it exists        
        if new_customer not in customers:
            # It's new! Add to database
            customers.append(new_customer)
        if new_contact not in contacts:
            # It's new! Add to database
            customers.append(new_customer)
        if new_item not in items:
            # It's new! Add to database
            customers.append(new_customer)
        
        
        # Insert into database
        cursor.execute("INSERT INTO bill_details(`Invoice no.`, `Customer`, `Contact`, `Item`, `Invoiced amount`, `Recieved amount`, `TDS 1`, `TDS 2`, `Balance amount`, `Invoice Date`, `Note`) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (f"SE/25-26/{new_invoice_no}", new_customer, new_contact, new_item, new_inv_amt, new_rec_amt, new_tds1, new_tds2, new_balance, new_date, new_note))
        
            
        # # Re-render the page with the updated list so the new name appears next time
        # return render_template('test.html', customers=customers, message=message)

        # print(selected_name, selected_contact, selected_item)

        # SYNTAX: flash("Message Text", "category")
        # Categories map to Bootstrap colors: 'success' (Green), 'danger' (Red), 'warning' (Yellow)
        flash("Invoice saved successfully!", "success")
        return redirect('/')
    
    
    

    return render_template('index.html', 
                           customers=customers, 
                           contacts=contacts, 
                           items=items,
                           total_invoiced=total_invoiced,
                           total_recieved=total_recieved,
                           total_balance=total_balance,
                           new_invoice_no = new_invoice_no)

@app.route('/view-invoices')
@login_required
def view_invoices():
    # In a real app, you would fetch this from MySQL:
    # cursor.execute("SELECT * FROM invoices")
    # invoices = cursor.fetchall()
    cursor.execute("SELECT * FROM bill_details")
    invoices_data = cursor.fetchall()
    invoices = [{"id": inv[1],
                "date": inv[10],
                "customer": inv[2],
                "contact": inv[3],
                "item": inv[4],
                "inv_amt": inv[5],
                "rec_amt": inv[6],
                "tds1": inv[7],
                "tds2": inv[8],
                "balance": inv[9],
                "note": "Partial Payment received" if 0<inv[6]<inv[5] else "Payment Not Recieved" if inv[6]==0 else "Payment Recieved"} 
                for inv in invoices_data
                ]
    
    
    return render_template('view_invoices.html', invoices=invoices)

@app.route('/edit-invoice/<invoice_id>', methods=['GET', 'POST'])
@login_required
def edit_invoice(invoice_id):
    # 1. FETCH EXISTING DATA
    # In a real app: cursor.execute("SELECT * FROM invoices WHERE id=%s", (invoice_id,))
    invoice_id = invoice_id.replace('_', '/')
    # Mock data to simulate what the database returns
    cursor.execute("SELECT * FROM bill_details WHERE `Invoice no.`=%s",(invoice_id,))
    inv = cursor.fetchone()
    print(inv)
    invoice_data = {"id": inv[1],
                "date": inv[10],
                "customer": inv[2],
                "contact": inv[3],
                "item": inv[4],
                "inv_amt": inv[5],
                "rec_amt": inv[6],
                "tds1": inv[7],
                "tds2": inv[8],
                "balance": inv[9],
                "note": "Partial Payment received" if 0<inv[6]<inv[5] else "Payment Not Recieved" if inv[6]==0 else "Payment Recieved" 
                
                }

    # 2. HANDLE UPDATES (POST)
    if request.method == 'POST':
        # Get updated values from form
        new_customer = request.form['customer_name']
        new_contact = request.form['contact_name']
        new_item = request.form['item_name']
        new_date = request.form['invoice_date']
        new_note = request.form['note']
        # Get Numbers (Handle empty strings safely)
        new_inv_amt = request.form['invoiced_amount'] or 0
        new_rec_amt = request.form['received_amount'] or 0
        new_tds1 = request.form['tds_1'] or 0
        new_tds2 = request.form['tds_2'] or 0
        
        # Calculate new balance for the database (Optional, or calculate on read)
        new_balance = float(new_inv_amt) - float(new_rec_amt) - float(new_tds1) - float(new_tds2)
        
        # Write data in mysql table
        # Id, Invoice no., Customer, Contact, Item, Invoiced amount, Recieved amount, TDS 1, TDS 2, Balance amount, Invoice Date, Note
        cursor.execute("UPDATE bill_details SET `Customer`=%s, `Contact`=%s, `Item`=%s, `Invoiced amount`=%s, `Recieved amount`=%s, `TDS 1`=%s, `TDS 2`=%s, `Balance amount`=%s, `Invoice Date`=%s, `Note`=%s WHERE `Invoice no.`=%s",(new_customer, new_contact, new_item, new_inv_amt, new_rec_amt, new_tds1, new_tds2, new_balance, new_date, new_note, invoice_id))
        flash(f"Invoice {invoice_id} updated successfully!", "success")
        return redirect('/view-invoices')

    # 3. RENDER FORM (GET)
    # We pass the same dropdown lists (customers, contacts) so the search still works
    

    return render_template('edit_invoice.html', 
                           invoice=invoice_data,
                           customers=customers, 
                           contacts=contacts, 
                           items=items)

@app.route('/delete-invoice/<invoice_id>', methods=['GET', 'POST'])
@login_required
def deletes_invoice(invoice_id):
    if request.method=="POST":
        invoice_id = invoice_id.replace('_', '/')

        cursor.execute("DELETE FROM bill_details WHERE `Invoice no.`=%s",(invoice_id,))
        flash(f"Invoice {invoice_id} deleted successfully!", "success")
        return redirect('/view-invoices')

@app.route('/export-invoices', methods=["POST"])
@login_required
def export_invoices():
    data = request.get_json()
    invoice_ids = tuple(data.get('ids', ()))
    placeholders = ', '.join(['%s'] * len(invoice_ids))

    query = f"SELECT * FROM bill_details WHERE `Invoice no.` IN ({placeholders})"
    cursor.execute(query, invoice_ids)

    fetched_data = cursor.fetchall()
    # Convert to pd dataframe
    df = pandas.DataFrame(fetched_data, columns=['Id', 'Invoice no.', 'Customer', 'Contact', 'Item', 'Invoiced amount', 'Recieved amount', 'TDS 1', 'TDS 2', 'Balance amount', 'Invoice Date', 'Note'])
    df.drop(columns=['Id'], inplace=True)
    df.fillna("", inplace=True)
    df = df.replace({"None": ""})

    # Create an in-memory buffer for the Excel file
    output = BytesIO()
    
    # Save the Excel to the buffer instead of a physical file
    with pandas.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Invoices')
    
    output.seek(0) # Go to the beginning of the buffer

    filename = f'Invoice-List-{datetime.now().strftime("%d-%b-%Y")}.xlsx'

    # Return the file directly to the browser
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )
if __name__ == '__main__':
    app.run()