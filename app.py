import requests
import string
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///alaska_weather.db'  # Renamed DB
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'thisisasecret'
db = SQLAlchemy(app)


class City(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)


# Modified to focus on Alaskan cities
def get_weather_data(city):
    # Default to Fairbanks if empty
    if not city:
        city = "Fairbanks"
    
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid=b21a2633ddaac750a77524f91fe104e7"
    try:
        r = requests.get(url).json()
        if r['cod'] != 200:
            # Fallback to Fairbanks if invalid city
            return get_weather_data("Fairbanks")
        return r
    except:
        return get_weather_data("Fairbanks")  # Ensure Alaska data always shows


@app.route('/')
def index_get():
    cities = City.query.all()

    # If no cities in DB, auto-add Fairbanks
    if not cities:
        default_city = City(name="Fairbanks")
        db.session.add(default_city)
        db.session.commit()
        cities = [default_city]

    weather_data = []
    alaskan_cities = ["Fairbanks", "Anchorage", "Barrow"]  # Priority cities

    # Show Alaskan cities first
    for city_name in alaskan_cities:
        city = City.query.filter_by(name=city_name).first()
        if city:
            r = get_weather_data(city.name)
            weather = {
                'city': city.name,
                'temperature': r['main']['temp'],
                'description': r['weather'][0]['description'],
                'icon': r['weather'][0]['icon'],
            }
            weather_data.append(weather)

    # Add other cities
    for city in cities:
        if city.name not in alaskan_cities:
            r = get_weather_data(city.name)
            weather = {
                'city': city.name,
                'temperature': r['main']['temp'],
                'description': r['weather'][0]['description'],
                'icon': r['weather'][0]['icon'],
            }
            weather_data.append(weather)

    return render_template('weather.html', weather_data=weather_data)


@app.route('/', methods=['POST'])
def index_post():
    err_msg = ''
    new_city = request.form.get('city', '').strip().lower()
    new_city = string.capwords(new_city) if new_city else "Fairbanks"  # Default to Fairbanks

    if new_city:
        existing_city = City.query.filter_by(name=new_city).first()
        
        if not existing_city:
            new_city_data = get_weather_data(new_city)
            if new_city_data['cod'] == 200:
                new_city_obj = City(name=new_city)
                db.session.add(new_city_obj)
                db.session.commit()
            else:
                err_msg = 'City not found! Try Alaskan cities like Juneau or Nome.'
        else:
            err_msg = 'City already tracked!'

    if err_msg:
        flash(err_msg, 'error')
    else:
        flash(f'{new_city} added!', 'success')

    return redirect(url_for('index_get'))


@app.route('/delete/<name>')
def delete_city(name):
    if name not in ["Fairbanks", "Anchorage"]:  # Prevent deleting default Alaskan cities
        city = City.query.filter_by(name=name).first()
        if city:
            db.session.delete(city)
            db.session.commit()
            flash(f'Deleted {city.name}!', 'success')
    else:
        flash('Cannot delete core Alaskan cities!', 'error')
    return redirect(url_for('index_get'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Initialize DB
    app.run()
