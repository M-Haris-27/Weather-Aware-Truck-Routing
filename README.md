# Weather-Aware Truck Routing

A full-stack React + Django application that helps truck drivers choose the safest route based on weather conditions, load weight, and travel time. Built as a technical assessment demonstrating modern web development practices, API integration, and real-world problem solving.

## 🚀 Live Demo

- **Frontend:** https://weather-aware-truck-routing-flame.vercel.app
- **Backend API:** https://weather-aware-truck-routing-ip71.onrender.com

## 📋 Overview

The application generates up to three alternative routes between origin and destination, forecasts weather conditions at checkpoints **for the exact hour the truck will arrive**, calculates risk levels using weather thresholds and load rules, and recommends the safest route. The interactive map displays all routes, checkpoints with detailed weather data, and a 48-hour weather heatmap with an animated slider.

### Architecture

```
React (Vite + TypeScript + MapLibre GL)
              ↓
      Django REST API
              ↓
    ┌─────────┴─────────┐
    ↓                   ↓
Mapbox Directions    Open-Meteo
& Geocoding          Weather API
    ↓                   ↓
Risk Calculation Engine (Pure Python, 105+ Unit Tests)
              ↓
    Route Recommendation
```

## 🎯 Key Features

✅ **3 Route Alternatives** - Generates multiple route options using Mapbox Directions API  
✅ **Smart Checkpoint Placement** - Samples weather every 10/25/50 miles (automatic based on route length)  
✅ **Time-Aware Weather Forecasting** - Fetches weather for the exact estimated arrival time at each checkpoint  
✅ **Load-Based Risk Calculation** - Applies wind/rain/snow thresholds and heavy load rules  
✅ **Intelligent Route Recommendation** - Ranks routes by: Severe miles → High miles → Avg risk → Travel time  
✅ **Interactive Map** - MapLibre GL with custom layers for routes, checkpoints, and risk visualization  
✅ **48-Hour Weather Heatmap** - Animated slider showing risk evolution along the trip corridor  
✅ **Real-Time Autocomplete** - Geocoding with instant suggestions as you type  
✅ **Responsive Design** - Works on desktop, tablet, and mobile  

## 🛠️ Tech Stack

### Frontend
- **React 18** with TypeScript
- **Vite** for fast development and optimized builds
- **MapLibre GL** for interactive mapping
- **TanStack Query** for API state management
- **Vitest** for unit testing (18 tests)

### Backend
- **Django 5** with Django REST Framework
- **Python 3.11+** with type hints
- **Gunicorn** production server
- **pytest** for unit testing (105 tests, 100% coverage on domain logic)
- **Domain-Driven Design** - Business logic separated from framework

### APIs & Services
- **Mapbox Directions API** - Route generation and geocoding
- **Open-Meteo** - Free weather forecast data (or mock for demo)
- **Vercel** - Frontend hosting with automatic deployments
- **Render** - Backend API hosting with environment management

## 💻 Local Development

### Prerequisites
- Python 3.10 or higher
- Node.js 18 or higher
- Git

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your MAPBOX_ACCESS_TOKEN

