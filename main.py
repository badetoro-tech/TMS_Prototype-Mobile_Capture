from flask import Flask, render_template, redirect, url_for, flash, abort, request, session
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date, datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
import os
from functools import wraps
from sqlalchemy.ext.declarative import declarative_base
from werkzeug.utils import secure_filename
from pprint import pprint
from os import listdir, replace, remove
from os.path import isfile, join, getsize
import time
from PIL import Image
from modules.image_edit import EditImage, AllPaths
from modules.plate_recognizer import PlateRecognizer
import shutil
from collections import namedtuple

UPLOAD_FOLDER = 'static/vehicle-capture/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'jfif'}
TOKEN = '8c7da83008dc52f30a4624fcaaf1d7c9912e69fc'

all_paths = AllPaths()
upload_dir = all_paths.upload_path

app = Flask(__name__)
# app.config['SECRET_KEY'] = os.urandom(16)
# app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['SECRET_KEY'] = '#RIFUiahfsdhio83F8D3'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ckeditor = CKEditor(app)
Bootstrap(app)
login_manager = LoginManager()
login_manager.init_app(app)
Base = declarative_base()
# gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False,
#                     base_url=None)

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///tms_prototype.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

current_timestamp = datetime.now()


# CONFIGURE TABLES

class Bookings(db.Model):
    __tablename__ = "traffic_bookings"
    id = db.Column(db.Integer, primary_key=True)
    officer_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    officer = relationship("User", back_populates="bookings")
    offence_id = db.Column(db.Integer, db.ForeignKey("traffic_offence.id"))
    offence = relationship("Offence", back_populates="booking")
    plate_no = db.Column(db.String(250), nullable=False)
    vehicle_type = db.Column(db.String(250), nullable=False)
    img = db.Column(db.String(250), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    username = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    bookings = relationship("Bookings", back_populates="officer")
    date_created = db.Column(db.DateTime, nullable=False)


class Offence(db.Model):
    __tablename__ = "traffic_offence"
    id = db.Column(db.Integer, primary_key=True)
    offence = db.Column(db.String(250), nullable=False)
    booking = relationship("Bookings", back_populates="offence")
    offence_desc = db.Column(db.Text, nullable=True)
    fees = db.Column(db.Float, nullable=False)
    date_created = db.Column(db.DateTime, nullable=False)


# class Fees(db.Model):
#     __tablename__ = "traffic_offence"
#     id = db.Column(db.Integer, primary_key=True)
#     offence_id = db.Column(db.Integer, db.ForeignKey("traffic_offence.id"))
#     offence = db.Column(db.String(250), nullable=False)
#     offence_desc = db.Column(db.Text, nullable=True)
#     enabled = db.Column(db.Boolean, nullable=False)
#     date_created = db.Column(db.Datetime, nullable=False)


def admin_only(function):
    @wraps(function)
    def wrapper_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.id != 1:
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


# @app.route('/')
# def get_all_posts():
#     posts = Bookings.query.all()
#     return render_template("index.html", all_posts=posts)

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


@app.route('/capture_image', methods=['GET', 'POST'])
def capture_image():
    # posts = Bookings.query.all()
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # print(filename)
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

            # Move processed file into processed dir
            replace(temp_file, f'{all_paths.processed_path}/{filename}')

            # Move original resized file into original dir
            if is_image_resized:
                replace(file_path, f'{all_paths.original_file_path}/{filename}')
            else:
                remove(file_path)

            print('********')
            print(plate_data)
            session["plate_data"] = plate_data
            session["name"] = filename
            return redirect(url_for('capture_offence', name=filename, plate_data=plate_data))
    return render_template("index.html")


@app.route("/capture-details", methods=["GET", "POST"])
def capture_offence():
    plate_data = session.get("plate_data")
    filename = session.get("name")
    print('^^^^^^^^^^^')
    print(plate_data)

    image = f'{all_paths.processed_path}/{filename}'

    form = CreatePostForm()
    form.plate_no.choices = [
        (row["plate"].upper(), row["plate"].upper() + ' / ' + str(round(row["score"] * 100, 2)) + '%') for row in
        plate_data["results"][0]["candidates"]]

    if form.validate_on_submit():
        new_post = Bookings(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, current_user=current_user, plate_data=plate_data, image=image)


#
# @app.route("/post/<int:post_id>", methods=['GET', 'POST'])
# def show_post(post_id):
#     form = CommentForm()
#     requested_post = Bookings.query.get(post_id)
#     if form.validate_on_submit():
#         comment = form.comment_text.data
#         if not current_user.is_authenticated:
#             flash('You need to login, or register to comment.')
#             return redirect(url_for('login'))
#         else:
#             new_comment = Comment(
#                 text=comment,
#                 comment_author=current_user,
#                 parent_post=requested_post
#             )
#             db.session.add(new_comment)
#             db.session.commit()
#
#             return redirect(url_for('show_post', post_id=post_id))
#
#     return render_template("post.html", post=requested_post, form=form, current_user=current_user)
#
#
# @app.route("/about")
# def about():
#     return render_template("about.html")
#
#
# @app.route("/contact")
# def contact():
#     return render_template("contact.html")
#
#
# @app.route("/new-post", methods=["GET", "POST"])
# @admin_only
# def add_new_post():
#     form = CreatePostForm()
#     if form.validate_on_submit():
#         new_post = Bookings(
#             title=form.title.data,
#             subtitle=form.subtitle.data,
#             body=form.body.data,
#             img_url=form.img_url.data,
#             author=current_user,
#             date=date.today().strftime("%B %d, %Y")
#         )
#         db.session.add(new_post)
#         db.session.commit()
#         return redirect(url_for("get_all_posts"))
#     return render_template("make-post.html", form=form, current_user=current_user)
#
#
# @app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
# @admin_only
# def edit_post(post_id):
#     post = Bookings.query.get(post_id)
#     edit_form = CreatePostForm(
#         title=post.title,
#         subtitle=post.subtitle,
#         img_url=post.img_url,
#         author=post.officer,
#         body=post.body
#     )
#     if edit_form.validate_on_submit():
#         post.title = edit_form.title.data
#         post.subtitle = edit_form.subtitle.data
#         post.img_url = edit_form.img_url.data
#         # post.officer = edit_form.officer.data
#         post.body = edit_form.body.data
#         db.session.commit()
#         return redirect(url_for("show_post", post_id=post.id))
#
#     return render_template("make-post.html", form=edit_form, current_user=current_user)
#
#
# @app.route("/delete/<int:post_id>")
# @admin_only
# def delete_post(post_id):
#     post_to_delete = Bookings.query.get(post_id)
#     db.session.delete(post_to_delete)
#     db.session.commit()
#     return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='192.168.100.5', port=5000, debug=True)
