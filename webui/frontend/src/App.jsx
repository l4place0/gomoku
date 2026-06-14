import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import ErrorBoundary from './components/ErrorBoundary';
import Dashboard from './pages/Dashboard';
import Graph from './pages/Graph';
import Models from './pages/Models';
import Logs from './pages/Logs';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <nav className="sidebar">
          <div className="logo">Gomoku ML</div>
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/graph">Graph</NavLink>
          <NavLink to="/models">Models</NavLink>
          <NavLink to="/logs">Logs</NavLink>
        </nav>
        <main className="content">
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/graph" element={<Graph />} />
              <Route path="/models" element={<Models />} />
              <Route path="/logs" element={<Logs />} />
            </Routes>
          </ErrorBoundary>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
