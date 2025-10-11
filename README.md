# FurNet

A simple full-stack web application with FastAPI backend and React + Tailwind CSS + Vite frontend.

## TLDR - Quick Start

**Backend:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip3 install -r requirements.txt
uvicorn main:app --reload
```

**Frontend (in a new terminal):**
```bash
cd frontend
npm install
npm run dev
```

Then open `http://localhost:5173` in your browser.

## Project Structure

```
furnet/
├── backend/                # FastAPI backend
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py      # API routes
│   ├── main.py            # FastAPI application
│   ├── requirements.txt   # Python dependencies
│   └── .env.example       # Environment variables template
├── frontend/              # React frontend
│   ├── src/
│   │   ├── components/
│   │   │   └── ItemList.jsx
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── postcss.config.js
├── CLAUDE.md              # AI assistant context
└── README.md              # This file
```

## Features

- **FastAPI Backend**: RESTful API with automatic documentation
- **React Frontend**: Modern React with hooks
- **Tailwind CSS**: Utility-first CSS framework
- **Vite**: Fast development server and build tool
- **CORS Configured**: Backend ready for frontend communication
- **Proxy Setup**: Vite configured to proxy API requests

## Prerequisites

- Python 3.12+
- Node.js 22+
- npm or yarn

## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:
```bash
# On macOS/Linux
source venv/bin/activate

# On Windows
venv\Scripts\activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. (Optional) Create a `.env` file from `.env.example`:
```bash
cp .env.example .env
```

6. Start the FastAPI server:
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Usage

Once both servers are running:

1. Open your browser to `http://localhost:5173`
2. You should see the FurNet homepage with a list of items
3. Items are fetched from the FastAPI backend
4. You can delete items by clicking the "Delete" button
5. Refresh the list with the "Refresh" button

## API Endpoints

### Base Endpoints
- `GET /` - Welcome message
- `GET /health` - Health check

### Items API
- `GET /api/items` - Get all items
- `GET /api/items/{item_id}` - Get a specific item
- `POST /api/items` - Create a new item
- `DELETE /api/items/{item_id}` - Delete an item

## Development

### Backend Development

The FastAPI server runs with hot reload enabled. Any changes to Python files will automatically restart the server.

To run tests (after setting them up):
```bash
pytest
```

### Frontend Development

The Vite dev server provides hot module replacement (HMR). Changes to React components will update in the browser instantly.

To build for production:
```bash
npm run build
```

To preview the production build:
```bash
npm run preview
```

## Technology Stack

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **Uvicorn**: ASGI server for running FastAPI
- **Pydantic**: Data validation using Python type hints

### Frontend
- **React 19**: UI library with hooks
- **Vite 6**: Next generation frontend tooling
- **Tailwind CSS**: Utility-first CSS framework
- **Axios**: (Available) HTTP client for API requests

## Next Steps

- Add authentication and user management
- Implement a database (PostgreSQL, MongoDB, etc.)
- Add form validation
- Create more CRUD operations
- Add unit and integration tests
- Set up CI/CD pipeline
- Deploy to production (Vercel, Railway, etc.)

## License

MIT
