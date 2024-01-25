from flask import Flask, render_template, redirect, url_for, flash, request, session, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import datetime
import time
import re

app = Flask(__name__)
app.secret_key = '3d6f45a5fc12445dbac2f59c3b6c7cb1'
app.config[
    'SQLALCHEMY_DATABASE_URI'] = 'mssql+pyodbc://SA:Wer0820_@localhost/METZ?driver=ODBC+Driver+17+for+SQL+Server'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['Pictures'] = '/Users/alexeydubovik/PycharmProjects/METZApplicationApp/Pictures'
Session(app)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    tab_number = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.NVARCHAR(None), nullable=False)
    inventory_number = db.Column(db.String(20), nullable=False)
    photo = db.Column(db.String(100))
    status = db.Column(db.Integer)
    latest_valubale_date = db.Column(db.DATETIME())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


def save_photo(photo):
    if photo.filename != '':
        filename = str(time.time()) + ".jpg"
        photo.save(os.path.join(app.config['Pictures'], filename))
        return filename
    return None


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def hello_world():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        tab_number = request.form['tab_number']
        password = request.form['password']
        user = User.query.filter_by(tab_number=tab_number).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Вы успешно вошли в систему!', 'success')
            return redirect(url_for('application'))
        else:
            flash('Неверный табельный номер или пароль', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        tab_number = request.form['tab_number']
        password = request.form['password']

        # Validate tab number
        if not re.match(r'^\d{5,6}$', tab_number):
            flash('Табельный номер должен содержать от 5 до 6 цифр', 'danger')
            return redirect(url_for('register'))

        # Validate passwor

        # Check if user with the same tab number already exists
        existing_user = User.query.filter_by(tab_number=tab_number).first()
        if existing_user:
            flash('Пользователь с таким табельным номером уже существует', 'danger')
            return redirect(url_for('register'))

        # Create a new user
        new_user = User(tab_number=tab_number)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Вы успешно зарегистрированы! Теперь вы можете войти', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/pictures/<filename>')
def get_picture(filename):
    return send_from_directory('Pictures', filename, as_attachment=True)


@app.route('/application', methods=['GET', 'POST'])
@login_required
def application():
    if request.method == 'POST':
        description = request.form['description']
        inventory_number = request.form['inventory_number']
        photo = None

        # Validate inventory number
        if not re.match(r'^\d{5,8}$', inventory_number):
            flash('Инвентарный номер должен содержать от 5 до 8 цифр', 'danger')
            return redirect(url_for('application'))

        if 'photo' in request.files:
            photo = save_photo(request.files['photo'])

        # Создаем новую заявку
        new_application = Application(
            description=description,
            inventory_number=inventory_number,
            photo=photo,
            user_id=current_user.id,
            status=0
        )
        db.session.add(new_application)
        db.session.commit()

        flash('Заявка успешно отправлена!', 'success')
        return redirect(url_for('application'))

    return render_template('application.html')


@app.route('/mark_as_done/<int:application_id>', methods=['POST'])
@login_required
def mark_as_done(application_id):
    application = Application.query.get(application_id)
    if application and application.status == 2:
        application.status = 3
        application.latest_valubale_date = datetime.datetime.now()
        db.session.commit()
    return redirect(url_for('profile'))


@app.route('/profile')
@login_required
def profile():
    user = current_user
    result = db.session.query(Application).filter_by(user_id=current_user.id).all()
    return render_template('profile.html', user=user, applications=result)


if __name__ == '__main__':
    app.run(debug=True)