from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

def init_db():

    
    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()
 
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT UNIQUE,
    password TEXT,
    role TEXT
)
""")

    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            age INTEGER,
            disease TEXT,
            created_date TEXT
        )
    ''')

    cursor.execute('''
         CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            specialization TEXT,
            phone TEXT,
            status TEXT
    )
''')
    
    
    cursor.execute("""
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_name TEXT,
    doctor_name TEXT,
    date TEXT,
    time TEXT,
    status TEXT
)
""")
    
    cursor.execute("""
CREATE TABLE IF NOT EXISTS billing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_name TEXT,
    doctor_name TEXT,
    treatment TEXT,
    amount INTEGER,
    bill_date TEXT
)
""")
    
    cursor.execute("""
CREATE TABLE IF NOT EXISTS settings(
id INTEGER PRIMARY KEY AUTOINCREMENT,
hospital_name TEXT,
email TEXT,
contact TEXT
)
""")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS appointment_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id INTEGER,
    gender TEXT,
    blood_group TEXT,
    phone TEXT,
    disease TEXT,
    previous_treatment TEXT
)
""")
    conn.commit()
    conn.close()


init_db()

def update_db():
    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()

    try:
        cursor.execute("ALTER TABLE patients ADD COLUMN email TEXT")
        print("✅ Email column added successfully")
    except:
        print("⚠ Column already exists")

    conn.commit()
    conn.close()

update_db()
  
def send_sms(phone, message):
    url = "https://www.fast2sms.com/dev/bulkV2"

    headers = {
        'authorization': 'YOUR_API_KEY',
        'Content-Type': "application/json"
    }

    payload = {
        "route": "q",
        "message": message,
        "language": "english",
        "numbers": phone
    }

    response = requests.post(url, json=payload, headers=headers)
    print("SMS Response:", response.text)

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        conn = sqlite3.connect('hospital.db')
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                (name, email, password, role)
            )
            conn.commit()
        except:
            conn.close()
            return "Email already exists!"

        conn.close()

        session['role'] = role
        session['name'] = name

        if role == "admin":
            return redirect('/admin')
        elif role == "doctor":
            return redirect('/doctor')
        else:
            return redirect('/patient')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        conn = sqlite3.connect('hospital.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM users WHERE email=? AND password=? AND role=?",
            (email, password, role)
        )
        user = cursor.fetchone()
        conn.close()

        if user:
            session['role'] = role
            session['name'] = user[0]

            if role == "admin":
                return redirect('/admin')
            elif role == "doctor":
                return redirect('/doctor')
            else:
                return redirect('/patient')
        else:
            return "Invalid Credentials!"

    return render_template('login.html')


@app.route('/admin')
def admin():
    if 'role' in session and session['role'] == 'admin':

        section = request.args.get('section', 'dashboard')
        view_id = request.args.get('id')

        conn = sqlite3.connect('hospital.db')
        conn.row_factory = sqlite3.Row   
        cursor = conn.cursor()

        absent_notifications = []

        cursor.execute("SELECT name FROM doctors WHERE status='On Leave'")
        absent_doctors = cursor.fetchall()

        for doctor in absent_doctors:
            doctor_name = doctor[0]
            
            today = datetime.now().strftime("%Y-%m-%d")

            cursor.execute("""
            SELECT patient_name, date 
            FROM appointments 
            WHERE doctor_name=? AND date=?
            """, (doctor_name,today))

            patients = cursor.fetchall()

            for p in patients:
                msg = f"Doctor {doctor_name} is absent today. Appointment for {p[0]} is affected."
                absent_notifications.append(msg)

        cursor.execute("SELECT * FROM patients")
        patients = cursor.fetchall()

        cursor.execute("SELECT * FROM doctors")
        doctors = cursor.fetchall()

        search = request.args.get('search')

        if section == 'appointments' and search:
            cursor.execute("""
            SELECT * FROM appointments 
            WHERE patient_name LIKE ?
            """, ('%' + search + '%',))
        else:
            from datetime import timedelta

            today = datetime.now().strftime("%Y-%m-%d")
            tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

            cursor.execute("""
            SELECT * FROM appointments
            ORDER BY 
                CASE 
                    WHEN date=? THEN 1
                    WHEN date=? THEN 2
                    ELSE 3
                 END,
                 date ASC
            """, (today, tomorrow))
            appointments = cursor.fetchall()

        cursor.execute("SELECT * FROM billing")
        bills = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) FROM doctors")
        total_doctors = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM patients")
        total_patients = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM appointments")
        total_appointments = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM billing")
        total_bills = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(amount) FROM billing")
        total_earnings = cursor.fetchone()[0] or 0

      
        selected_appointment = None

        if section in ['view_appointment', 'report'] and view_id:
           cursor.execute("""
           SELECT a.*, d.gender, d.blood_group, d.phone, d.disease, d.previous_treatment
           FROM appointments a
           LEFT JOIN appointment_details d
           ON a.id = d.appointment_id
           WHERE a.id=?
           """, (view_id,))
    
           selected_appointment = cursor.fetchone()


        grouped_appointments = {}

        if section == 'sections':
            cursor.execute("""
            SELECT a.*, d.disease
            FROM appointments a
            LEFT JOIN appointment_details d
            ON a.id = d.appointment_id
            """)

            data = cursor.fetchall()

            for row in data:
                 disease = row[6] if row[6] else "Unknown"

                 if disease not in grouped_appointments:
                    grouped_appointments[disease] = []

                 grouped_appointments[disease].append(row)

        conn.close()

        return render_template(
    'admin.html',
    name=session['name'],
    section=section,
    patients=patients,
    doctors=doctors,
    appointments=appointments,
    bills=bills,
    total_doctors=total_doctors,
    total_patients=total_patients,
    total_appointments=total_appointments,
    total_bills=total_bills,
    total_earnings=total_earnings,
    selected_appointment=selected_appointment,
    grouped_appointments=grouped_appointments,
    absent_notifications=absent_notifications
    )

    return redirect('/login')



