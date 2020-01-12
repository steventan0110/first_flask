from flask import Flask, render_template, session, redirect, url_for, flash
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_script import Manager, Shell
from flask_wtf import Form
from flask_migrate import Migrate, MigrateCommand
from flask_mail import Mail, Message
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from threading import Thread
import os
from wtforms.validators import Required

#Configurations
app = Flask(__name__)
app.config['SECRET_KEY'] = 'hard to guess string'
app.config['SQLALCHEMY_DATABASE_URI'] = \
    'mysql+mysqldb://root:twt123456@localhost:3306/sqlalchemy'
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False #suppress warning
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['FLASKY_MAIL_SUBJECT_PREFIX'] = '[Flasky]'
app.config['FLASKY_MAIL_SENDER'] = 'Flasky Admin <steventan0110@gmail.com>'
app.config['FLASKY_ADMIN'] = os.environ.get('FLASKY_ADMIN')

#utilize bootstrap and mysql
bootstrap = Bootstrap(app)
db = SQLAlchemy(app)
manager = Manager(app)
mail = Mail(app)

#DB migration
migrate = Migrate(app,db)
manager.add_command('db', MigrateCommand)

#Form definition
class NameForm(Form):
    name = StringField('What is your name?', validators=[DataRequired()])
    submit = SubmitField('Submit')

#Model definition:
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    def __repr__(self):
        return '<Role %r>' % self.name
    users = db.relationship('User', backref='role',lazy='dynamic')

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    def __repr__(self):
        return '<User %r>' % self.username
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))


@app.route('/user/<name>')
def user(name):
    return render_template('user.html', name=name)

#Error handling
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

#background thread sending emails:
def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(to, subject, template, **kwargs):
    msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + subject,
                  sender=app.config['FLASKY_MAIL_SENDER'],
                  recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    print(msg.body,msg.html)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr

@app.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.name.data).first()
        if user is None:
            user = User(username=form.name.data)
            db.session.add(user)
            session['known'] = False
            if app.config['FLASKY_ADMIN']:
                send_email(app.config['FLASKY_ADMIN'], 'New User',
                           'mail/new_user', user=user)
        else:
            session['known'] = True

        old_name = session.get('name')
        session['name'] = form.name.data
        if old_name is not None and old_name != form.name.data:
            #flash status update message for user
            flash("Looks like you have changed your name")
        form.name.data = ''
        return redirect(url_for('index'))
    return render_template('index.html',
                           form=form,
                           name=session.get('name'),
                           known=session.get('known', False))

#display app information through shell command
def make_shell_context():
    return dict(app=app, db=db, User=User, Role=Role)
manager.add_command("shell", Shell(make_context=make_shell_context))

if __name__ == '__main__':
    manager.run()




