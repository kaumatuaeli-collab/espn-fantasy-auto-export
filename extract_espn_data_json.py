import json
import requests
import os
from datetime import datetime

# Function to validate JSON serializability
def validate_json_serializable(data):
    """
    Validate if the given data is JSON serializable.
    """
    try:
        json.dumps(data)
        return True
    except TypeError as e:
        print(f"Error: Non-serializable data encountered - {e}")
        return False

# Function to extract ESPN data
def extract_espn_data():
    url = 'https://fantasy.espn.com/apis/v3/games'  # Sample URL
    print("Fetching ESPN data...")
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    return data

# Saving the extracted data to a JSON file
def save_data_to_json(data, filename):
    if not validate_json_serializable(data):
        raise ValueError("Data is not JSON serializable")

    try:
        with open(filename, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, indent=4, ensure_ascii=False)
        size_kb = os.path.getsize(filename) / 1024
        print(f"✔ Saved: {filename} ({size_kb:.1f} KB)")
    except IOError as e:
        print(f"Error: Unable to write JSON file - {e}")

if __name__ == '__main__':
    try:
        print("Starting ESPN data extraction...")
        espn_data = extract_espn_data()
        save_data_to_json(espn_data, 'espn_data.json')
        print("Data extraction and saving complete.")
    except Exception as e:
        print(f"✗ ERROR: {e}")
        raise
