from flask import Flask, render_template, redirect, url_for, flash, abort, request, session
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from forms import CreateTravelOffence, RegisterForm, LoginForm, CommentForm, SearchForm
import os
from functools import wraps
from sqlalchemy.ext.declarative import declarative_base
# from werkzeug.utils import secure_filename
# from pprint import pprint

from os import listdir, replace, remove
from os.path import isfile, join, getsize
from PIL import Image
from modules.image_edit import EditImage, AllPaths
from modules.plate_recognizer import PlateRecognizer
import shutil

# import test_json

UPLOAD_FOLDER = 'static/vehicle-capture/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'jfif'}
# Register on https://platerecognizer.com/ to get your own token
TOKEN = os.environ.get('PLATE_RECOGIZER_TOKEN')

# Store all images in all path: True (False - Only store processed images in processed path)
STORE_IMAGES = False

all_paths = AllPaths()
upload_dir = all_paths.upload_path
append_username_to_image = True

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1000 * 1000
ckeditor = CKEditor(app)
Bootstrap(app)
login_manager = LoginManager()
login_manager.init_app(app)
Base = declarative_base()

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///tms_prototype.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

current_timestamp = datetime.now()


# pprint(os.environ)
# CONFIGURE TABLES

class Bookings(db.Model):
    __tablename__ = "traffic_bookings"
    id = db.Column(db.Integer, primary_key=True)
    officer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    officer = relationship("User", back_populates="booking_officer")
    offence_id = db.Column(db.Integer, db.ForeignKey("traffic_offence.id"), nullable=False)
    offence = relationship("Offence", back_populates="offence_booking")
    plate_no = db.Column(db.String(250), nullable=False)
    vehicle_type = db.Column(db.String(250), nullable=True)
    vehicle_model = db.Column(db.String(250), nullable=True)
    vehicle_make = db.Column(db.String(250), nullable=True)
    vehicle_color = db.Column(db.String(250), nullable=True)
    vehicle_orientation = db.Column(db.String(250), nullable=True)
    comment = db.Column(db.Text, nullable=True)
    img = db.Column(db.String(250), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    username = db.Column(db.String(250), unique=True, nullable=False)
    booking_officer = relationship("Bookings", back_populates="officer")
    password = db.Column(db.String(250), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False)


class Offence(db.Model):
    __tablename__ = "traffic_offence"
    id = db.Column(db.Integer, primary_key=True)
    offence_name = db.Column(db.String(250), nullable=False)
    offence_booking = relationship("Bookings", back_populates="offence")
    offence_desc = db.Column(db.Text, nullable=True)
    fees = db.Column(db.Float, nullable=False)
    date_created = db.Column(db.DateTime, nullable=False)


def authenticated_user(function):
    @wraps(function)
    def wrapper_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return abort(403)
        else:
            return function(*args, **kwargs)

    return wrapper_function


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Create all the tables in the database
db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user_name = form.username.data
        user = User.query.filter_by(username=user_name).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('capture_image'))
            else:
                flash('Password incorrect, try again')
                return redirect(url_for('login'))
        else:
            flash('The user does not exist.')
            return redirect(url_for('login'))

    return render_template("login.html", form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        user_name = form.username.data
        if User.query.filter_by(username=user_name).first():
            flash('User already registered, log in instead')
            return redirect(url_for('login'))
        else:
            new_user = User(
                name=form.name.data,
                email=form.email.data,
                username=user_name,
                password=generate_password_hash(form.password.data, method='pbkdf2:sha256', salt_length=8),
                date_created=current_timestamp
            )
            db.session.add(new_user)
            db.session.commit()

            # login_user(new_user)

            # return redirect(url_for("get_all_posts"))
            return redirect(url_for("login"))
    return render_template("register.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/offence', methods=['GET', 'POST'])
@authenticated_user
def capture_image():
    username = current_user.username
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('File not selected')
            return redirect(request.url)
        if file and allowed_file(file.filename):

            # filename = secure_filename(file.filename)
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            print(f'File uploaded successfully: {filename}')
            # print(filename)
            # print(file.filename)
            edit_image = EditImage(filename)

            file_path = f'{upload_dir}/{filename}'
            temp_file = edit_image.processing_file

            plate_recognizer = PlateRecognizer(filename, temp_file)

            # time.sleep(1.1)

            token = f'Token {TOKEN}'
            regions = ['ng']  # Change to your country

            file_size = getsize(file_path)
            one_mb_size = 1024 * 1024
            three_mb_size_limit = 3 * one_mb_size
            file_size_mb = round(file_size / one_mb_size, 2)
            is_image_resized = False

            print(f'Image Mame: {filename} | Image Size: {file_size_mb} MB')
            # print(file_path)

            # Checking image file size
            if file_size > three_mb_size_limit:
                # Resize image and copy into WIP folder
                img = Image.open(edit_image.uploaded_file)
                edit_image.resize_img(img)
                is_image_resized = True
            else:
                # Copy original image into WIP folder
                shutil.copy(edit_image.uploaded_file, edit_image.processing_file)

            plate_data = plate_recognizer.check_process_plate(regions, token)
            # plate_data = test_json.plate_data

            # Move processed file into processed dir
            if append_username_to_image:
                date_string = datetime.now().strftime("%Y%m%d-%H%M%S")
                new_filename = f'{username}_{date_string}_{filename}'
                replace(temp_file, f'{all_paths.processed_path}/{new_filename}')
            else:
                replace(temp_file, f'{all_paths.processed_path}/{filename}')

            # Move original resized file into original dir
            if is_image_resized and STORE_IMAGES:
                replace(file_path, f'{all_paths.original_file_path}/{filename}')
            else:
                remove(file_path)

            if not STORE_IMAGES:
                try:
                    remove(f'{all_paths.wip_path}/{filename}')
                    remove(f'{all_paths.upload_path}/{filename}')
                    remove(f'{all_paths.cropped_path}/{filename}')
                except FileNotFoundError:
                    pass

            session["plate_data"] = plate_data
            session["name"] = filename
            session["filename"] = new_filename
            return redirect(url_for('capture_offence'))
    return render_template("landing.html")


@app.route("/capture-details", methods=["GET", "POST"])
def capture_offence():
    plate_data = session.get("plate_data")
    processed_file = session.get("filename")

    image = f'{all_paths.processed_path}/{processed_file}'
    form = CreateTravelOffence()

    if request.method == 'POST':
        form.validate()
        offence_committed = Offence.query.filter_by(id=form.offence.data).first()

        if form.replace_plate_no.data:
            plate_num = form.replace_plate_no.data
        else:
            plate_num = form.plate_no.data

        new_offence = Bookings(
            officer=current_user,
            offence=offence_committed,
            plate_no=plate_num,
            vehicle_type=form.vehicle_type.data,
            vehicle_model='',
            vehicle_make='',
            vehicle_color='',
            vehicle_orientation='',
            comment='',
            img=image,
            date_created=datetime.now()
        )
        db.session.add(new_offence)
        db.session.commit()
        return redirect(url_for("capture_image"))

    form.plate_no.choices = [
        (row["plate"].upper(), row["plate"].upper() + ' / ' + str(round(row["score"] * 100, 2)) + '%') for row in
        plate_data["results"][0]["candidates"]]
    form.offence.choices = [
        (row.id, row.offence_name) for row in Offence.query.all()
    ]
    form.vehicle_type.data = plate_data["results"][0]["vehicle"]["type"]

    return render_template("post-offence.html", form=form, current_user=current_user, plate_data=plate_data,
                           image=image)


@app.route('/search', methods=["GET", "POST"])
def search_offence():
    search_form = SearchForm()
    if search_form.validate_on_submit():
        search_query = search_form.search_value.data
        # print(search_query)
        search_result = Bookings.query.filter_by(plate_no=search_query).all()
        list_of_rows = [
            ['Plate Number', 'Vehicle Type', 'Traffic Offence', 'Charge', 'Officer', 'Date Captured', 'Image Captured']]
        for row in search_result:
            new_row = [row.plate_no,
                       row.vehicle_type,
                       Offence.query.get(row.offence_id).offence_name,
                       "₦{:,.2f}".format(Offence.query.get(row.offence_id).fees),
                       User.query.get(row.officer_id).name,
                       row.date_created.strftime("%d-%b-%Y %I:%M:%S%p"),
                       row.img]
            list_of_rows.append(new_row)

        return render_template("search.html", form=search_form, result=list_of_rows, query=search_query)
    else:
        list_of_rows = [
            ['Plate Number', 'Vehicle Type', 'Traffic Offence', 'Charge', 'Officer', 'Date Captured', 'Image Captured']]
        query = Bookings.query.limit(20).all()
        for row in query:
            new_row = [row.plate_no,
                       row.vehicle_type,
                       Offence.query.get(row.offence_id).offence_name,
                       "₦{:,.2f}".format(Offence.query.get(row.offence_id).fees),
                       User.query.get(row.officer_id).name,
                       row.date_created.strftime("%d-%b-%Y %I:%M:%S%p"),
                       row.img]
            list_of_rows.append(new_row)

        return render_template("search.html", form=search_form, result=list_of_rows)


if __name__ == "__main__":
    app.run(host='localhost', port=5000, debug=True)