@app.route('/doctor')
def doctor():

    if 'role' not in session or session['role'] != 'doctor':
        return redirect('/login')
    
    section = request.args.get('section')
    view_id = request.args.get('view_id')

    section = request.args.get('section', 'dashboard')
    view_id = request.args.get('view_id')

    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM patients")
    patients = cursor.fetchall()

    doctor_name = session['name']

    cursor.execute("""
    SELECT * FROM appointments 
    WHERE doctor_name=?
    """, (doctor_name,))

    appointments = cursor.fetchall()

    selected_appointment = None

    if view_id:
     cursor.execute("SELECT * FROM appointments WHERE id=?", (view_id,))
     selected_appointment = cursor.fetchone()
    
     conn.close()

    return render_template(
      'doctor.html',
       section=section,
       patients=patients,
       appointments=appointments,
       selected_appointment=selected_appointment
)
@app.route('/add_patient', methods=['POST'])
def add_patient():

    name = request.form['name']
    age = request.form['age']
    disease = request.form['disease']

    created_date = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO patients (name, age, disease, created_date) VALUES (?, ?, ?, ?)",
        (name, age, disease, created_date)
    )

    conn.commit()
    conn.close()

    return redirect('/admin?section=patients')

import re

@app.route('/add_doctor', methods=['POST'])
def add_doctor():
    name = request.form['name']
    specialization = request.form['specialization']
    phone = request.form['phone']
    status = request.form['status']

    
    valid_specializations = [
        "Cardiologist", "Dermatologist", "Neurologist",
        "Orthopedic", "Pediatrician", "Gynecologist",
        "General Physician"
    ]

    if specialization not in valid_specializations:
        return " Invalid specialization!"

    if not re.match("^[0-9]{10}$", phone):
        return " Phone must be exactly 10 digits!"

    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO doctors (name, specialization, phone, status) VALUES (?,?,?,?)",
        (name, specialization, phone, status)
    )

    conn.commit()
    conn.close()

    return redirect('/admin?section=doctors')
@app.route('/add_appointment', methods=['POST'])
def add_appointment():

    patient_name = request.form['patient_name']
    doctor_name = request.form['doctor_name']
    date = request.form['date']
    time = request.form['time']
    status = request.form['status']
    gender = request.form['gender']
    blood_group = request.form['blood_group']
    phone = request.form['phone']
    disease = request.form['disease']
    previous_treatment = request.form['previous_treatment']

    
    if not re.match("^[A-Za-z ]+$", patient_name):
        return " Patient name must contain only letters!"

    if phone and not re.match("^[0-9]{10}$", phone):
        return " Phone must be 10 digits!"

    if disease and not re.match("^[A-Za-z ]+$", disease):
        return " Disease must contain only letters!"

    if previous_treatment and not re.match("^[A-Za-z ]+$", previous_treatment):
        return " Previous treatment must contain only letters!"

    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()

    cursor.execute(
        """INSERT INTO appointments (patient_name, doctor_name, date, time, status) VALUES (?,?,?,?,?)""",
        (patient_name, doctor_name, date, time, status)
    )

    appointment_id = cursor.lastrowid 

    # INSERT into appointment_details
    cursor.execute("""
    INSERT INTO appointment_details 
    (appointment_id, gender, blood_group, phone, disease, previous_treatment)
    VALUES (?,?,?,?,?,?)
    """, (appointment_id, gender, blood_group, phone, disease, previous_treatment))

    conn.commit()
    conn.close()

    return redirect('/admin?section=appointments')


