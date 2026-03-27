#!/usr/bin/env python3
"""
Flask wrapper for Sixt scraper to run on Render
"""

import os
import sys
import json
import glob
import pandas as pd
from flask import Flask, jsonify, request, render_template_string
from datetime import datetime
import subprocess

app = Flask(__name__)

# HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Sixt Scraper</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
        }
        input[type="text"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
        }
        button:active {
            transform: translateY(0);
        }
        .results {
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 12px;
            display: none;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #667eea;
        }
        .error {
            background: #fee;
            color: #c33;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #c33;
        }
        .success {
            background: #efe;
            color: #3c3;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #3c3;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        tr:hover {
            background: #f5f5f5;
        }
        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-suv {
            background: #ff9800;
            color: white;
        }
        .badge-sedan {
            background: #2196f3;
            color: white;
        }
        .badge-standard {
            background: #4caf50;
            color: white;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚗 Sixt Car Rental Scraper</h1>
        <div class="subtitle">AI-Powered Scraping with Playwright</div>
        
        <form id="scrapeForm">
            <div class="form-group">
                <label for="location">Enter Location:</label>
                <input type="text" id="location" name="location" 
                       placeholder="e.g., YYC, Calgary, London Heathrow, JFK" 
                       required>
                <small style="color: #666; display: block; margin-top: 5px;">
                    Supports: Airport codes, city names, addresses, or postal codes
                </small>
            </div>
            <button type="submit">🔍 Start Scraping</button>
        </form>
        
        <div id="results"></div>
    </div>
    
    <script>
        document.getElementById('scrapeForm').onsubmit = async (e) => {
            e.preventDefault();
            const location = document.getElementById('location').value;
            const resultsDiv = document.getElementById('results');
            
            resultsDiv.innerHTML = `
                <div class="results" style="display: block;">
                    <div class="loading">
                        <div>⏳ Processing request for "${location}"...</div>
                        <div style="font-size: 14px; margin-top: 10px;">This may take 1-2 minutes</div>
                    </div>
                </div>
            `;
            
            try {
                const response = await fetch('/scrape', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ location: location })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    resultsDiv.innerHTML = `
                        <div class="results" style="display: block;">
                            <div class="error">❌ Error: ${data.error}</div>
                        </div>
                    `;
                } else if (data.cars && data.cars.length > 0) {
                    let html = '<div class="results" style="display: block;">';
                    html += '<div class="success">✅ Scraping completed successfully!</div>';
                    html += '<h3>📊 Results:</h3>';
                    html += '<table>';
                    html += '<thead><tr>';
                    html += '<th>Car Name</th><th>Type</th><th>Price/Day</th><th>Seats</th><th>Bags</th>';
                    html += '</tr></thead><tbody>';
                    
                    for (const car of data.cars) {
                        let badgeClass = 'badge-standard';
                        if (car.car_type === 'SUV') badgeClass = 'badge-suv';
                        else if (car.car_type === 'Sedan') badgeClass = 'badge-sedan';
                        
                        html += `<tr>
                            <td><strong>${car.car_name}</strong></td>
                            <td><span class="badge ${badgeClass}">${car.car_type}</span></td>
                            <td>${car.price_per_day}</td>
                            <td>${car.seats}</td>
                            <td>${car.bags}</td>
                        </tr>`;
                    }
                    
                    html += '</tbody></table>';
                    html += `<p><small>📁 CSV: ${data.csv_path}</small></p>`;
                    html += `<p><small>📄 JSON: ${data.json_path}</small></p>`;
                    html += '</div>';
                    
                    resultsDiv.innerHTML = html;
                } else {
                    resultsDiv.innerHTML = `
                        <div class="results" style="display: block;">
                            <div class="error">⚠️ No cars found for "${location}"</div>
                            <p>Try a different location or check the logs for details.</p>
                        </div>
                    `;
                }
            } catch (error) {
                resultsDiv.innerHTML = `
                    <div class="results" style="display: block;">
                        <div class="error">❌ Network Error: ${error.message}</div>
                    </div>
                `;
            }
        };
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/scrape', methods=['POST'])
def scrape():
    try:
        location = request.json.get('location', '')
        if not location:
            return jsonify({'error': 'Location is required'}), 400
        
        # Run the scraper script
        # First, let's check if we can import and run it
        try:
            # Add current directory to path
            sys.path.insert(0, os.getcwd())
            
            # Import the original script as a module
            import scraper_original
            
            # Set up a way to pass the location
            # We'll modify the script's behavior by mocking input
            original_input = __builtins__.input if hasattr(__builtins__, 'input') else input
            
            # Store the location
            mock_input = lambda prompt: location if 'Enter' in prompt else original_input(prompt)
            
            # Temporarily replace input
            import builtins
            builtins.input = mock_input
            
            # Run the main function
            scraper_original.main()
            
            # Restore input
            builtins.input = original_input
            
        except Exception as e:
            print(f"Error running scraper: {e}")
            # Try running as subprocess as fallback
            result = subprocess.run(
                ['python3', '-c', f'import scraper_original; scraper_original.main()'],
                input=f"{location}\n",
                text=True,
                capture_output=True,
                timeout=300
            )
            print(f"Subprocess output: {result.stdout}")
            print(f"Subprocess error: {result.stderr}")
        
        # Find the latest output files
        csv_files = sorted(glob.glob('scrapers/outputs/sixt_*.csv'), key=os.path.getctime, reverse=True)
        json_files = sorted(glob.glob('scrapers/outputs/sixt_*.json'), key=os.path.getctime, reverse=True)
        
        cars = []
        if csv_files:
            df = pd.read_csv(csv_files[0])
            cars = df.to_dict('records')
        
        return jsonify({
            'success': True,
            'cars': cars[:20],  # Limit to 20 cars for display
            'csv_path': csv_files[0] if csv_files else None,
            'json_path': json_files[0] if json_files else None,
            'total_cars': len(cars)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
EOFcat > app.py << 'EOF'
#!/usr/bin/env python3
"""
Flask wrapper for Sixt scraper to run on Render
"""

import os
import sys
import json
import glob
import pandas as pd
from flask import Flask, jsonify, request, render_template_string
from datetime import datetime
import subprocess

app = Flask(__name__)

# HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Sixt Scraper</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
        }
        input[type="text"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
        }
        button:active {
            transform: translateY(0);
        }
        .results {
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 12px;
            display: none;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #667eea;
        }
        .error {
            background: #fee;
            color: #c33;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #c33;
        }
        .success {
            background: #efe;
            color: #3c3;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #3c3;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        tr:hover {
            background: #f5f5f5;
        }
        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-suv {
            background: #ff9800;
            color: white;
        }
        .badge-sedan {
            background: #2196f3;
            color: white;
        }
        .badge-standard {
            background: #4caf50;
            color: white;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚗 Sixt Car Rental Scraper</h1>
        <div class="subtitle">AI-Powered Scraping with Playwright</div>
        
        <form id="scrapeForm">
            <div class="form-group">
                <label for="location">Enter Location:</label>
                <input type="text" id="location" name="location" 
                       placeholder="e.g., YYC, Calgary, London Heathrow, JFK" 
                       required>
                <small style="color: #666; display: block; margin-top: 5px;">
                    Supports: Airport codes, city names, addresses, or postal codes
                </small>
            </div>
            <button type="submit">🔍 Start Scraping</button>
        </form>
        
        <div id="results"></div>
    </div>
    
    <script>
        document.getElementById('scrapeForm').onsubmit = async (e) => {
            e.preventDefault();
            const location = document.getElementById('location').value;
            const resultsDiv = document.getElementById('results');
            
            resultsDiv.innerHTML = `
                <div class="results" style="display: block;">
                    <div class="loading">
                        <div>⏳ Processing request for "${location}"...</div>
                        <div style="font-size: 14px; margin-top: 10px;">This may take 1-2 minutes</div>
                    </div>
                </div>
            `;
            
            try {
                const response = await fetch('/scrape', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ location: location })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    resultsDiv.innerHTML = `
                        <div class="results" style="display: block;">
                            <div class="error">❌ Error: ${data.error}</div>
                        </div>
                    `;
                } else if (data.cars && data.cars.length > 0) {
                    let html = '<div class="results" style="display: block;">';
                    html += '<div class="success">✅ Scraping completed successfully!</div>';
                    html += '<h3>📊 Results:</h3>';
                    html += '<table>';
                    html += '<thead><tr>';
                    html += '<th>Car Name</th><th>Type</th><th>Price/Day</th><th>Seats</th><th>Bags</th>';
                    html += '</tr></thead><tbody>';
                    
                    for (const car of data.cars) {
                        let badgeClass = 'badge-standard';
                        if (car.car_type === 'SUV') badgeClass = 'badge-suv';
                        else if (car.car_type === 'Sedan') badgeClass = 'badge-sedan';
                        
                        html += `<tr>
                            <td><strong>${car.car_name}</strong></td>
                            <td><span class="badge ${badgeClass}">${car.car_type}</span></td>
                            <td>${car.price_per_day}</td>
                            <td>${car.seats}</td>
                            <td>${car.bags}</td>
                        </tr>`;
                    }
                    
                    html += '</tbody></table>';
                    html += `<p><small>📁 CSV: ${data.csv_path}</small></p>`;
                    html += `<p><small>📄 JSON: ${data.json_path}</small></p>`;
                    html += '</div>';
                    
                    resultsDiv.innerHTML = html;
                } else {
                    resultsDiv.innerHTML = `
                        <div class="results" style="display: block;">
                            <div class="error">⚠️ No cars found for "${location}"</div>
                            <p>Try a different location or check the logs for details.</p>
                        </div>
                    `;
                }
            } catch (error) {
                resultsDiv.innerHTML = `
                    <div class="results" style="display: block;">
                        <div class="error">❌ Network Error: ${error.message}</div>
                    </div>
                `;
            }
        };
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/scrape', methods=['POST'])
def scrape():
    try:
        location = request.json.get('location', '')
        if not location:
            return jsonify({'error': 'Location is required'}), 400
        
        # Run the scraper script
        # First, let's check if we can import and run it
        try:
            # Add current directory to path
            sys.path.insert(0, os.getcwd())
            
            # Import the original script as a module
            import scraper_original
            
            # Set up a way to pass the location
            # We'll modify the script's behavior by mocking input
            original_input = __builtins__.input if hasattr(__builtins__, 'input') else input
            
            # Store the location
            mock_input = lambda prompt: location if 'Enter' in prompt else original_input(prompt)
            
            # Temporarily replace input
            import builtins
            builtins.input = mock_input
            
            # Run the main function
            scraper_original.main()
            
            # Restore input
            builtins.input = original_input
            
        except Exception as e:
            print(f"Error running scraper: {e}")
            # Try running as subprocess as fallback
            result = subprocess.run(
                ['python3', '-c', f'import scraper_original; scraper_original.main()'],
                input=f"{location}\n",
                text=True,
                capture_output=True,
                timeout=300
            )
            print(f"Subprocess output: {result.stdout}")
            print(f"Subprocess error: {result.stderr}")
        
        # Find the latest output files
        csv_files = sorted(glob.glob('scrapers/outputs/sixt_*.csv'), key=os.path.getctime, reverse=True)
        json_files = sorted(glob.glob('scrapers/outputs/sixt_*.json'), key=os.path.getctime, reverse=True)
        
        cars = []
        if csv_files:
            df = pd.read_csv(csv_files[0])
            cars = df.to_dict('records')
        
        return jsonify({
            'success': True,
            'cars': cars[:20],  # Limit to 20 cars for display
            'csv_path': csv_files[0] if csv_files else None,
            'json_path': json_files[0] if json_files else None,
            'total_cars': len(cars)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
