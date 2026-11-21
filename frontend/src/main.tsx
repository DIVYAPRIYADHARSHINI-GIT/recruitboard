import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './styles.css';

const stored = localStorage.getItem('recruitboard-theme');
document.documentElement.dataset.theme = stored === 'dark' ? 'dark' : 'light';
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><BrowserRouter><App/></BrowserRouter></React.StrictMode>);