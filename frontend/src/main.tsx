import React from 'react'
import ReactDOM from 'react-dom/client'
import { App } from './app/App'
import './styles/tokens.css'
import './styles/globals.css'

// tokens.css before globals.css — globals.css @tailwind directives reference token variables

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
