from os.path import join, dirname, abspath
from flask import Flask, request, render_template, redirect, session
from flask_session import Session
from database import Database


app = Flask(__name__)

# Configure session.
app.config['SESSION_PERMENENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Temp dictionary to hold usernames and passwords. To be replaced with a SQL database.
# USERS = {'Mahmoud Hussein': 'admin1234', 'Test': 'Test'}

# Configure database.
db_file = "database.db"
db = Database(db_file)

# Prices of items in stock.
# PRICES = {'item1': 10, 'item2': 5}

# Configure photo upload and save.
UPLOAD_FOLDER = join(dirname(abspath(__file__)), 'photos')
# ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'heif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/')
def index():
    '''Define the default route.'''
    # If no user is logged in, redirect to login page.
    if not session.get('id'):
        return redirect('/login')

    # Get user's data.
    user_data = db.select(session.get('id'))

    return render_template('index.html', user_data=user_data)


@app.route('/login', methods=['GET', 'POST'])
def login():
    '''Define the login route.'''
    if request.method == 'POST':
        if check_login_form(request):
            # User submitted the form correctly.
            username = request.form.get('username')
            password = request.form.get('password')

            # Get all rows from db.
            rows = db.select_all()

            # If user is in database, log them in.
            for row in rows:
                if username == row['username'] and password == row['password']:
                    # Add user to session and redirect to homepage.
                    session['id'] = row['id']
                    return redirect('/')

            # User is not registered.
            return render_template('login.html', msg='User is not registerd.')
        else:
            return render_template('login.html', msg='Please, enter data correctly.')

    # GET request.
    if not session.get('id'):  # If user is not logged in.
        return render_template('login.html')
    else:
        # User already logged in.
        return redirect('/')


@app.route('/logout')
def logout():
    '''Define logout route.'''
    # Remove user from session.
    session['id'] = None
    return redirect('/')


@app.route('/register', methods=['POST', 'GET'])
def register():
    """ Define the register route. """
    if request.method == 'POST':
        rows = db.select_all()
        # Check no missing data from the from.
        if check_register_form(request):
            username = request.form.get('username')
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm')
            photo = request.files['photo']

            # Confirm password is entered correctly.
            if password != confirm_password:
                return render_template('register.html', msg="Enter password correctly.")
            # Make sure username and email don't already exist.
            for row in rows:
                if username == row['username']:
                    return render_template('register.html', msg='Username already exists!')
                if email == row['email']:
                    return render_template('register.html', msg='Email already exists!')

            # Insert new user data in database.
            new_id = db.insert((username, name, email, password))

            # Change the name of the photo.
            photo.filename = str(new_id) + '.' + photo.filename.rsplit('.', 1)[1].lower()

            # Save photo.
            photo.save(join(app.config['UPLOAD_FOLDER'], photo.filename))

            # Login the user and redirect to homepage.
            session['id'] = new_id
            return redirect('/')

        else:
            # Form is missing data.
            return render_template('register.html', msg="Please, fill in all data fields.")

    # GET request.
    if not session.get('id'):
        return render_template('register.html')
    else:
        return redirect('/')


USER_ID = None  # id of user standing in front of the camera.


@app.route('/_face_id')
def face_id():
    """ Handle requests from face_id program. """
    global USER_ID
    if request.args.get('id'):
        user_data = db.select(request.args.get('id'))
        USER_ID = user_data['id']
        print(f"Hello, {user_data['name']}")
    else:
        USER_ID = None
        print(None)
    return ('', 204)


@app.route('/_node_mcu')
def node_mcu():
    """ Handle requests from NodeMCU. """
    msg = request.args.get('msg')
    print(f"msg: {msg}")
    price = 55
    # If no user recognized respond with error code.
    if USER_ID is None:
        return ('Error', 503)

    if msg == '1':
        # User bought an item.
        new_balance = db.select(USER_ID)['balance'] - price

    elif msg == "-1":
        # User returned an item.
        new_balance = db.select(USER_ID)['balance'] + price

    db.update(USER_ID, new_balance)
    return ('OK', 200)


def check_login_form(req):
    """ Make sure that the user submitted the form correctly. """
    # Check for username and password.
    return all(req.form.get(i) for i in ['username', 'password'])


def check_register_form(req):
    """ Make sure the user submitted the form correctly. """
    return all([req.form.get(i) for i in ['username', 'name', 'email', 'password', 'confirm']]) and 'photo' in req.files


# def allowed_file(filename):
#     return '.' in filename and \
#            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
