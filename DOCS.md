# AI-Driven PC Diagnostic Assistant - Complete Documentation

**Last Updated:** January 7, 2026

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Setup Guide](#setup-guide)
3. [Architecture & Integration](#architecture--integration)
4. [Troubleshooting & Fixes](#troubleshooting--fixes)
5. [Development History](#development-history)

---

## Project Overview

An intelligent, full-stack application that leverages AI and AutoGen agents to diagnose PC issues through natural conversation. Built with Django REST Framework backend and React frontend.

### Key Features
- AI-driven conversational PC diagnostics
- Multi-agent system using AutoGen framework
- Real-time hardware telemetry collection
- **PC Upgrade Compatibility Checker** - Check component compatibility and get upgrade recommendations
- Google Gemini integration with intelligent fallbacks
- Automated report generation
- Service center recommendations

### Tech Stack
- **Backend:** Django 4.2+, Django REST Framework
- **Frontend:** React 18+, Modern UI components
- **AI:** Google Gemini 2.5, AutoGen, LLaMA (fallback)
- **Hardware Monitoring:** psutil, LibreHardwareMonitor (optional)

---

## Setup Guide

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git
- Google Gemini API key (optional but recommended)

### Backend Setup

1. **Navigate to backend directory:**
   ```powershell
   cd backend
   ```

2. **Create and activate virtual environment:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   - Copy `.env.example` to `.env`
   - Add your Gemini API key:
     ```env
     GEMINI_API_KEY=your_api_key_here
     GEMINI_MODEL=gemini-2.0-flash-exp
     ```

5. **Run migrations:**
   ```powershell
   python manage.py migrate
   ```

6. **Start the server:**
   ```powershell
   python manage.py runserver
   ```

### Frontend Setup

1. **Navigate to frontend directory:**
   ```powershell
   cd frontend
   ```

2. **Install dependencies:**
   ```powershell
   npm install
   ```

3. **Start development server:**
   ```powershell
   npm start
   ```

4. **Access the application:**
   Open `http://localhost:3000` in your browser

### Testing the Integration

Test the API endpoint:
```powershell
$body = @{ query = "My computer is running slow" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/predict/" -Method POST -Body $body -ContentType "application/json"
```

---

## Architecture & Integration

### System Architecture

```
┌─────────────────┐
│  React Frontend │
│  (Port 3000)    │
└────────┬────────┘
         │ HTTP/REST
         ▼
┌─────────────────┐
│ Django Backend  │
│  (Port 8000)    │
└────────┬────────┘
         │
         ├─────► Hardware Telemetry
         │       (psutil, LibreHardwareMonitor)
         │
         ├─────► LLM Provider Chain
         │       ├─ Google Gemini (Primary)
         │       ├─ Local LLaMA (Fallback #1)
         │       └─ Mock Analysis (Fallback #2)
         │
         └─────► AutoGen Multi-Agent System
                 ├─ User Proxy Agent
                 ├─ Diagnostic Agent
                 ├─ Hardware Specialist
                 └─ Software Specialist
```

### LLM Fallback Chain

The system implements a robust three-tier fallback mechanism:

1. **Google Gemini (Primary)**
   - Cloud-based, cutting-edge AI
   - Fast and accurate diagnostics
   - Requires API key

2. **Local LLaMA (Fallback #1)**
   - Privacy-focused, offline-capable
   - Runs locally if Gemini fails
   - No API key required

3. **Offline Mock Engine (Fallback #2)**
   - Rule-based analysis
   - Guaranteed uptime
   - Basic diagnostics without AI

### Key Backend Components

- **`pc_diagnostic/views.py`**: Main prediction endpoint and compatibility checking
- **`pc_diagnostic/hardware_compatibility.py`**: Hardware detection and compatibility analysis
- **`pc_diagnostic/llm/`**: LLM provider implementations
- **`pc_diagnostic/advanced_telemetry.py`**: Hardware monitoring
- **`autogen_integration/`**: Multi-agent orchestration
- **`ai_diagnostic/`**: Core diagnostic logic

### Key Frontend Components

- **`src/App.js`**: Main application component with routing
- **`src/pages/CompatibilityChecker.js`**: PC upgrade compatibility checker
- **`src/components/`**: UI components
- **`src/pages/`**: Page layouts

---

## Troubleshooting & Fixes

### Critical Fixes Applied

#### Fix #1: Indentation Error in views.py (January 4, 2026)

**Problem:**
- 140+ lines of response-building code were indented inside an unreachable code block
- After `if not prediction: return ...`, the rest of the function was never executed
- Gemini API worked but responses were never returned

**Solution:**
- Fixed indentation in `backend/pc_diagnostic/views.py` lines 365-507
- Moved response-building code to correct scope
- All LLM providers now return results properly

#### Fix #2: Unicode Encoding Error (January 4, 2026)

**Problem:**
- Emoji characters in print statements (🤖, ✅, 🔧, etc.)
- Windows PowerShell uses cp1252 encoding (doesn't support emojis)
- Server crashed during initialization with `UnicodeEncodeError`

**Solution:**
- Replaced all emoji characters with text equivalents
- Added `.encode('ascii', 'ignore')` where needed
- Server now starts successfully on Windows

#### Fix #3: CORS Configuration

**Problem:**
- React frontend couldn't communicate with Django backend
- CORS errors in browser console

**Solution:**
- Installed `django-cors-headers`
- Added to `INSTALLED_APPS` and `MIDDLEWARE`
- Configured `CORS_ALLOWED_ORIGINS` for localhost:3000

#### Fix #4: Cache Issues

**Problem:**
- Old code cached in `__pycache__` directories
- Changes not reflecting after code updates

**Solution:**
```powershell
# Clear Python cache
Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force
```

### Common Issues

#### "Gemini API not working"

1. Check API key in `.env` file
2. Verify key is active at [Google AI Studio](https://aistudio.google.com/app/apikey)
3. Check server logs for errors
4. Test with: `python backend/test_gemini_direct.py`

#### "Service Unavailable" errors

1. Ensure backend is running on port 8000
2. Check CORS configuration
3. Clear browser cache
4. Verify frontend is calling correct endpoint

#### "Hardware telemetry not collecting"

1. Install psutil: `pip install psutil`
2. For advanced monitoring, install LibreHardwareMonitor
3. Run with administrator privileges (for some sensors)

---

## Development History

### Project Evolution

**Phase 1: Initial Setup (December 2025)**
- Created Django backend with REST API
- Built React frontend with chat interface
- Implemented basic diagnostic endpoint

**Phase 2: AI Integration (January 2026)**
- Integrated Google Gemini API
- Implemented LLM fallback chain
- Added AutoGen multi-agent system

**Phase 3: Bug Fixes & Optimization (January 4-5, 2026)**
- Fixed critical indentation error
- Resolved Unicode encoding issues
- Optimized LLM provider initialization
- Improved error handling

**Phase 4: Documentation Consolidation (January 7, 2026)**
- Cleaned up redundant documentation files
- Created comprehensive DOCS.md
- Streamlined project structure

**Phase 5: PC Upgrade Compatibility Checker (February 15, 2026)**
- Added comprehensive hardware detection and specification scanning
- Implemented AI-powered upgrade compatibility checking
- Created upgrade recommendation engine
- Built interactive frontend page with tabbed interface
- Integrated power requirement calculations
- Added socket detection for Intel/AMD CPUs
- Implemented RAM, GPU, and storage detection

### Verification Checklist

After setup, verify:
- ✅ Backend starts without errors
- ✅ Frontend loads at localhost:3000
- ✅ API endpoint responds to test queries
- ✅ Gemini API is being used (check response notes)
- ✅ Hardware telemetry collects successfully
- ✅ Chat interface sends/receives messages

### Testing Commands

**Test Gemini Integration:**
```powershell
python backend/test_gemini_direct.py
```

**Test API Endpoint:**
```powershell
python backend/test_predict_api.py
```

**Test LLM Connection:**
```powershell
python backend/test_llm_connection.py
```

**Test Fallback Order:**
```powershell
python backend/test_fallback_order.py
```

---

## Additional Resources

- **Main README:** See `README.md` for feature overview
- **Backend Setup:** See `backend/requirements.txt` for dependencies
- **Frontend Features:** See `frontend/README.md` for React app details
- **AutoGen Integration:** See `backend/autogen_integration/README.md`

---

## Support & Contribution

For issues, improvements, or questions:
1. Check this documentation first
2. Review the main README.md
3. Check server logs in terminal
4. Test individual components with provided scripts

---

**End of Documentation**
