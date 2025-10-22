import json
import requests

# Function to extract ESPN data

def extract_espn_data():
    url = 'https://fantasy.espn.com/apis/v3/games'  # Sample URL
    response = requests.get(url)
    data = response.json()
    return data

# Saving the extracted data to a JSON file

def save_data_to_json(data, filename):
    with open(filename, 'w') as json_file:
        json.dump(data, json_file, indent=4)

if __name__ == '__main__':
    espn_data = extract_espn_data()
    save_data_to_json(espn_data, 'espn_data.json')