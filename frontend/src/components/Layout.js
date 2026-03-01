import React from 'react';
import { NavLink } from 'react-router-dom';
import './Layout.css';

const Layout = ({ children }) => {
  return (
    <div className="layout">
      <header className="top-nav">
        <div className="nav-brand">
          <h1>AutoMend</h1>
        </div>
        
        <nav className="nav-links">
          <NavLink 
            to="/" 
            className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
            end
          >
            <span className="nav-text">Home</span>
          </NavLink>
          
          <NavLink 
            to="/diagnosis" 
            className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
          >
            <span className="nav-text">Diagnosis</span>
          </NavLink>
          
          <NavLink 
            to="/hardware-protection" 
            className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
          >
            <span className="nav-text">Hardware Protection</span>
          </NavLink>
          
          <NavLink 
            to="/service-centers" 
            className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
          >
            <span className="nav-text">Service Centers</span>
          </NavLink>
          
          <NavLink 
            to="/compatibility-checker" 
            className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
          >
            <span className="nav-text">Upgrade Checker</span>
          </NavLink>
          
          <NavLink 
            to="/about" 
            className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
          >
            <span className="nav-text">About</span>
          </NavLink>
        </nav>
      </header>
      
      <main className="main-content">
        {children}
      </main>
    </div>
  );
};

export default Layout;
