import os
import flask
import bcrypt
import base64
from datetime import datetime, timedelta
from init import app, db
import models

### Before-request handlers ###

@app.before_request
def csrf_protect():
    if flask.request.method == "POST":
        if 'csrf_token' in flask.session:
            if flask.request.form['csrf_token'] != flask.session['csrf_token']:
                flask.abort(403)
        else:
            flask.abort(403)


@app.before_request
def setup_csrf_token():
    if 'csrf_token' not in flask.session:
        flask.session['csrf_token'] = base64.b64encode(os.urandom(32)).decode('ascii')


@app.before_request
def setup_user_global():
    if 'auth_user' in flask.session:
        user = models.User.query.get(flask.session['auth_user'])
        if user is None:
            del flask.session['auth_user']
        flask.g.user = user

### Webpage handlers ###

@app.route('/')
def main_page():
    # If user is logged in, render the main activity page
    if 'auth_user' in flask.session:
        # Check if user has activity underway
        uid = flask.session['auth_user']
        activity_check = models.Activity.query.filter_by(user_id=uid).filter_by(current=True).first()
        in_progress = 0
        description = ''
        start_time = ''
        if activity_check is not None:
            in_progress = 1
            description = activity_check.description
            start_time = activity_check.start_time.isoformat()
        return flask.render_template('activity.html', in_progress=in_progress, description=description, start_time=start_time)
    # User is not logged in; render login page
    return flask.render_template('index.html')


@app.errorhandler(404)
def page_not_found():
    return flask.render_template('not_found.html'), 404

### API handlers ###

@app.route('/start-activity', methods=['POST'])
def start_activity():
    description = flask.request.form['description']
    uid = flask.request.form['user_id']
    if not check_auth(uid):
        return flask.abort(403)
    # Check if user already has an activity underway
    activity_check = models.Activity.query.filter_by(user_id=uid).filter_by(current=True).first()
    if activity_check is not None:
        flask.abort(400)
    # Create activity object
    activity =  models.Activity()
    activity.description = description
    activity.current = True
    start_time = datetime.utcnow()
    activity.start_time = start_time
    activity.user_id = uid
    # Save activity
    db.session.add(activity)
    db.session.commit()
    # Create activity JSON
    json_activity = {}
    json_activity['description'] = activity.description
    json_activity['start'] = start_time
    return flask.jsonify(json_activity)


@app.route('/end-activity', methods=['POST'])
def end_activity():
    uid = flask.request.form['user_id']
    if not check_auth(uid):
        return flask.abort(403)
    activity = models.Activity.query.filter_by(user_id=uid).order_by(models.Activity.id.desc()).first()
    if activity is None:
        flask.abort(400)
    if activity.current is False:
        flask.abort(400)
    activity.current = False
    activity.end_time = datetime.utcnow()
    db.session.commit()
    return activity.description


@app.route('/get-activities', methods=['POST'])
def get_activities():
    uid = flask.request.form['user_id']
    if not check_auth(uid):
        return flask.abort(403)
    index = int(flask.request.form['index'])
    index *= 10
    activities = models.Activity.query.filter_by(user_id=uid).filter_by(current=False).\
        order_by(models.Activity.id.desc()).limit(10).offset(index).all()
    activity_list = []
    for activity in activities:
        activity_dict = {}
        activity_dict['description'] = activity.description
        activity_dict['start_time'] = activity.start_time.isoformat()
        activity_dict['end_time'] = activity.end_time.isoformat()
        activity_dict['duration'] = (activity.end_time - activity.start_time).total_seconds()
        activity_list.append(activity_dict)
    # Check if there are more activities
    has_next = 0
    if len(activities) > 9:
        next_check = None
        next_check = models.Activity.query.filter_by(user_id=uid).filter_by(current=False).\
            order_by(models.Activity.id.desc()).offset(index+10).first()
        if next_check is not None:
            has_next = 1
    return flask.jsonify({'activities': activity_list, 'has_next': has_next})


### Authentication handlers ###


@app.route('/login', methods=['POST'])
def login():
    username = flask.request.form['username']
    password = flask.request.form['password']
    user = models.User.query.filter_by(username=username).first()
    if user is not None:
    # Hash the password given in the form and compare to the stored hash for this user
        pw_hash = bcrypt.hashpw(password.encode('utf8'), user.pw_hash)
        if pw_hash == user.pw_hash:
            flask.session['auth_user'] = user.id
            return flask.redirect(flask.url_for('main_page'), 303) # change this later
    # If username or password is invalid, redirect to main page
    flask.flash('Invalid username or password.')
    return flask.redirect(flask.url_for('main_page'))


@app.route('/register', methods=['POST'])
def create_account():
    username = flask.request.form['username']
    password = flask.request.form['password']
    pwConfirm = flask.request.form['password-confirm']
    username_check = models.User.query.filter_by(username=username).first()
    if username_check is not None:
        flask.flash('There is already an account registered for this username address.')
        return flask.redirect(flask.url_for('main_page'), 303)
    if password != pwConfirm:
        flask.flash('Passwords do not match.')
        return flask.redirect(flask.url_for('main_page'), 303)
    # Create a new User object
    user = models.User()
    user.username = username
    user.pw_hash = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt(15))
    # Save user to DB
    db.session.add(user)
    db.session.commit()
    #Save user info in Flask session
    flask.session['auth_user'] = user.id
    flask.g.user = user
    return flask.redirect(flask.url_for('main_page'), 303) # change this later


@app.route('/logout', methods=['POST'])
def logout():
    del flask.session['auth_user']
    del flask.g.user
    return flask.redirect(flask.url_for('main_page'), 303)


# Checks if user is properly authenticated.
def check_auth(uid):
    if 'auth_user' not in flask.session:
        return False
    if int(uid) is not flask.session['auth_user']:
        return False
    return True