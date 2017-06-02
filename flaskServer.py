#! /usr/bin/env python3
#  -*- coding: utf-8 -*-

""" This Python file is the webserver that performs CRUD operations on the
    catalog.db """

# Python imports
from flask import Flask, render_template, request, redirect, url_for
from flask import jsonify, make_response, session as login_session
from generate_database import Base, User, Catalog, Item
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
import random
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
import requests
import string
from functools import wraps

app = Flask(__name__)

engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']


# This function checks if the user is logged in.
def isUserLoggedIn():
    return not (login_session.get('access_token') is None and
                login_session.get('username') is None and
                login_session.get('gplus_id') is None)


# This function is a wrapper function that redirects the user if he/she is not
# Logged in.
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if isUserLoggedIn():
            return f(*args, **kwargs)
        else:
            return redirect('/login')
    return decorated_function


# This function displays all the Catalogs.
@app.route('/')
@app.route('/catalog/')
def displayCatalogs():
    catalogs = session.query(Catalog).order_by(Catalog.name).all()
    return render_template('catalogsTemplate.html', catalogs=catalogs,
                           isUserLoggedIn=isUserLoggedIn())


# This function displays the login button.
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state,
                           isUserLoggedIn=isUserLoggedIn())


# This function handles connection of a user.
@app.route('/oauth2callback', methods=['POST'])
def gconnect():
    print("HI")
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads((h.request(url, 'GET')[1]).decode())
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print("Token's client ID does not match app's.")
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps(
                                 'Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        print(response)
        return redirect(url_for('showLogin'))

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = answer.json()
    login_session['username'] = data['name']
    login_session['email'] = data["email"]
    user = None
    try:
        user = session.query(User).filter_by(email=login_session['email']).one()
    except:
        user = None
    if user is None:
        newUser = User(email=login_session['email'])
        session.add(newUser)
        session.commit()
    print(login_session['username'])
    return ("Hi " + login_session['username'])


# This function handles disconnection of a User.
@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
            print('Access Token is None')
            return redirect(url_for('displayCatalogs'))
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print('result is ')
    print(result['status'])
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        print("Success: %s" % response)
        return redirect(url_for('displayCatalogs'))
    else:
        response = make_response(json.dumps('Revoke token failed.', 400))
        response.headers['Content-Type'] = 'application/json'
        print("Failed: %s" % response)
        return redirect(url_for('displayCatalogs'))


# This function displays Items of a Catalog.
@app.route('/catalog/<cName>/items')
def displayCatalogItems(cName):
    catalog = session.query(Catalog).filter_by(name=cName).one()
    catalogItems = session.query(Item).filter_by(catalog_id=catalog.id).all()
    return render_template('catalogItemsTemplate.html', cName=cName,
                           items=catalogItems, isUserLoggedIn=isUserLoggedIn())


# This function handles addition of an Item.
@app.route('/catalog/<cName>/items/add', methods=['GET', 'POST'])
@login_required
def addCatalogItem(cName):
    catalog = session.query(Catalog).filter_by(name=cName).one()
    currentUser = session.query(User).filter_by(email=login_session
                                                    .get('email')).one()
    if request.method == 'POST':
        newItem = Item(name=request.form['name'],
                       description=request.form['description'],
                       catalog_id=catalog.id, user_id=currentUser.id)
        session.add(newItem)
        session.commit()
        return redirect(url_for('displayCatalogItems', cName=cName,
                                isUserLoggedIn=isUserLoggedIn()))
    else:
        return render_template('addItemTemplate.html', cName=cName)


# This function displays a single Item.
@app.route('/catalog/<cName>/items/<itemName>')
def displayCatalogItem(cName, itemName):
    item = session.query(Item).filter_by(name=itemName).one()
    return render_template('itemTemplate.html', cName=cName, item=item,
                           isUserLoggedIn=isUserLoggedIn())


# This function handles editing of an Item.
@app.route('/catalog/<cName>/items/<itemName>/edit', methods=['GET', 'POST'])
@login_required
def editCatalogItem(cName, itemName):
    editItem = session.query(Item).filter_by(name=itemName).one()
    currentUser = session.query(User).filter_by(email=login_session
                                                .get('email')).one()
    if currentUser.id != editItem.user_id:
        return "<h1>You can't edit this item! Return back.</h1>"
    if request.method == 'POST':
        if request.form['name']:
            editItem.name = request.form['name']
            editItem.description = request.form['description']
            session.add(editItem)
            session.commit()
        return redirect(url_for('displayCatalogItem', cName=cName,
                                itemName=editItem.name,
                                isUserLoggedIn=isUserLoggedIn()))
    else:
        return render_template('editItemTemplate.html',
                               cName=cName, item=editItem)


# This function handles deletion of an Item.
@app.route('/catalog/<cName>/items/<itemName>/delete', methods=['GET', 'POST'])
@login_required
def deleteCatalogItem(cName, itemName):
    deleteItem = session.query(Item).filter_by(name=itemName).one()
    currentUser = session.query(User).filter_by(email=login_session
                                                .get('email')).one()
    if currentUser.id != deleteItem.user_id:
        return "<h1>You can't delete this item! Return back.</h1>"
    if request.method == 'POST':
        session.delete(deleteItem)
        session.commit()
        return redirect(url_for('displayCatalogItems', cName=cName,
                                isUserLoggedIn=isUserLoggedIn()))
    else:
        return render_template('deleteItemTemplate.html', cName=cName,
                               itemName=itemName)


# This function displays the json of catalogs.
@app.route('/catalogs/json')
def displayCatalogsJSON():
    catalogs = session.query(Catalog).order_by(Catalog.id).all()
    return jsonify(Catalog=[catalog.serialize for catalog in catalogs])


# This function displays the json of Items.
@app.route('/items/json')
def displayItemsJSON():
    items = session.query(Item).order_by(Item.id).all()
    return jsonify(Items=[item.serialize for item in items])


# This function displays a JSON for a single Item.
@app.route('/catalog/<cName>/items/<itemName>')
def displayCatalogItemJSON(cName, itemName):
    item = session.query(Item).filter_by(name=itemName).one()
    return jsonify(Items=[item.serialize])


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8080)
