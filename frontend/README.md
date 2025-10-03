# Trip Planner Frontend

A modern React frontend for the AI-powered trip planning API.

## Features

- 🎯 **Interactive Trip Planning Form** - Comprehensive form for trip details, travellers, and preferences
- 🏨 **Smart Selection Interface** - Interactive selection of lodging, activities, food, and transport options
- 📊 **Real-time Results Display** - Beautiful display of planning results with budget estimates and recommendations
- 🔄 **Seamless Workflow** - Handles the complete planning workflow from start to finish
- 📱 **Responsive Design** - Works perfectly on desktop and mobile devices
- ⚡ **Modern Tech Stack** - Built with React, TypeScript, and Tailwind CSS

## Tech Stack

- **React 18** with TypeScript
- **Tailwind CSS** for styling
- **React Hook Form** for form management
- **Axios** for API communication
- **React Query** for state management

## Getting Started

### Prerequisites

- Node.js 16+ and npm
- Backend API running on http://localhost:8000

### Installation

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm start
```

3. Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

### Building for Production

```bash
npm run build
```

This builds the app for production to the `build` folder.

## API Integration

The frontend integrates with the following API endpoints:

- `POST /plan/start` - Start a new trip planning session
- `POST /plan/resume` - Resume planning after user selections
- `GET /health` - Health check endpoint

## Project Structure

```
src/
├── components/          # React components
│   ├── TripForm.tsx    # Trip planning form
│   ├── PlanningResults.tsx # Results display
│   ├── SelectionInterface.tsx # User selection interface
│   ├── LoadingSpinner.tsx
│   └── ErrorMessage.tsx
├── hooks/              # Custom React hooks
│   ├── useTripPlanning.ts
│   └── useApi.ts
├── services/           # API services
│   └── api.ts
├── types/              # TypeScript type definitions
│   └── api.ts
├── App.tsx             # Main application component
├── index.tsx           # Application entry point
└── index.css           # Global styles
```

## Usage

1. **Fill out the trip form** with destination, dates, budget, and traveller information
2. **Submit the form** to start the AI planning process
3. **Review the results** including budget estimates and recommendations
4. **Make selections** if the workflow requires user input
5. **Continue planning** until the final itinerary is complete

## Environment Variables

Create a `.env` file in the root directory:

```
REACT_APP_API_URL=http://localhost:8000
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.