@app.route('/delete_patient/<int:id>')
def delete_patient(id):

    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()

    cursor.execute("DELETE FROM patients WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect('/doctor?section=patients')

@app.route('/delete_doctor/<int:id>')
def delete_doctor(id):
    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()

    cursor.execute("DELETE FROM doctors WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect('/admin?section=doctors')


@app.route('/delete_appointment/<int:id>')
def delete_appointment(id):

    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()

    cursor.execute("DELETE FROM appointment_details WHERE appointment_id=?", (id,))
    cursor.execute("DELETE FROM appointments WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect('/admin?section=appointments')

@app.route('/add_bill', methods=['POST'])
def add_bill():

    patient_name = request.form['patient_name']
    doctor_name = request.form['doctor_name']
    treatment = request.form['treatment']
    amount = request.form['amount']
    bill_date = request.form['bill_date']

    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO billing (patient_name, doctor_name, treatment, amount, bill_date)
        VALUES (?, ?, ?, ?, ?)
    """, (patient_name, doctor_name, treatment, amount, bill_date))

    conn.commit()
    conn.close()

    return redirect('/admin?section=billing')

@app.route('/cancel_absent_appointments', methods=['POST'])
def cancel_absent_appointments():

    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()

    # Find absent doctors
    cursor.execute("SELECT name FROM doctors WHERE status='On Leave'")
    doctors = cursor.fetchall()

    for d in doctors:
        doctor_name = d[0]

        # Cancel today's appointments
        cursor.execute("""
        UPDATE appointments
        SET status='Cancelled'
        WHERE doctor_name=? AND date=DATE('now')
        """, (doctor_name,))

    conn.commit()
    conn.close()

    return redirect('/admin?section=appointments')

@app.route('/update_settings', methods=['POST'])
def update_settings():

    hospital_name = request.form['hospital_name']
    email = request.form['email']
    contact = request.form['contact']

    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO settings (hospital_name, email, contact)
        VALUES (?, ?, ?)
    """, (hospital_name, email, contact))

    conn.commit()
    conn.close()

    return redirect('/admin?section=settings')

@app.route('/update_doctor_status/<int:id>')
def update_doctor_status(id):

    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()

    cursor.execute("SELECT status, name FROM doctors WHERE id=?", (id,))
    doctor = cursor.fetchone()

    current_status = doctor[0]
    doctor_name = doctor[1]

    if current_status == "Available":
        new_status = "On Leave"
    else:
        new_status = "Available"

    cursor.execute(
        "UPDATE doctors SET status=? WHERE id=?",
        (new_status, id)
    )

    if new_status == "On Leave":
        cursor.execute(
            "UPDATE appointments SET status='Cancelled' WHERE doctor_name=?",
            (doctor_name,)
        )
    elif new_status == "Available":
        cursor.execute(
        "UPDATE appointments SET status='Scheduled' WHERE doctor_name=? AND status='Cancelled'",
        (doctor_name,)
    )
    conn.commit()
    conn.close()

    return redirect('/admin?section=doctors')

@app.route('/patient')
def patient():
    if 'role' in session and session['role'] == 'patient':
        return render_template('patient.html', name=session['name'])
    return redirect('/login')

@app.route('/doctor/view_appointment/<int:id>', methods=['GET'])
def view_appointment(id):
    if 'role' not in session or session['role'] != 'doctor':
        return redirect('/login')

    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM appointments WHERE id=?", (id,))
    appointment = cursor.fetchone()

    if not appointment:
        return "Appointment not found"

    cursor.execute("SELECT * FROM patients WHERE name=?", (appointment[1],))
    patient = cursor.fetchone()

    cursor.execute("SELECT * FROM doctors WHERE name=?", (appointment[2],))
    doctor = cursor.fetchone()

    conn.close()

    return render_template(
        'view_appointment.html', 
        appointment=appointment,
        patient=patient,
        doctor=doctor
    )
@app.route('/doctor/edit_appointment/<int:id>', methods=['GET', 'POST'])
def edit_appointment(id):
    if 'role' not in session or session['role'] != 'doctor':
        return redirect('/login')

    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()

    cursor.execute("""
     SELECT a.*, d.gender, d.blood_group, d.phone, d.disease, d.previous_treatment
       FROM appointments a
       LEFT JOIN appointment_details d 
       ON a.id = d.appointment_id
       WHERE a.id=?
       """, (id,))

    appointment = cursor.fetchone()

    cursor.execute("SELECT * FROM doctors")
    doctors = cursor.fetchall()

    if request.method == 'POST':
       
        patient_name = request.form['patient_name']
        doctor_name = request.form['doctor_name']
        date = request.form['date']
        time = request.form['time']

        cursor.execute("""
            UPDATE appointments 
            SET patient_name=?, doctor_name=?, date=?, time=?
            WHERE id=?
        """, (patient_name, doctor_name, date, time, id))

        conn.commit()
        conn.close()

        return redirect('/doctor?section=appointments')

    conn.close()
    return render_template('edit_appointment.html', appointment=appointment, doctors=doctors)

@app.route('/doctor/update_appointment_status/<int:id>', methods=['POST'])
def update_appointment_status(id):
    if 'role' not in session or session['role'] != 'doctor':
        return redirect('/login')

    conn = sqlite3.connect('hospital.db')
    cursor = conn.cursor()

    status = request.form['status']
    next_date = request.form.get('next_date', None)  

    if status == 'Pending' and next_date:
        cursor.execute("""
            UPDATE appointments 
            SET status=?, date=? 
            WHERE id=?
        """, (status, next_date, id))
    else:
        cursor.execute("""
            UPDATE appointments 
            SET status=? 
            WHERE id=?
        """, (status, id))

    conn.commit()
    conn.close()

    return redirect('/doctor?section=appointments')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)