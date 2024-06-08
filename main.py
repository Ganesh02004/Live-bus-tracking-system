from flask import Flask, render_template, request, redirect, url_for,jsonify
from pymongo import MongoClient
import json
import bcrypt

from uuid import uuid4
app=Flask(__name__)


client = MongoClient('mongodb://localhost:27017/')
db = client['hackathon']
users_collection = db['users']
users_collection1 = db['admin_log']
db1 = client['bus_tracking_db']
routes_collection = db1['routes']
bus_stops_collection = db1['bus_stops']
buses_collection = db1['buses']


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        users_collection.insert_one({'username': username, 'password': hashed_password})

        return redirect(url_for('login'))
    return render_template('signup.html')



login_attempts = {}  

@app.route('/login', methods=['GET', 'POST'])
def login():
    error_message = None
    if request.method == 'POST':
    
        username = request.form['username']
        password = request.form['password']
        user = users_collection.find_one({'username': username})
        if user:

            if bcrypt.checkpw(password.encode('utf-8'), user['password']):
                print('true that the password has matched')
                return redirect(url_for('index'))
            else:
                error_message = 'Incorrect password'
        else:
            error_message = 'User not found'

        if username in login_attempts:
            login_attempts[username] += 1
        else:
            login_attempts[username] = 1

        if login_attempts.get(username, 0) >= 3:
            error_message = 'Too many login attempts. Try again later. you can try after 10'

    return render_template('login.html', error_message=error_message)



@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/index')
def index():
    return render_template('bus_selection.html')

@app.route('/get_bus_stops', methods=['POST'])
def get_bus_stops():
    
    query = request.json['query']
    matching_bus_stops = bus_stops_collection.find({"name": {"$regex": query, "$options": "i"}})
    bus_stop_names = [bus_stop['name'] for bus_stop in matching_bus_stops]
    return jsonify(bus_stop_names)

@app.route('/get_available_buses', methods=['POST'])
def get_available_buses():
    starting_bus_stop = request.json['starting_bus_stop']
    destination_bus_stop = request.json['destination_bus_stop']
    

    matching_routes = routes_collection.find({"bus_stops": {"$all": [starting_bus_stop, destination_bus_stop]}})
    
    available_buses = []

    for route in matching_routes:

        starting_index = route['bus_stops'].index(starting_bus_stop)
        destination_index = route['bus_stops'].index(destination_bus_stop)
        

        if starting_index < destination_index:
            buses_on_route = list(buses_collection.find({"route_id": route['_id']}))
            for bus in buses_on_route:
                if 'dispatch_time' in bus and bus['dispatch_time']:
                    available_buses.append({'id': str(bus['_id']), 'name': bus['name'], 'dispatch_time': bus['dispatch_time'],'type':bus['type']})
                else:
                    available_buses.append({'id': str(bus['_id']), 'name': bus['name'],'type':bus['type']})

    if available_buses:
        return jsonify({'buses': available_buses})
    else:
        return jsonify({'message': 'No buses available on this route'})



@app.route('/logout')
def logout():
    return redirect(url_for('home'))


@app.route('/map',methods=['GET','POST'])
def map():
    bus_stops_list = []
    if request.method == 'POST':
        data = request.get_json()
        bus_name = data.get('busName')
        bus = buses_collection.find_one({'name': bus_name})
        route_id = bus['route_id']
        route = routes_collection.find({'_id': route_id})
        
    
        for bus_stops in route:
            for bus_stop in bus_stops['bus_stops']:
                bus_stop_data = bus_stops_collection.find_one({"name": bus_stop})
                if bus_stop_data:

                    bus_stops_list.append({
                        'name': bus_stop_data['name'],
                        'coordinates': [bus_stop_data['latitude'], bus_stop_data['longitude']]
                    })
                
            break
        with open('static/bus_stops.json', 'w') as json_file:
                    json.dump(bus_stops_list, json_file)
    return render_template('map.html')




if __name__ == '__main__':
    app.run(debug=True) 