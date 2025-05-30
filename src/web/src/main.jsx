import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import '@fontsource/roboto/300.css';
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/500.css';
import '@fontsource/roboto/700.css';
import 'leaflet/dist/leaflet.css';
import './App.css';
import { startMockServer } from './mockServer'

// Start the mock server only in development
if (import.meta.env.VITE_ENV !== 'production') {
  console.log('Initializing mock server for development...');
  startMockServer();
}

console.log('Mounting React application...');
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
