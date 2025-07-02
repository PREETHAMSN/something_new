from flask import Flask, jsonify, request
import mysql.connector

# Initialize Flask app
app = Flask(__name__)

# Database configuration (replace with your actual credentials)
db_config = {
    'user': 'your_username',
    'password': 'your_password',
    'host': 'your_host',
    'database': 'your_database'
}

# Function to establish database connection
def get_db_connection():
    return mysql.connector.connect(**db_config)

# Endpoint for core/cet dropdown options
@app.route('/api/core_cet_options', methods=['GET'])
def get_core_cet_options():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT core_cet FROM issues")
    options = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return jsonify(options)

# Endpoint for platform dropdown options
@app.route('/api/platforms', methods=['GET'])
def get_platforms():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT platform FROM issues")
    options = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return jsonify(options)

# Endpoint for generation dropdown options
@app.route('/api/generations', methods=['GET'])
def get_generations():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT generation FROM issues")
    options = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return jsonify(options)

# Endpoint for issue counts based on selected combination
@app.route('/api/issue_counts', methods=['GET'])
def get_issue_counts():
    # Get query parameters from the frontend
    core_cet = request.args.get('core_cet')
    platform = request.args.get('platform')
    generation = request.args.get('generation')

    # Validate that all parameters are provided
    if not all([core_cet, platform, generation]):
        return jsonify({'error': 'Missing parameters'}), 400

    # Connect to the database and execute query
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
    SELECT
        SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END) AS closed,
        SUM(CASE WHEN status = 'Open' THEN 1 ELSE 0 END) AS open
    FROM issues
    WHERE core_cet = %s AND platform = %s AND generation = %s
    """
    cursor.execute(query, (core_cet, platform, generation))
    result = cursor.fetchone()

    # Clean up database resources
    cursor.close()
    conn.close()

    # Process query result
    if result:
        closed, open_ = result
        return jsonify({'closed': closed or 0, 'open': open_ or 0})
    return jsonify({'closed': 0, 'open': 0})

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)