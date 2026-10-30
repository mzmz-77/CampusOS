import React from 'react';
import {createRoot} from 'react-dom/client';
import App from './App';
async function start(){if(import.meta.env.VITE_HOSTED_PREVIEW==='true'){const {installPreview}=await import('./preview');installPreview();}createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);}
void start();
if('serviceWorker' in navigator && import.meta.env.PROD)window.addEventListener('load',()=>{navigator.serviceWorker.register('/sw.js').catch(()=>{/* App works without offline shell. */});});
