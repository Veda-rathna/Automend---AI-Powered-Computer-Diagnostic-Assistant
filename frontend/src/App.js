import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import DiagnosisPage from './pages/DiagnosisPage';
import HardwareProtection from './pages/HardwareProtection';
import ServiceCenters from './pages/ServiceCenters';
import CompatibilityChecker from './pages/CompatibilityChecker';
import About from './pages/About';
import './App.css';

function App() {

  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/diagnosis" element={<DiagnosisPage />} />
          <Route path="/hardware-protection" element={<HardwareProtection />} />
          <Route path="/service-centers" element={<ServiceCenters />} />
          <Route path="/compatibility-checker" element={<CompatibilityChecker />} />
          <Route path="/about" element={<About />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
