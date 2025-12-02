# NiceGUI Main Application Setup

## Task: Create NiceGUI main application entry point

### Todo Items:
- [x] Create nicegui_app/main.py with basic structure
- [x] Import NiceGUI components (ui, app)
- [x] Import database config from src.database
- [x] Set up basic app configuration (title, port, host)
- [x] Create home route with header and login button
- [x] Add main execution block

### Requirements:
1. Import NiceGUI: from nicegui import ui, app
2. Import existing database config from: from src.database import get_db
3. Set up basic app configuration:
   - Title: "TJM Time Calendar"
   - Port: 8080
   - Host: 0.0.0.0
4. Create a simple home route (@ui.page('/')) that displays:
   - "TJM Time Calendar System" as a large header
   - "Login" button (no functionality yet, just UI)
5. Add if __name__ == '__main__': ui.run(port=8080, host='0.0.0.0')

### Review:
**Completed**: Created NiceGUI main application entry point

**Changes Made**:
1. Created `nicegui_app/main.py` with minimal structure
2. Imported NiceGUI components (`ui`, `app`) and database config (`get_db`)
3. Set app title to "TJM Time Calendar"
4. Created home route (`/`) with:
   - Large header displaying "TJM Time Calendar System"
   - Login button (UI only, no functionality yet)
   - Centered layout using NiceGUI classes
5. Added main execution block to run on port 8080, host 0.0.0.0

**Notes**:
- Kept implementation minimal as requested
- Used NiceGUI's built-in styling classes for layout
- Database import is ready for future use
- Login button is placeholder for future authentication implementation
