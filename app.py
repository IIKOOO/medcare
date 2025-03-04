from flask import Flask, render_template, request, jsonify, redirect, send_file, session
import cx_Oracle
import io
import csv
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'secret'

username = 'softeng'
password = '00000'
dsn = 'localhost/XE'

def get_db_connection():
    connection = cx_Oracle.connect(username, password, dsn)
    return connection

@app.route('/')
def login_choice():
    return render_template('login_choice.html')

@app.route('/login_nurse')
def login_nurse():
    return render_template('login_nurse.html')

@app.route('/login_student')
def login_student():
    return render_template('login_student.html')

@app.route('/login_admin')
def login_admin():
    return render_template('login_admin.html')  

@app.route('/nurse_main', methods=['GET'])
def nurse_main():
    school_year = request.args.get('school_year')
    search_name = request.args.get('search_name')

    connection = get_db_connection()
    cursor = connection.cursor()

    query = "SELECT id, full_name, school_year FROM student_files WHERE 1=1"
    params = {}

    if school_year:
        query += " AND school_year = :school_year"
        params['school_year'] = school_year

    if search_name:
        query += " AND full_name LIKE :search_name"
        params['search_name'] = f"%{search_name}%"

    cursor.execute(query, params)
    students = [{'id': row[0], 'full_name': row[1], 'school_year': row[2]} for row in cursor.fetchall()]

    cursor.close()
    connection.close()

    return render_template('nurse_main.html', students=students)

@app.route('/student_main')
def student_main():
    student_info = session.get('student_info', {})
    full_name = student_info.get('full_name')

    description = ""
    sched_date = ""
    sched_time = ""

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT description FROM student_files WHERE full_name = :full_name", {'full_name': full_name})
    row = cursor.fetchone()
    if row:
        description = row[0]

    if not description:
        cursor.execute("SELECT description FROM approved WHERE full_name = :full_name", {'full_name': full_name})
        row = cursor.fetchone()
        if row:
            description = row[0]

    if not description:
        cursor.execute("SELECT description FROM pending WHERE full_name = :full_name", {'full_name': full_name})
        row = cursor.fetchone()
        if row:
            description = row[0]

    cursor.execute("SELECT sched_date, sched_time FROM schedules WHERE full_name = :full_name", {'full_name': full_name})
    schedule_row = cursor.fetchone()
    if schedule_row:
        sched_date = schedule_row[0].strftime('%Y-%m-%d') if schedule_row[0] else ""
        sched_time = schedule_row[1] if schedule_row[1] else ""

    cursor.close()
    connection.close()

    return render_template('student_main.html', student_info=student_info, description=description, sched_date=sched_date, sched_time=sched_time)

@app.route('/admin_main')
def admin_main():
    connection = get_db_connection()
    cursor = connection.cursor()
    
    cursor.execute("SELECT * FROM student_login")
    students = [{'account_id': row[0], 'email': row[1], 'password': row[2], 'fullname': row[3], 'school_year': row[4], 'student_id': row[5], 'is_active': bool(row[6])} for row in cursor.fetchall()]

    cursor.execute("SELECT * FROM nurse_login")
    nurses = [{'account_id': row[0], 'email': row[1], 'password': row[2], 'is_active': bool(row[3])} for row in cursor.fetchall()]

    cursor.close()
    connection.close()
    return render_template('admin_main.html', students=students, nurses=nurses)

@app.route('/schedule')
def schedule():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT id, full_name, school_year, student_id, sched_date, sched_time FROM schedules")
    schedules = [{'id': row[0], 'full_name': row[1], 'school_year': row[2], 'student_id': row[3], 'sched_date': row[4], 'sched_time': row[5]} for row in cursor.fetchall()]

    cursor.close()
    connection.close()

    return render_template('schedule.html', schedules=schedules)

