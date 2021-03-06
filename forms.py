from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, FieldList, Form, FormField, FloatField, SelectField
from wtforms.validators import DataRequired, URL, Email
from flask_ckeditor import CKEditorField


# WTForm
class CreateTravelOffence(FlaskForm):
    plate_no = SelectField('Plate Number')
    replace_plate_no = StringField("Plate Number (If not above)")
    offence = SelectField('Traffic Offence')
    vehicle_type = StringField("Vehicle Type")
    # img_url = StringField("Blog Image URL", validators=[DataRequired(), URL()])
    body = CKEditorField("Comment", validators=[DataRequired()])
    submit = SubmitField("Submit Post")


class RegisterForm(FlaskForm):
    name = StringField("Full Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Register!")


class LoginForm(FlaskForm):
    # name = StringField("Full Name", validators=[DataRequired()])
    # email = StringField("Email", validators=[DataRequired(), Email()])
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log In!")


class CommentForm(FlaskForm):
    comment_text = CKEditorField("Comment", validators=[DataRequired()])
    submit = SubmitField("Submit Comment")


class SearchForm(FlaskForm):
    search_value = StringField("Enter Plate Number", validators=[DataRequired()])
    submit = SubmitField("Search")
