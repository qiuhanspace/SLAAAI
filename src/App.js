import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';

// Import your components/pages
import Header from './components/Header';
import Home from './pages/Home';
import UploadMeal from './pages/UploadMeal';
import MealHistorySimple from './pages/MealHistorySimple';

function App() {
  return (
    <Router>
      <div className="App">
        <Header />
        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/upload" element={<UploadMeal />} />
            <Route path="/history" element={<MealHistorySimple />} />
          </Routes>
        </main>
        <footer className="py-3 mt-4 text-center">
          <p>© 2023 Healthy Meal Analyzer</p>
        </footer>
      </div>
    </Router>
  );
}

export default App; 