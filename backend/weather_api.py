from flask import Flask, request, jsonify
import datetime as dt
import meteomatics.api as api
import google.generativeai as genai
import os
import json
from pprint import pprint as pp

app = Flask(__name__)

def get_filtered_weather_data(lat, lon):
    coords = [(lat, lon)]
    username = 'METEOMATICS_API_USERNAME'
    password = 'METEOMATICS_API_PASSWORD'
    parameters = ['precip_24h:mm', 'heavy_rain_warning_24h:idx', 'wind_warning_24h:idx', 'tstorm_warning_24h:idx']
    # , 'sat_storm_warning:idx', 'wind_speed_mean_10m_1h:km/h'
    model = 'mix'
    startdate = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
    enddate = startdate + dt.timedelta(days=10)
    interval = dt.timedelta(hours=24)

    df = api.query_time_series(coords, startdate, enddate, interval, parameters, username, password, model=model)
    
    # filtered_df = df[(df['heavy_rain_warning_24h:idx'] > 1) | (df['tstorm_warning_24h:idx'] > 2)]

    # return filtered_df if not filtered_df.empty else None
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 8192,
        "response_mime_type": "application/json",
    }

    model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    )
    init_prompt = '''
Analyze the following weather data and provide a detailed summary in JSON format, highlighting the severity of weather conditions for each date. The parameters to consider are as follows:
- Precipitation: Total rainfall in mm accumulated over the last 24 hours.
- Heavy Rain Warning Index: A description based on the index value ranging from 0 to 3, indicating the severity of rainfall.
  - 0: No severe rainfall
  - 1: Heavy Rainfall
  - 2: Severe Heavy Rainfall
  - 3: Extreme Heavy Rainfall
- Wind Warning Index: A description based on the index value ranging from 0 to 6, indicating the severity of wind conditions.
  - 0: No severe wind conditions (< 50km/h)
  - 1: Wind Gusts (50km/h to 64km/h)
  - 2: Squall (65km/h to 89km/h)
  - 3: Severe Squall (90km/h to 104km/h)
  - 4: Violent Squall (105km/h to 119km/h)
  - 5: Gale-Force Winds (120km/h to 139km/h)
  - 6: Extreme Gale-Force Winds (> 140km/h)
- Thunderstorm Warning Index**: A description based on the index value ranging from 0 to 4, indicating the severity of thunderstorms.
  - 0: No thunderstorms
  - 1: Thunderstorm (Occurrence of electric discharge)
  - 2: Heavy Thunderstorm (Occurrence of electric discharge with strong gale, heavy rain, or hail)
  - 3: Severe Thunderstorm (Occurrence of electric discharge with strong gale, heavy rain, or hail, with at least one warning feature)
  - 4: Severe Thunderstorm with Extreme Squalls and Heavy Rainfall (Occurrence of electric discharge with strong gale, heavy rain, or hail with at least one alerting feature)
  
  the returned JSON should have
  - "message": A brief description of the climate in 4 words or fewer.
- "info": A more detailed explanation (up to one sentence) regarding the severity of the weather conditions based on the precipitation    index, heavy rain warning index, wind warning index, and thunderstorm warning index. upto 10 words or so max.
- "alert": You decide which alert to provide based on the weather conditions. Green, Yellow, Orange, Red. single word.
    REMEMBER THE JSON SHOULD HAVE ONLY 2 KEYS "message" and "info" and "alert" AND CONTAINS ONLY 1 OBJECT also remember to speak as if you are providing weather information to the user and speak about present and future weather conditions.

  '''
    json_data = df.to_json(orient='records', date_format='iso')
    response = model.generate_content(init_prompt + " Here is the json for the data: " + json_data)
    text = response.text
    print("response type: ", type(response))
    return text

@app.route('/weather', methods=['POST'])
def get_weather():
    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON format"}), 400
    lat = data.get('lat')
    lon = data.get('lon')
    # lat, lon = 25.29, 91.58
    # hostel = 9.53, 76.82
    result = get_filtered_weather_data(lat, lon)
    json_data = json.loads(result)
    # print(result)
    if result is not None:
        return jsonify({
            "location": "",
            "message": json_data.get('message'),
            "info": json_data.get('info'),
            "alert": json_data.get('alert')
        })
    else:
        return jsonify({
            "location": "Unknown",
            "message": "No message",
            "info": "No info",
            "alert": "No alert"
        })

if __name__ == '__main__':
    app.run(debug=True)