# Run development server
python manage.py runserver
```

Backend will be available at **http://localhost:8000**

**API Endpoints:**
- `GET /api/health` - Health check and provider status
- `GET /api/geocode?q=query` - Location search autocomplete
- `POST /api/analyze` - Route analysis (main endpoint)

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend will be available at **http://localhost:5173**

Vite automatically proxies `/api/*` requests to the Django backend, so no CORS configuration needed in development.

### Running Without API Keys

Set these in `backend/.env` for offline development:
```env
ROUTING_PROVIDER=mock
GEOCODING_PROVIDER=mock
WEATHER_PROVIDER=mock
```

The app works completely offline with deterministic fake data. Mock geocoder includes: Dallas, Denver, Seattle, Atlanta, New York, Washington DC, Chicago, Los Angeles, and more.

### Testing

```bash
# Backend tests (105 tests)
cd backend
pytest

# Frontend tests (18 tests)
cd frontend
npm test

# Type checking
npm run build
```

## 📐 Requirements Implementation

| Assessment Requirement | Implementation | File Location |
|------------------------|----------------|---------------|
| User inputs: Origin, destination, departure, load weight | Search form with geocoding autocomplete | `frontend/src/components/SearchForm.tsx` |
| Generate 3 route options using routing API | Mapbox Directions with alternatives parameter | `backend/routing_app/services/routing/mapbox.py` |
| Sample weather every 10/25/50 miles | Checkpoint algorithm with distance-based sampling | `backend/routing_app/domain/checkpoints.py` |
| Use truck's estimated arrival time | ETA calculation: `departure + (distance/total) * duration` | `backend/routing_app/domain/checkpoints.py:64-72` |
| Calculate risk using provided thresholds | Wind/rain/snow classification per spec | `backend/routing_app/domain/risk.py` |
| Apply load weight rules | Heavy load modifiers (30k, 40k lb thresholds) | `backend/routing_app/domain/risk.py:55-63` |
| Recommend best route | Multi-criteria ranking: Severe → High → Avg risk → Time | `backend/routing_app/domain/recommend.py` |
| Display all routes, checkpoints, ETAs on map | MapLibre GL with custom layers and popups | `frontend/src/components/MapView.tsx` |
| Show 0-48 hour weather heatmap with slider | Client-side animated heatmap (no network) | `frontend/src/components/HeatmapControl.tsx` |

## 🏗️ Architecture & Design Decisions

### Backend Architecture

**Domain-Driven Design**
- Business logic lives in `backend/routing_app/domain/` with zero Django dependencies
- Pure Python functions that are easy to test, reason about, and reuse
- 105 unit tests with 100% coverage on core risk calculation and recommendation logic

**Request Pipeline** (`pipeline.py`)
1. Validate user input (departure time, load weight)
2. Fetch 3 route alternatives from routing provider
3. Generate checkpoints every 10/25/50 miles based on route length
4. Calculate ETA for each checkpoint (constant velocity assumption)
5. Batch-fetch weather for all checkpoints + heatmap points (single API call per 50 locations)
6. Assess risk at each checkpoint using weather + load rules
7. Rank routes by multi-criteria algorithm
8. Return complete analysis with recommendation

**Weather Optimization**
- Batches up to 50 locations per API call (ThreadPoolExecutor with 4 workers)
- Caches results per ~1km grid cell for 30 minutes
- One weather API call covers both checkpoints AND entire 48-hour heatmap
- Retry logic with exponential backoff for 429/5xx errors

**Risk Calculation** (`domain/risk.py`)
- Implements exact thresholds from specification (wind, rain, snow)
- Load weight rules: 55+ mph = No Travel, 45-54 mph + 30k lb = No Travel, 35-44 mph + 40k lb = Severe
- Boundary-value tested: 30,000 lb vs 30,001 lb, 40,000 lb vs 40,001 lb, 54.9 mph vs 55.0 mph
- Returns both risk level AND human-readable explanation

### Frontend Architecture

**Performance Optimizations**
- **Route selection is instant** - Geometry loaded once, selection swaps MapLibre layer filters (no re-render)
- **Checkpoints are map layers, not DOM elements** - Hundreds of markers stay smooth at 60fps
- **Heatmap slider is client-side only** - All 49 hours of data come with initial response, slider never hits network
- **Code splitting** - MapLibre GL is its own chunk (600KB), cached separately from app code

**State Management**
- TanStack Query for server state (automatic caching, deduplication)
- Local React state for UI interactions (map selection, slider position)
- Single source of truth for route data

**Map Implementation**
- MapLibre GL for rendering (free, no token required for tiles)
- OpenFreeMap tiles (community-maintained, free to use)
- Custom layers: heatmap (below labels), routes (2 layers per selection state), checkpoints (circle layers)
- Popups built with DOM for rich formatting (weather icons, risk badges)

### Key Technical Decisions

✅ **Heatmap and checkpoints use identical risk logic** - Both call the same `assess()` function, guaranteeing consistency

✅ **Load weight affects recommendations** - Unit test proves: 30k lb load prefers different route than 45k lb with same weather

✅ **ETA-based weather sampling** - Weather is fetched for the hour the truck arrives, not departure time

✅ **Automatic checkpoint spacing** - Routes ≤150 mi: 10 mi, ≤500 mi: 25 mi, >500 mi: 50 mi (user can override)

✅ **Stateless backend** - No database required, scales horizontally, easy to deploy

✅ **Mock providers for offline development** - Complete app functionality without any API keys

## 📂 Project Structure

```
.
├── backend/                      # Django REST API
│   ├── config/                   # Django settings and URLs
│   │   ├── settings.py           # Environment-based config
│   │   └── urls.py               # API route definitions
│   ├── routing_app/
│   │   ├── domain/               # Pure Python business logic (no Django)
│   │   │   ├── checkpoints.py    # Checkpoint generation algorithm
│   │   │   ├── risk.py           # Weather risk classification
│   │   │   ├── recommend.py      # Route ranking algorithm
│   │   │   ├── scoring.py        # Risk aggregation (miles by level, avg)
│   │   │   └── geometry.py       # Coordinate math (distance, interpolation)
│   │   ├── services/             # External API integrations
│   │   │   ├── routing/          # Mapbox, OpenRouteService, Mock
│   │   │   ├── weather.py        # Open-Meteo with batching & caching
│   │   │   └── geocoding.py      # Location search
│   │   ├── api/                  # REST API layer
│   │   │   ├── views.py          # Endpoints: /analyze, /geocode, /health
│   │   │   ├── serializers.py    # Request validation
│   │   │   └── presenters.py     # Response formatting
│   │   ├── pipeline.py           # Main orchestration logic
│   │   └── tests/                # 105 unit tests
│   ├── requirements.txt          # Python dependencies
│   └── build.sh                  # Render deployment script
│
├── frontend/                     # React SPA
│   ├── src/
│   │   ├── components/           # React components
│   │   │   ├── SearchForm.tsx    # User input with autocomplete
│   │   │   ├── MapView.tsx       # MapLibre GL map with layers
│   │   │   ├── RouteCards.tsx    # Route comparison cards
│   │   │   ├── CheckpointTable.tsx # Detailed weather table
│   │   │   ├── HeatmapControl.tsx # 48-hour slider
│   │   │   └── Legend.tsx        # Risk color legend
│   │   ├── api/                  # Backend API client
│   │   │   ├── client.ts         # HTTP wrapper with error handling
│   │   │   └── types.ts          # TypeScript interfaces
│   │   ├── lib/                  # Utilities
│   │   │   ├── geojson.ts        # GeoJSON builders for map
│   │   │   ├── format.ts         # Date/time/number formatting
│   │   │   ├── risk.ts           # Risk level constants
│   │   │   └── popup.ts          # Map popup HTML builder
│   │   └── App.tsx               # Root component
│   ├── package.json              # npm dependencies
│   ├── vite.config.ts            # Build configuration
│   └── vercel.json               # Vercel deployment config
│
└── README.md                     # This file
```

## 🧪 Testing

### Backend Tests (105 tests)
```bash
cd backend
pytest

# With coverage report
pytest --cov=routing_app --cov-report=html
```

**Test Coverage:**
- ✅ Risk calculation: All boundary conditions (54.9 vs 55 mph, 30000 vs 30001 lb, etc.)
- ✅ Recommendation logic: Multi-criteria sorting, tie-breaking
- ✅ Checkpoint generation: Distance sampling, owned miles calculation
- ✅ Geometry utilities: Distance calculations, point interpolation
- ✅ API endpoints: Request validation, error handling
- ✅ Mock providers: Deterministic fake data generation

### Frontend Tests (18 tests)
```bash
cd frontend
npm test

# Watch mode
npm test -- --watch
```

**Test Coverage:**
- ✅ API client: Error parsing, request formatting
- ✅ Type guards: Runtime validation of API responses
- ✅ Utilities: Date formatting, risk level mapping

## 🚢 Deployment

### Production Deployment

**Frontend (Vercel)**
- Automatic deployments on `git push` to main
- Environment variables configured in Vercel dashboard
- CDN distribution with edge caching
- **Live URL:** https://weather-aware-truck-routing-flame.vercel.app

**Backend (Render)**
- Automatic deployments on `git push` to main
- Gunicorn with 120-second timeout for weather API calls
- Environment variables for API keys and configuration
- **Live URL:** https://weather-aware-truck-routing-ip71.onrender.com

### Environment Variables

**Backend (Render):**
```env
PYTHON_VERSION=3.11.0
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=<random-secret-key>
MAPBOX_ACCESS_TOKEN=<your-mapbox-token>
ROUTING_PROVIDER=mapbox
GEOCODING_PROVIDER=mapbox
WEATHER_PROVIDER=mock  # or open_meteo for production
GEOCODING_COUNTRY=US
WEATHER_CACHE_TTL_SECONDS=1800
THROTTLE_ANALYZE=30/min
THROTTLE_GEOCODE=120/min
```

**Frontend (Vercel):**
```env
VITE_API_URL=https://weather-aware-truck-routing-ip71.onrender.com
```

## 🔍 Assumptions & Design Choices

### Weather Thresholds
- **Lower bounds are inclusive** per specification
- **"No Travel" upper bounds:** wind ≥ 55 mph, rain > 1.00 in/hr, snow > 3.0 in/hr
- **Load rules are strict:** 30,000 lb vs 30,001 lb makes a difference (tested)

### Checkpoint Placement
- Specification says "every 10 / 25 / 50 miles" without specifying when to use which
- **Implementation:** Automatic based on route length (≤150 mi: 10, ≤500 mi: 25, else 50)
- User can override via dropdown (Automatic / 10 / 25 / 50)

### ETA Calculation
- **Constant velocity assumption:** `departure + (checkpoint_distance / total_distance) × total_duration`
- Weather fetched for nearest forecast hour to calculated ETA
- Real-world factors (traffic, rest stops, speed limits) not modeled

### Route Ranking
- **Priority order:** No Travel miles → Severe miles → High miles → Average risk → Travel time
- All values rounded before comparison (prevents float precision from deciding ties)
- **Tie-breaking:** If all metrics equal, first route wins (arbitrary but deterministic)

### Routing Limitations
- Mapbox driving profile is **not truck-specific** (no height/weight/hazmat restrictions)
- OpenRouteService has truck profile but free API limits alternatives on long routes
- For production, recommend paid Mapbox API with truck routing

### Mock Weather
- Deterministic algorithm using `sin(lat × 7 + lon × 5 + hours/9)`
- Generates realistic storm patterns that drift with time
- Same input always produces same output (good for demos)

## 🤝 Contributing

This is an assessment project and not open for contributions. However, if you're building something similar:

1. Fork the repository
2. Review `backend/README.md` for detailed backend documentation
3. Check `frontend/README.md` for frontend setup details
4. Run tests before making changes
5. Follow existing code style and patterns

## 📄 License

This project was created as a technical assessment. See LICENSE file for details.

## 👤 Author

**Muhammad Haris**
- GitHub: [@M-Haris-27](https://github.com/M-Haris-27)

## 🙏 Acknowledgments

- **Mapbox** for routing and geocoding APIs
- **Open-Meteo** for free weather forecast data
- **OpenFreeMap** for free map tiles