@app.route('/login', methods=['POST'])
def login():
    email = request.json.get('email')
    password = request.json.get('password')
    role = request.json.get('role')
    
    connection = get_db_connection()
    cursor = connection.cursor()

    user = None
    is_active = None

    if role == 'nurse':
        cursor.execute("""
            SELECT * 
            FROM nurse_login 
            WHERE email = :email AND password = :password
        """, {'email': email, 'password': password})
        user = cursor.fetchone()
        is_active = user[3] if user else None

    elif role == 'student':
        cursor.execute("""
            SELECT * 
            FROM student_login 
            WHERE email = :email AND password = :password
        """, {'email': email, 'password': password})
        user = cursor.fetchone()
        is_active = user[6] if user else None

        if user and is_active:
            session['student_info'] = {
                'full_name': user[3],
                'school_year': user[4],
                'student_id': user[5]
            }

    elif role == 'admin':
        cursor.execute("""
            SELECT * 
            FROM admin_login 
            WHERE email = :email AND password = :password
        """, {'email': email, 'password': password})
        user = cursor.fetchone()
        is_active = True  

    cursor.close()
    connection.close()

    if user:
        if is_active:
            return jsonify({'success': True, 'role': role})
        else:
            return jsonify({'success': False, 'message': 'Account is deactivated'})
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'})

