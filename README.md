# AshaStats

A web application for analyzing Fantasy Premier League (FPL) mini-leagues, providing detailed statistics and insights about player ownership, captaincy choices, transfers, and more.

## Project Overview

FPL League Analyzer (AshaStats) is a Flask-based web application that allows users to track and analyze statistics for their Fantasy Premier League mini-leagues. The application provides a user-friendly interface to view important FPL data like:

- Effective ownership percentages
- Captaincy choices across your league
- Transfer activity
- Manager performance rankings
- Unique player selections
- Team representation stats

The application is built as a Progressive Web App (PWA) and can be installed on mobile devices for a native-like experience.

## Project Structure

```
├── app.py                 # Main Flask application entry point
├── fpl_analyzer.py        # Core FPL data analysis functionality
├── generate_ios_assets.py # Script to generate iOS app icons and splash screens
├── requirements.txt       # Python dependencies
├── sw.js                  # Service Worker for PWA functionality
├── static/                # Static assets
│   ├── assets/            # Images, icons, and splash screens
│   ├── css/               # Stylesheets
│   │   ├── styles.css     # Main styles
│   │   └── components.css # Component-specific styles
│   ├── js/                # JavaScript files
│   │   ├── app.js         # Core application logic
│   │   ├── settings.js    # Settings management
│   │   └── stats.js       # Statistics handling
│   └── manifest.json      # PWA manifest file
└── templates/             # HTML templates
    ├── debug_index.html   # Debug version of the main page
    ├── index.html         # Main application HTML
    ├── settings.html      # Settings page content
    └── stats.html         # Stats page content
```

## Features

- **League Analysis**: Enter your FPL mini-league ID to analyze your league
- **Gameweek Navigation**: Navigate through gameweeks to view historical data
- **Comprehensive Stats**: Multiple statistics cards with detailed insights
- **Dark Mode**: Toggle between light and dark themes
- **Responsive Design**: Works on mobile, tablet, and desktop devices
- **PWA Support**: Install as a standalone app on supported devices
- **Offline Capability**: Basic functionality works offline through service worker caching

## Quick Start

### Prerequisites

- Python 3.7+ 
- pip (Python package manager)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/fpl-analyzer.git
   cd fpl-analyzer
   ```

2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python app.py
   ```

4. Open your browser and navigate to:
   ```
   http://localhost:5050
   ```

### Using the Application

1. Enter your FPL mini-league ID in the Settings tab
2. Navigate to the Stats tab to view league statistics
3. Use the gameweek selector to view data from different gameweeks

### Generating App Icons (Optional)

If you want to customize the app icons:

1. Replace the logo image at `static/assets/logo.png`
2. Run the icon generator script:
   ```
   python generate_ios_assets.py
   ```

## Technical Details

- **Backend**: Python Flask
- **Frontend**: HTML, CSS, JavaScript
- **API**: Fantasy Premier League official API
- **PWA Features**: Service Worker, Manifest, Offline Support

## License

This project is open-source and available under the MIT License.

## Acknowledgments

- Fantasy Premier League API
- Flask web framework
- The FPL community for inspiration