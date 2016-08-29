import os
from flask import request, session, abort, g, render_template, redirect, flash, jsonify, url_for
import bcrypt
import base64
from datetime import datetime, timedelta
from init import app, db
import models

### Before-request handlers ###

@app.before_request
def csrf_protect():
    if request.method == "POST":
        if 'csrf_token' in session:
            if request.form['csrf_token'] != session['csrf_token']:
                abort(403)
        else:
            abort(403)


@app.before_request
def setup_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = base64.b64encode(os.urandom(32)).decode('ascii')


@app.before_request
def setup_user_global():
    if 'auth_user' in session:
        user = models.User.query.get(session['auth_user'])
        if user is None:
            del session['auth_user']
        g.user = user

### Webpage handlers ###

@app.route('/')
def main_page():
    # If user is logged in, render the main activity page
    if 'auth_user' in session:
        # Check if user has activity underway
        uid = session['auth_user']
        activity_check = models.Activity.query.filter_by(user_id=uid).filter_by(current=True).first()
        in_progress = 0
        description = ''
        start_time = ''
        if activity_check is not None:
            in_progress = 1
            description = activity_check.description
            start_time = activity_check.start_time.isoformat()
        return render_template('activity.html', in_progress=in_progress, description=description, start_time=start_time)
    # User is not logged in; render login page
    return render_template('index.html')


@app.errorhandler(404)
def page_not_found(error):
    return render_template('not_found.html'), 404

### API handlers ###

@app.route('/start-activity', methods=['POST'])
def start_activity():
    description = request.form['description']
    uid = request.form['user_id']
    if not check_auth(uid):
        return abort(403)
    # Check if user already has an activity underway
    activity_check = models.Activity.query.filter_by(user_id=uid).filter_by(current=True).first()
    if activity_check is not None:
        abort(400)
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
    return jsonify(json_activity)


@app.route('/end-activity', methods=['POST'])
def end_activity():
    uid = request.form['user_id']
    if not check_auth(uid):
        return abort(403)
    activity = models.Activity.query.filter_by(user_id=uid).order_by(models.Activity.id.desc()).first()
    if activity is None:
        abort(400)
    if activity.current is False:
        abort(400)
    activity.current = False
    activity.end_time = datetime.utcnow()
    db.session.commit()
    return activity.description


@app.route('/get-activities', methods=['POST'])
def get_activities():
    uid = request.form['user_id']
    if not check_auth(uid):
        return abort(403)
    index = int(request.form['index'])
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
    return jsonify({'activities': activity_list, 'has_next': has_next})


### Authentication handlers ###


@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = models.User.query.filter_by(username=username).first()
    if user is not None:
    # Hash the password given in the form and compare to the stored hash for this user
        pw_hash = bcrypt.hashpw(password.encode('utf8'), user.pw_hash)
        if pw_hash == user.pw_hash:
            session['auth_user'] = user.id
            return redirect(url_for('main_page'), 303) # change this later
    # If username or password is invalid, redirect to main page
    flash('Invalid username or password.')
    return redirect(url_for('main_page'))


@app.route('/register', methods=['POST'])
def create_account():
    username = request.form['username']
    password = request.form['password']
    pwConfirm = request.form['password-confirm']
    username_check = models.User.query.filter_by(username=username).first()
    if username_check is not None:
        flash('There is already an account registered for this username address.')
        return redirect(url_for('main_page'), 303)
    if password != pwConfirm:
        flash('Passwords do not match.')
        return redirect(url_for('main_page'), 303)
    # Create a new User object
    user = models.User()
    user.username = username
    user.pw_hash = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt(15))
    # Save user to DB
    db.session.add(user)
    db.session.commit()
    #Save user info in Flask session
    session['auth_user'] = user.id
    g.user = user
    return redirect(url_for('main_page'), 303) # change this later


@app.route('/logout', methods=['POST'])
def logout():
    del session['auth_user']
    del g.user
    return redirect(url_for('main_page'), 303)


# Checks if user is properly authenticated.
def check_auth(uid):
    if 'auth_user' not in session:
        return False
    if int(uid) is not session['auth_user']:
        return False
    return True