@app.route('/upload', methods=['POST'])
def upload_file():
    full_name = request.form['full_name']
    school_year = request.form['school_year']
    student_id = request.form['student_id']
    lab_result_file = request.files.get('lab_result_file')
    med_cert_file = request.files.get('med_cert_file')

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT 'student_files' AS table_name FROM student_files WHERE full_name = :full_name
        UNION ALL
        SELECT 'approved' AS table_name FROM approved WHERE full_name = :full_name
        UNION ALL
        SELECT 'pending' AS table_name FROM pending WHERE full_name = :full_name
    """, {'full_name': full_name})
    match = cursor.fetchone()

    if match:
        table_name = match[0]
        if lab_result_file:
            lab_result_data = lab_result_file.read()
            cursor.execute(f"""
                UPDATE {table_name} 
                SET school_year = :school_year, lab_result = :lab_result 
                WHERE full_name = :full_name
            """, {
                'school_year': school_year,
                'lab_result': lab_result_data,
                'full_name': full_name
            })

        if med_cert_file:
            cursor.execute(f"SELECT lab_result FROM {table_name} WHERE full_name = :full_name", {'full_name': full_name})
            lab_result = cursor.fetchone()

            if lab_result and lab_result[0]:
                med_cert_data = med_cert_file.read()
                cursor.execute(f"""
                    UPDATE {table_name} 
                    SET med_cert = :med_cert 
                    WHERE full_name = :full_name
                """, {
                    'med_cert': med_cert_data,
                    'full_name': full_name
                })
            else:
                return jsonify({'success': False, 'message': 'You must upload a lab result before uploading a medical certificate.'})

    else:
        if lab_result_file:
            cursor.execute("""
                INSERT INTO student_files (full_name, school_year, lab_result, med_cert, description, student_id) 
                VALUES (:full_name, :school_year, :lab_result, :med_cert, NULL, :student_id)
            """, {
                'full_name': full_name,
                'school_year': school_year,
                'lab_result': lab_result_file.read(),
                'med_cert': med_cert_file.read() if med_cert_file else None,
                'student_id': student_id
            })
        else:
            return jsonify({'success': False, 'message': 'You must upload a lab result first.'})

    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({'success': True, 'message': 'Upload successful!'})

@app.route('/get_student_files/<int:student_id>', methods=['GET'])
def get_student_files(student_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    
    cursor.execute("""
        SELECT lab_result, med_cert 
        FROM student_files 
        WHERE id = :student_id
    """, {'student_id': student_id})
    row = cursor.fetchone()

    lab_result = bool(row[0]) 
    med_cert = bool(row[1])  

    cursor.close()
    connection.close()

    return jsonify({'lab_result': lab_result, 'med_cert': med_cert})

from flask import Flask, send_file, jsonify
import io

@app.route('/display_file/<int:student_id>/<file_type>/<table>', methods=['GET'])
def display_file(student_id, file_type, table):
    connection = get_db_connection()
    cursor = connection.cursor()

    if table == 'approved':
        table_name = 'approved'
    elif table == 'pending':
        table_name = 'pending'
    else:
        table_name = 'student_files'

    if file_type == 'lab_result':
        cursor.execute(f"SELECT lab_result FROM {table_name} WHERE id = :student_id", {'student_id': student_id})
    elif file_type == 'med_cert':
        cursor.execute(f"SELECT med_cert FROM {table_name} WHERE id = :student_id", {'student_id': student_id})
    else:
        cursor.close()
        connection.close()
        return jsonify({'error': 'Invalid file type'}), 400

    row = cursor.fetchone()
    file_data = row[0] if row else None

    if file_data:
        file_bytes = file_data.read()
        cursor.close()
        connection.close()
        return send_file(
            io.BytesIO(file_bytes),
            mimetype='application/pdf',
            as_attachment=False,
            download_name=f'{file_type}.pdf'
        )
    else:
        cursor.close()
        connection.close()
        return jsonify({'error': 'File not found'}), 404
    
@app.route('/upload_comment/<int:student_id>', methods=['POST'])
def upload_comment(student_id):
    data = request.json
    comment = data.get('comment')
    table = data.get('table')

    connection = get_db_connection()
    cursor = connection.cursor()

    if table == 'approved':
        cursor.execute("""
            UPDATE approved 
            SET description = :description 
            WHERE id = :student_id
        """, {
            'description': comment,
            'student_id': student_id
        })
    elif table == 'pending':
        cursor.execute("""
            UPDATE pending 
            SET description = :description 
            WHERE id = :student_id
        """, {
            'description': comment,
            'student_id': student_id
        })
    elif table == 'student_files':
        cursor.execute("""
            UPDATE student_files 
            SET description = :description 
            WHERE id = :student_id
        """, {
            'description': comment,
            'student_id': student_id
        })
    else:
        return jsonify({'success': False, 'message': 'Invalid table specified.'}), 400

    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({'success': True})


@app.route('/move_to_approved/<int:student_id>', methods=['POST'])
def move_to_approved(student_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM pending WHERE id = :student_id", {'student_id': student_id})
    student_record = cursor.fetchone()

    if student_record:
        cursor.execute("""
            INSERT INTO approved (id, full_name, school_year, lab_result, description, med_cert) 
            VALUES (:id, :full_name, :school_year, :lab_result, :description, :med_cert)
        """, {
            'id': student_record[0],
            'full_name': student_record[1],
            'school_year': student_record[2],
            'lab_result': student_record[3],
            'description': student_record[4],
            'med_cert': student_record[5]
        })

        cursor.execute("DELETE FROM pending WHERE id = :student_id", {'student_id': student_id})
    
    else:
        cursor.execute("SELECT * FROM student_files WHERE id = :student_id", {'student_id': student_id})
        student_record = cursor.fetchone()

        if student_record:
            cursor.execute("""
                INSERT INTO approved (id, full_name, school_year, lab_result, description, med_cert) 
                VALUES (:id, :full_name, :school_year, :lab_result, :description, :med_cert)
            """, {
                'id': student_record[0],
                'full_name': student_record[1],
                'school_year': student_record[2],
                'lab_result': student_record[3],
                'description': student_record[4],
                'med_cert': student_record[5]
            })

            cursor.execute("DELETE FROM student_files WHERE id = :student_id", {'student_id': student_id})

    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({'success': True})


@app.route('/move_to_pending/<int:student_id>', methods=['POST'])
def move_to_pending(student_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM approved WHERE id = :student_id", {'student_id': student_id})
    student_record = cursor.fetchone()

    if student_record:
        cursor.execute("""
            INSERT INTO pending (id, full_name, school_year, lab_result, description, med_cert) 
            VALUES (:id, :full_name, :school_year, :lab_result, :description, :med_cert)
        """, {
            'id': student_record[0],
            'full_name': student_record[1],
            'school_year': student_record[2],
            'lab_result': student_record[3],
            'description': student_record[4],
            'med_cert': student_record[5]
        })

        cursor.execute("DELETE FROM approved WHERE id = :student_id", {'student_id': student_id})

    else:
        cursor.execute("SELECT * FROM student_files WHERE id = :student_id", {'student_id': student_id})
        student_record = cursor.fetchone()

        if student_record:
            cursor.execute("""
                INSERT INTO pending (id, full_name, school_year, lab_result, description, med_cert) 
                VALUES (:id, :full_name, :school_year, :lab_result, :description, :med_cert)
            """, {
                'id': student_record[0],
                'full_name': student_record[1],
                'school_year': student_record[2],
                'lab_result': student_record[3],
                'description': student_record[4],
                'med_cert': student_record[5]
            })

            cursor.execute("DELETE FROM student_files WHERE id = :student_id", {'student_id': student_id})

    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({'success': True})

@app.route('/approved', methods=['GET'])
def approved():
    school_year = request.args.get('school_year')
    search_name = request.args.get('search_name')

    connection = get_db_connection()
    cursor = connection.cursor()

    query = "SELECT id, full_name, school_year FROM approved WHERE 1=1"
    params = {}

    if school_year:
        query += " AND school_year = :school_year"
        params['school_year'] = school_year

    if search_name:
        query += " AND full_name LIKE :search_name"
        params['search_name'] = f"%{search_name}%"

    cursor.execute(query, params)
    approved_students = [{'id': row[0], 'full_name': row[1], 'school_year': row[2]} for row in cursor.fetchall()]

    cursor.close()
    connection.close()

    return render_template('approved.html', students=approved_students)

@app.route('/pending', methods=['GET'])
def pending():
    school_year = request.args.get('school_year')
    search_name = request.args.get('search_name')

    connection = get_db_connection()
    cursor = connection.cursor()

    query = "SELECT id, full_name, school_year FROM pending WHERE 1=1"
    params = {}

    if school_year:
        query += " AND school_year = :school_year"
        params['school_year'] = school_year

    if search_name:
        query += " AND full_name LIKE :search_name"
        params['search_name'] = f"%{search_name}%"

    cursor.execute(query, params)
    pending_students = [{'id': row[0], 'full_name': row[1], 'school_year': row[2]} for row in cursor.fetchall()]

    cursor.close()
    connection.close()

    return render_template('pending.html', students=pending_students)

@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    file = request.files['csv_file']
    table = request.form['table']
    connection = get_db_connection()
    cursor = connection.cursor()

    csv_file = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
    reader = csv.reader(csv_file)
    next(reader)

    if table == 'student_login':
        for row in reader:
            account_id, email, password, fullname, school_year, student_id = row
            cursor.execute("""
                MERGE INTO student_login USING dual 
                ON (account_id = :account_id)
                WHEN MATCHED THEN 
                    UPDATE SET email = :email, password = :password, fullname = :fullname, 
                               school_year = :school_year, student_id = :student_id
                WHEN NOT MATCHED THEN 
                    INSERT (account_id, email, password, fullname, school_year, student_id) 
                    VALUES (:account_id, :email, :password, :fullname, :school_year, :student_id)
            """, {
                'account_id': account_id,
                'email': email,
                'password': password,
                'fullname': fullname,
                'school_year': school_year,
                'student_id': student_id
            })
    elif table == 'nurse_login':
        for row in reader:
            account_id, email, password = row
            cursor.execute("""
                MERGE INTO nurse_login USING dual 
                ON (account_id = :account_id)
                WHEN MATCHED THEN 
                    UPDATE SET email = :email, password = :password
                WHEN NOT MATCHED THEN 
                    INSERT (account_id, email, password) 
                    VALUES (:account_id, :email, :password)
            """, {
                'account_id': account_id,
                'email': email,
                'password': password
            })

    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({'success': True})


@app.route('/modify_user', methods=['POST'])
def modify_user():
    data = request.json
    table = data['table']
    operation = data['operation']
    
    connection = get_db_connection()
    cursor = connection.cursor()

    if operation == 'delete':
        cursor.execute(f"DELETE FROM {table} WHERE account_id = :account_id", {'account_id': data['account_id']})
    elif operation == 'update':
        cursor.execute(f"UPDATE {table} SET email = :email, password = :password, fullname = :fullname, school_year = :school_year, student_id = :student_id WHERE account_id = :account_id", data)
    elif operation == 'add':
        cursor.execute(f"INSERT INTO {table} (account_id, email, password, fullname, school_year) VALUES (:account_id, :email, :password, :fullname, :school_year, student_id = :student_id)", data)
    
    connection.commit()
    cursor.close()
    connection.close()
    return jsonify({'success': True})

@app.route('/set_schedule', methods=['POST'])
def set_schedule():
    if request.method == 'POST':
        student_full_name = request.form['student_name']
        student_school_year = request.form['student_school_year']
        student_id = request.form['student_id']
        sched_date = request.form['sched_date']
        sched_time = request.form['sched_time']

        sched_date = datetime.strptime(sched_date, '%Y-%m-%d')

        print(f"Scheduling: {student_full_name} ({student_id}) for {sched_date} at {sched_time}")

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT student_id FROM student_files WHERE full_name = :full_name", {'full_name': student_full_name})
        student_record = cursor.fetchone()
        if not student_record:
            cursor.execute("SELECT student_id FROM approved WHERE full_name = :full_name", {'full_name': student_full_name})
            student_record = cursor.fetchone()
        if not student_record:
            cursor.execute("SELECT student_id FROM pending WHERE full_name = :full_name", {'full_name': student_full_name})
            student_record = cursor.fetchone()
        
        if student_record:
            student_id = student_record[0]

            cursor.execute('''
                SELECT * FROM schedules WHERE full_name = :full_name
            ''', {'full_name': student_full_name})
            existing_schedule = cursor.fetchone()

            if existing_schedule:
                cursor.execute('''
                    UPDATE schedules
                    SET sched_time = :sched_time, sched_date = :sched_date
                    WHERE full_name = :full_name
                ''', {
                    'sched_time': sched_time,
                    'sched_date': sched_date,
                    'full_name': student_full_name
                })
                connection.commit()
                print(f"Updated schedule for {student_full_name} to {sched_time} on {sched_date}.")
            else:
                cursor.execute('''
                    INSERT INTO schedules (full_name, school_year, student_id, sched_date, sched_time)
                    VALUES (:full_name, :school_year, :student_id, :sched_date, :sched_time)
                ''', {
                    'full_name': student_full_name,
                    'school_year': student_school_year,
                    'student_id': student_id,
                    'sched_date': sched_date,
                    'sched_time': sched_time
                })
                connection.commit()
                print(f"Inserted new schedule for {student_full_name} on {sched_date} at {sched_time}.")

            cursor.close()
            connection.close()

            return jsonify({'success': True, 'message': 'Schedule set successfully!'}), 200
        else:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'message': 'Student ID not found.'}), 404
        
        
@app.route('/download_schedules', methods=['GET'])
def download_schedules():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT id, full_name, school_year, student_id, sched_date, sched_time FROM schedules")
    schedules = cursor.fetchall()
    cursor.close()
    connection.close()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['Schedule ID', 'Full Name', 'School Year','Student ID', 'Schedule Date', 'Schedule Time'])

    for row in schedules:
        writer.writerow([
            row[0],
            row[1],
            row[2],
            row[3],
            row[4].strftime('%Y-%m-%d') if row[3] else '',
            row[5]
        ])
    
    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='Student schedules.csv'
    )

@app.route('/toggle_account_status', methods=['POST'])
def toggle_account_status():
    data = request.json
    table = data['table']
    account_id = data['account_id']
    action = data['action']

    new_status = 1 if action == 'activate' else 0

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(f"UPDATE {table} SET is_active = :status WHERE account_id = :account_id", {
        'status': new_status,
        'account_id': account_id
    })

    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({'success': True, 'message': f'Account {action}d successfully'})
    
if __name__ == '__main__':
    app.run(debug=True)
