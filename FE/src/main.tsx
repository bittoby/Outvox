import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.tsx';
import { installApiKeyHeader } from './services/authBootstrap';
import './index.css';

installApiKeyHeader();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
