#!/usr/bin/env python3
"""
Flask wrapper for the Sixt scraper to run on Render
This maintains your original logic unchanged
"""

import os
import sys
import subprocess
import json
from flask import Flask, jsonify, request, render_template_string
import logging
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# HTML interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Sixt Scraper AI Agent</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
        h1 { color: #333; }
        .form-group { margin-bottom: 20px; }
        label { font-weight: bold; display: block; margin-bottom: 5px; }
        input[type="text"] { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
        .results { margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 4px; }
        .error { color: #dc3545; }
        .success { color: #28a745; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚗 Sixt Scraper AI Agent</h1>
        <p>Enter a location to scrape car rental prices from Sixt</p>
        
        <form id="scrapeForm">
            <div class="form-group">
                <label for="location">Location:</label>
                <input type="text" id="location" name="location" placeholder="e.g., YYC, Calgary Downtown, London" required>
            </div>
            <button type="submit">Start Scraping</button>
        </form>
        
        <div id="results" style="display:none;"></div>
    </div>
    
    <script>
        document.getElementById('scrapeForm').onsubmit = async (e) => {
            e.preventDefault();
            const location = document.getElementById('location').value;
            const resultsDiv = document.getElementById('results');
            
            resultsDiv.style.display = 'block';
            resultsDiv.innerHTML = '<div class="results">⏳ Processing... This may take 1-2 minutes.</div>';
            
            try {
                const response = await fetch('/scrape', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ location: location })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    resultsDiv.innerHTML = `<div class="results error">❌ Error: ${data.error}</div>`;
                } else {
                    let html = '<div class="results success">✅ Scraping completed!</div>';
                    html += '<div class="results"><h3>Results:</h3>';
                    
                    if (data.cars && data.cars.length > 0) {
                        html += '<table><tr><th>Car Name</th><th>Type</th><th>Price/Day</th><th>Seats</th><th>Bags</th></tr>';
                        for (const car of data.cars) {
                            html += `<tr>
                                <td>${car.car_name}</td>
                                <td>${car.car_type}</td>
                                <td>${car.price_per_day}</td>
                                <td>${car.seats}</td>
                                <td>${car.bags}</td>
                            </tr>`;
                        }
                        html += '</table>';
                    } else {
                        html += '<p>No cars found for this location.</p>';
                    }
                    
                    html += `<p><small>CSV: ${data.csv_path}</small></p>`;
                    html += `<p><small>JSON: ${data.json_path}</small></p>`;
                    html += '</div>';
                    
                    resultsDiv.innerHTML = html;
                }
            } catch (error) {
                resultsDiv.innerHTML = `<div class="results error">❌ Error: ${error.message}</div>`;
            }
        };
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/scrape", methods=["POST"])
def scrape():
    """Run your original scraper script"""
    try:
        location = request.json.get("location", "")
        if not location:
            return jsonify({"error": "Location is required"}), 400

        # Save location to a temp file for your script
        with open("/tmp/location.txt", "w") as f:
            f.write(location)

        # Run your original script with the location
        # We'll pipe input to simulate user input
        result = subprocess.run(
            [
                "python3",
                "-c",
                f"""
import sys
sys.path.insert(0, '.')
# Your original script content will be here
# For now, we'll read it from the main script
exec(open('scraper_original.py').read())
""",
            ],
            input=f"{location}\n",
            text=True,
            capture_output=True,
            timeout=300,  # 5 minute timeout
        )

        # Check if output files were created
        import glob
        import pandas as pd

        # Find latest output files
        csv_files = sorted(
            glob.glob("scrapers/outputs/sixt_*.csv"), key=os.path.getctime, reverse=True
        )
        json_files = sorted(
            glob.glob("scrapers/outputs/sixt_*.json"),
            key=os.path.getctime,
            reverse=True,
        )

        cars = []
        if csv_files:
            df = pd.read_csv(csv_files[0])
            cars = df.to_dict("records")

        return jsonify(
            {
                "success": True,
                "cars": cars,
                "csv_path": csv_files[0] if csv_files else None,
                "json_path": json_files[0] if json_files else None,
                "output": result.stdout,
                "errors": result.stderr,
            }
        )

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Scraping timed out after 5 minutes"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
