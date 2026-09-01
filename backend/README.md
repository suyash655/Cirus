# CIRUS Backend

This is the FastAPI backend for the CIRUS application.

## Prerequisites

- Python 3.9+
- `pip`

## Getting Started

### 1. Navigate to the backend directory

```bash
cd backend
```

### 2. Set up a virtual environment (Recommended)

Create a virtual environment to keep dependencies isolated:

```bash
python -m venv venv
```

Activate the virtual environment:

**On Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

**On Windows (Command Prompt):**
```cmd
.\venv\Scripts\activate.bat
```

**On macOS/Linux:**
```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

The application requires environment variables to run.

```bash
# Copy the example file to create your local .env file
cp .env.example .env
```
*Note: Make sure to fill in any necessary secrets (like API keys or Database URLs) inside the `.env` file.*

### 5. Run the Server

Start the FastAPI server with live reloading enabled:

```bash
uvicorn app.main:app --reload
```

*Alternatively, you can run:*
```bash
python -m uvicorn app.main:app --reload
```

## API Documentation

Once the server is running, you can access the interactive API documentation at:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
