import os
import datetime
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash
from flask_bcrypt import Bcrypt

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.config.from_object(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'flaskr.db'),
    SECRET_KEY='dogeface'
))
app.config.from_envvar('FLASKR_SETTINGS', silent=True)

def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv

def init_db():
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()

@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    init_db()
    print('Initialized the database.')

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

@app.route('/')
def home():
    session.clear()
    return render_template('login.html')

@app.route('/admin')
def admin():
    session['back'] = False
    db = get_db()
    cur = db.execute('select username, password from users order by id desc')
    users = cur.fetchall()
    return render_template('admin.html', users=users)

@app.route('/security')
def security():
    session['back'] = False
    return render_template('security.html')

@app.route('/worker')
def worker():
    session['back'] = False
    return render_template('worker.html')

@app.route('/profile', methods=['POST', 'GET'])
def profile():
    error = None
    admin = None
    security = None
    worker = None
    session['back'] = True
    if request.method == 'POST':
        db = get_db()
        cur = db.execute('select username from users order by id desc')
        users = cur.fetchall()
        for row in users:
            if row[0] == request.form['username']:
                error = 'invalid username'
                db.commit()
                return render_template('profile.html', error=error)
        if request.form['type'] == "admin":
            admin = "1"
            security = "0"
            worker = "0"
        elif request.form['type'] == "security":
            admin = "0"
            security = "1"
            worker = "0"
        else:
            admin = "0"
            security = "0"
            worker = "1"
        db.execute('insert into users (username, password, admin, security, worker) values (?, ?, ?, ?, ?)',
            [request.form['username'], bcrypt.generate_password_hash(request.form['password']).decode('utf-8'), admin, security, worker])
        db.commit()
        flash('New user was successfully added')
        session['back'] = False
        return redirect(url_for('admin'))
    return render_template('profile.html', error=error)

@app.route('/login', methods=['POST'])
def login():
    db = get_db()
    cur = db.execute('select username, password, admin, security, worker from users order by id desc')
    users = cur.fetchall()
    for row in users:
        if row[0] == request.form['username'] and bcrypt.check_password_hash(row[1], request.form['password']):
            if row[2] == "1":
                db.commit()
                session['admin'] = True
                flash('You were logged in')
                return redirect(url_for('admin'))
            elif row[3] == "1":
                db.commit()
                session['security'] = True
                return redirect(url_for('security'))
            else:
                db.commit()
                session['worker'] = True
                return redirect(url_for('worker'))
        elif row[0] == request.form['username'] and not bcrypt.check_password_hash(row[1], request.form['password']):
            db.commit()
            error = 'invalid password'
            return render_template('login.html', error=error)
    db.commit()
    error = 'invalid username'
    return render_template('login.html', error=error)

@app.route('/register', methods=['POST', 'GET'])
def register():
    error = None
    levels = []
    viable = ['visitor', 'employee']
    session['back'] = True
    if request.method == 'POST':
        if request.form['access'] not in viable:
            error = 'invalid access level'
            return render_template('register.html', error=error)
        db = get_db()
        cur = db.execute('select numID from visitors order by id desc')
        visitors = cur.fetchall()
        for row in visitors:
            if row[0] == request.form['number']:
                error = 'duplicate personal ID'
                return render_template('register.html', error=error)
        db.execute('insert into visitors (firstName, lastName, regTimestamp, image, idNum, access) values (?, ?, ?, ?, ?, ?)',
            [request.form['firstname'], request.form['lastname'], '{:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now()), request.form['image'], request.form['number']], request.form['access'])
        if request.form['access'] == 'visitor':
            levels = ['1', '0']
        elif request.form['access'] == 'employee':
            levels = ['1', '1']
        db.execute('insert into levels (idNum, access) values (?, ?)', [request.form['number'], levels])
        db.commit()
        flash('New visitor was successfully added')
        session['back'] = False
        return redirect(url_for('worker'))
    return render_template('register.html', error=error)

@app.route('/searchfirst', methods=['POST', 'GET'])
def search_first():
    session['back'] = True
    if request.method == 'POST':
        db = get_db()
        cur = db.execute('select firstName, lastName, idNum, access from visitors order by id desc')
        vistors = cur.fetchall()
        vlist = []
        for row in vistors:
            if row[0] == request.form['firstName']:
                vlist.append(row)
                db.commit()
        return render_template('searchlist.html', users=vlist)
    return render_template('searchfirst.html')

@app.route('/searchlast', methods=['POST', 'GET'])
def search_last():
    session['back'] = True
    if request.method == 'POST':
        db = get_db()
        cur = db.execute('select firstName, lastName, idNum, access from visitors order by id desc')
        vistors = cur.fetchall()
        vlist = []
        for row in vistors:
            if row[1] == request.form['lastName']:
                vlist.append(row)
                db.commit()
        return render_template('searchlist.html', users=vlist)
    return render_template('searchlast.html')

@app.route('/searchnum', methods=['POST', 'GET'])
def search_num():
    session['back'] = True
    if request.method == 'POST':
        db = get_db()
        cur = db.execute('select firstName, lastName, idNum, access from visitors order by id desc')
        vistors = cur.fetchall()
        vlist = []
        for row in vistors:
            if row[2] == request.form['number']:
                vlist.append(row)
                db.commit()
        return render_template('searchlist.html', users=vlist)
    return render_template('searchnum.html')

@app.route('/searchlist', methods=['POST'])
def search_list():
    return render_template('searchlist.html')
