# DiDi Heatmap Monitoring and Prediction System

This project helps DiDi drivers monitor real-time heatmap data through automated Android phone screenshots and predicts optimal zones for order availability.

## Key Components
- ADB-based Android phone control and screenshot capture
- GPS location extraction and map positioning
- Automated map area stitching for full city coverage
- Orange hexagon detection for order zones
- Time-series data storage and analysis
- Machine learning prediction model
- Web dashboard for real-time and predicted heatmaps

## Development Guidelines
- Use Python 3.8+ for all modules
- Follow modular architecture with clear separation of concerns
- Implement proper error handling for ADB operations
- Use efficient image processing techniques for large map stitching
- Store data in SQLite/PostgreSQL with proper indexing
- Build responsive web interface for mobile access
- Implement proper logging for debugging ADB and image operations

## Project Structure
- `src/` - Main source code
  - `adb/` - Android device control
  - `image/` - Screenshot processing and analysis
  - `gps/` - Location handling
  - `database/` - Data storage operations
  - `ml/` - Machine learning models
  - `web/` - Web interface
- `config/` - Configuration files
- `data/` - Data storage and cache
- `tests/` - Unit and integration tests