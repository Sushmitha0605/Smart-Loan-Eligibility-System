from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # 🔥 DROP OLD TABLES (important to avoid column mismatch)
    c.execute("DROP TABLE IF EXISTS loans")
    c.execute("DROP TABLE IF EXISTS customers")

    # ✅ CREATE LOANS TABLE
    c.execute('''
        CREATE TABLE loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            decision TEXT,
            risk TEXT,
            emi REAL,
            emi_ratio REAL
        )
    ''')

    # ✅ CREATE CUSTOMERS TABLE (correct structure)
    c.execute('''
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            age INTEGER,
            income REAL,
            credit INTEGER,
            existing_loans INTEGER
        )
    ''')

    conn.commit()
    conn.close()


def save_application(name, decision, risk, emi, emi_ratio):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute('''
        INSERT INTO loans (name, decision, risk, emi, emi_ratio)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, decision, risk, emi, emi_ratio))

    conn.commit()
    conn.close()


# ---------------- LOAN LOGIC ----------------
def evaluate_loan(data):
    score = 0
    flags = []

    try:
        income = int(data['income'])
        loan = int(data['loan'])
        credit = int(data['credit'])
        existing_loans = int(data['existing_loans'])
    except:
        return "Rejected", "High", ["Invalid input data"], 0, 0

    # Credit
    if credit > 700:
        score += 3
    elif credit > 600:
        score += 2
    else:
        score += 1
        flags.append("Low credit score")

    # Income
    if income > 50000:
        score += 3
    elif income > 25000:
        score += 2

    # Loan vs income
    if loan > income * 6:
        flags.append("Loan too high compared to income")
    else:
        score += 2

    # Existing loans
    if existing_loans >= 3:
        score -= 1
        flags.append("Too many existing loans")
    else:
        score += 1

    if existing_loans > 0:
        flags.append(f"{existing_loans} existing loan(s)")

    # EMI
    rate = 0.08 / 12
    months = 60

    emi = (loan * rate * (1 + rate)**months) / ((1 + rate)**months - 1)
    emi_ratio = (emi / income) * 100

    if emi_ratio > 40:
        flags.append("EMI too high compared to income")

    # Decision
    if score >= 7:
        decision = "Approved"
        risk = "Low"
    elif score >= 5:
        decision = "Review"
        risk = "Medium"
    else:
        decision = "Rejected"
        risk = "High"

    return decision, risk, flags, round(emi, 2), round(emi_ratio, 2)


# ---------------- ROUTES ----------------

# Login Page
@app.route('/')
def login():
    return render_template('login.html')


# Login Handler
@app.route('/login', methods=['POST'])
def login_post():
    print("FORM DATA:", request.form)  # 🔥 DEBUG LINE

    username = request.form.get('username')
    password = request.form.get('password')

    if username == "admin" and password == "1234":
        return redirect('/dashboard')
    else:
        return f"Invalid credentials | You entered: {username} / {password}"


# Dashboard
@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT name, decision, risk, emi FROM loans")
    data = c.fetchall()

    conn.close()

    total = len(data)
    approved = len([d for d in data if d[1] == "Approved"])
    rejected = len([d for d in data if d[1] == "Rejected"])

    return render_template('dashboard.html',
                           total=total,
                           approved=approved,
                           rejected=rejected,
                           data=data)


# Applications Page
@app.route('/applications')
def applications():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT name, decision, risk, emi FROM loans")
    data = c.fetchall()

    conn.close()

    return render_template('applications.html', data=data)


# Delete Application
@app.route('/delete/<name>')
def delete(name):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("DELETE FROM loans WHERE name = ?", (name,))
    conn.commit()
    conn.close()

    return redirect('/applications')


# Customers Page
@app.route('/customers')
def customers():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT * FROM customers")
    data = c.fetchall()

    conn.close()

    return render_template('customers.html', data=data)


# Add Customer
@app.route('/add_customer', methods=['GET', 'POST'])
def add_customer():
    if request.method == 'POST':
        data = request.form

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute('''
            INSERT INTO customers (name, age, income, credit, existing_loans)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data['name'],
            data['age'],
            data['income'],
            data['credit'],
            data['existing_loans']
        ))

        conn.commit()
        conn.close()

        return redirect('/customers')

    return render_template('add_customer.html')


# Prefill Loan Form
@app.route('/new/<int:id>')
def new_application_prefill(id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT * FROM customers WHERE id = ?", (id,))
    customer = c.fetchone()

    conn.close()

    return render_template('new_application.html', customer=customer)


# New Application
@app.route('/new')
def new_application():
    return render_template('new_application.html', customer=None)


# Result Page
@app.route('/result', methods=['POST'])
def result():
    try:
        data = request.form

        decision, risk, flags, emi, emi_ratio = evaluate_loan(data)

        save_application(data['name'], decision, risk, emi, emi_ratio)

        return render_template('result.html',
                               decision=decision,
                               risk=risk,
                               flags=flags,
                               emi=emi,
                               emi_ratio=emi_ratio)

    except Exception as e:
        return f"ERROR: {str(e)}"


# ---------------- RUN ----------------
if __name__ == '__main__':
    init_db()
    app.run(debug=True)