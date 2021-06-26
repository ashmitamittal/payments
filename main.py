from flask import Flask, render_template, request, url_for, redirect, flash, send_from_directory
from sqlalchemy import desc
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
import datetime

app = Flask(__name__)

app.config['SECRET_KEY'] = 'rfwfft4#$frfgdtdyh#fth6w4w424'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pay_users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# CREATE TABLE IN DB
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    dob = db.Column(db.DateTime)
    date = db.Column(db.DateTime)
    money = db.Column(db.Integer)
    history = db.relationship('History', backref='payment', lazy=True)


class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(100))
    recipient = db.Column(db.String(100))
    amount = db.Column(db.Integer)
    date = db.Column(db.DateTime)
    status = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


# Line below only required once, when creating DB.
db.create_all()


@app.route('/')
def home():
    return render_template("index.html", logged_in=current_user.is_authenticated)


@app.route('/register', methods=["POST", "GET"])
def register():
    if request.method == "POST":

        user = User.query.filter_by(email=request.form.get('email'), ).first()

        if user:
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        hash_and_salted_password = generate_password_hash(
            request.form.get('password'),
            method='pbkdf2:sha256',
            salt_length=8
            )

        bday = ' '.join(request.form.get('Birthday').split('-'))
        new_user = User(
            email=request.form.get('email'),
            name=request.form.get('name'),
            password=hash_and_salted_password,
            dob=datetime.datetime.strptime(bday, '%Y %m %d'),
            date=datetime.datetime.utcnow(),
            money=0
            )
        db.session.add(new_user)
        db.session.commit()

        # Log in and authenticate user after adding details to database.
        login_user(new_user)

        return redirect(url_for('secrets'))

    return render_template("register.html", logged_in=current_user.is_authenticated)


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')

        # Find user by email entered.
        user = User.query.filter_by(email=email).first()

        if not user:
            flash("The email does not exist, please try again.")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash("Password incorrect, please try again.")
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('secrets'))

        # Check stored password hash against entered password hashed.

    return render_template("login.html", logged_in=current_user.is_authenticated)


@app.route('/secrets')
def secrets():
    return render_template("secrets.html", name=current_user.name, logged_in=True, wallet=current_user.money)


@app.route('/add', methods=["GET", "POST"])
def add():
    if request.method == "POST":
        amount = int(request.form.get('amount'))
        if amount > 10000:
            flash("Payment cannot be processed for amount greater than Rs.10000.")
            new_addition = History(sender=current_user.email, recipient=current_user.email, amount=amount,
                                   date=datetime.datetime.utcnow(), status="Fail", user_id=current_user.id)
            db.session.add(new_addition)
            db.session.commit()
            return redirect(url_for('add'))
        else:
            user = User.query.get(current_user.id)
            new_amt = user.money + amount
            user.money = new_amt
            db.session.commit()

            new_addition = History(sender=current_user.email, recipient=current_user.email, amount=amount,
                                   date=datetime.datetime.utcnow(), status="Success", user_id=current_user.id)
            db.session.add(new_addition)
            db.session.commit()
            flash("Payment successfully processed!")
            return redirect(url_for('add'))
    return render_template("add.html", logged_in=True, wallet=current_user.money)


@app.route('/send', methods=["GET", "POST"])
def send():
    # user_id = request.args.get('id')
    if request.method == "POST":
        email = request.form.get('email')
        amount = int(request.form.get('amount'))

        # Find user by email entered.
        user = User.query.filter_by(email=email).first()
        print(user)
        if user is None:
            flash("The user's email does not exist, please try again.")
            new_addition1 = History(sender=current_user.email, recipient=email, amount=amount,
                                    date=datetime.datetime.utcnow(), status="Fail", user_id=current_user.id)
            db.session.add(new_addition1)
            db.session.commit()
        elif amount > current_user.money:
            flash("Payment cannot be processed. Not enough balance.")
            new_addition1 = History(sender=current_user.email, recipient=user.email, amount=amount,
                                    date=datetime.datetime.utcnow(), status="Fail", user_id=current_user.id)
            db.session.add(new_addition1)
            db.session.commit()
            return redirect(url_for('send'))
        else:
            user.money = user.money + amount
            current_user.money = current_user.money - amount
            db.session.commit()
            new_addition1 = History(sender=current_user.email, recipient=user.email, amount=amount,
                                    date=datetime.datetime.utcnow(), status="Success", user_id=current_user.id)
            # new_addition2 = History(sender=current_user.email, recipient=current_user.email, amount=amount,
            #                        date=datetime.datetime.utcnow(), status="Success", user_id=user.id)
            db.session.add(new_addition1)
            # db.session.add(new_addition2)
            db.session.commit()
            return redirect(url_for('secrets'))

    return render_template("send.html", logged_in=True, wallet=current_user.money)


@app.route('/history')
def history():
    page = request.args.get('page', 1, type=int)
    user_email = current_user.email
    payments = History.query.order_by(History.date.desc()).filter((History.recipient == user_email) |
                                                                  (History.sender == user_email)).paginate(page=page, per_page=5)
    return render_template("history.html", logged_in=True, payments=payments, wallet=current_user.money, name=current_user.email)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


if __name__ == "__main__":
    app.run(debug=True)

