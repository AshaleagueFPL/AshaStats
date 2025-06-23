from flask import Flask, render_template, jsonify, request
from fpl_analyzer import FPLAnalyzer

app = Flask(__name__)

# Global analyzer instance
analyzer = FPLAnalyzer()

@app.route('/')
def index():
    """Main app page"""
    return render_template('index.html')

@app.route('/api/initialize')
def initialize():
    """Initialize FPL data"""
    if analyzer.initialize_data():
        return jsonify({
            "success": True,
            "current_gameweek": analyzer.current_gw,
            "total_gameweeks": len(analyzer.gdata['events'])
        })
    return jsonify({"success": False, "error": "Failed to load FPL data"})

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

@app.route('/api/set_league', methods=['POST'])
def set_league():
    """Set league ID"""
    data = request.get_json()
    league_id = data.get('league_id')
    
    if not league_id:
        return jsonify({"success": False, "error": "League ID required"})
    
    analyzer.league_id = league_id
    if analyzer.load_league_data():
        return jsonify({
            "success": True,
            "team_count": len(analyzer.teams),
            "league_name": analyzer.teams[0].get('league_name', 'Unknown') if analyzer.teams else 'Unknown'
        })
    
    return jsonify({"success": False, "error": "Failed to load league data"})

@app.route('/api/stats/<stat_type>/<int:gameweek>')
def get_stats(stat_type, gameweek):
    """Get specific stat data"""
    return jsonify(analyzer.get_stat_data(stat_type, gameweek))

@app.route('/api/available_stats')
def available_stats():
    """Get list of available stat types"""
    return jsonify({
        "stats": [
            {"id": "ownership", "name": "Effective Ownership", "icon": "fas fa-users"},
            {"id": "captaincy", "name": "Captaincy Analysis", "icon": "fas fa-bolt"},
            {"id": "transfers", "name": "Transfer Summary", "icon": "fas fa-exchange-alt"},
            {"id": "rankings", "name": "Manager Rankings", "icon": "fas fa-trophy"},
            {"id": "unique", "name": "Unique Players", "icon": "fas fa-star"},
            {"id": "representation", "name": "Team Representation", "icon": "fas fa-building"}
        ]
    })


# @app.route('/manifest.json')
# def manifest():
#     """PWA manifest"""
#     return jsonify({
#         "name": "FPL League Analyzer",
#         "short_name": "FPL Stats",
#         "description": "Fantasy Premier League statistics for your mini-league",
#         "start_url": "/",
#         "display": "standalone",
#         "background_color": "#38003c",
#         "theme_color": "#00ff85",
#         "icons": [
#             {
#                 "src": "/static/assets/icon-192.png",
#                 "sizes": "192x192",
#                 "type": "image/png"
#             },
#             {
#                 "src": "/static/assets/icon-512.png",
#                 "sizes": "512x512",
#                 "type": "image/png"
#             }
#         ]
#     })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)