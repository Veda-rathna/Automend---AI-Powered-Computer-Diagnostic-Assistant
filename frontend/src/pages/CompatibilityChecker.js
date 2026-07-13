import React, { useState, useEffect } from 'react';
import './CompatibilityChecker.css';

function CompatibilityChecker() {
  const [activeTab, setActiveTab] = useState('scan'); // 'scan', 'check', 'recommend'
  const [loading, setLoading] = useState(false);

  // Helper function to format AI response text
  const formatAnalysisText = (text) => {
    if (!text) return '';
    
    // Convert markdown-style headers to HTML
    let formatted = text
      .replace(/### (.*?)(\n|$)/g, '<h3>$1</h3>')
      .replace(/## (.*?)(\n|$)/g, '<h2>$1</h2>')
      .replace(/# (.*?)(\n|$)/g, '<h1>$1</h1>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code>$1</code>')
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br />');
    
    return `<p>${formatted}</p>`;
  };
  const [systemSpecs, setSystemSpecs] = useState(null);
  const [missingFields, setMissingFields] = useState([]);
  const [userInputs, setUserInputs] = useState({
    psu: { wattage: '', efficiency: '' },
    case: { form_factor: '', gpu_clearance_mm: '' },
    motherboard: { ram_slots: '', max_ram_gb: '' },
  });
  
  // Compatibility Check State
  const [proposedUpgrade, setProposedUpgrade] = useState('');
  const [compatibilityResult, setCompatibilityResult] = useState(null);
  
  // Recommendations State
  const [budget, setBudget] = useState('');
  const [upgradeGoal, setUpgradeGoal] = useState('general performance');
  const [recommendations, setRecommendations] = useState(null);

  // Scan hardware on component mount
  useEffect(() => {
    if (activeTab === 'scan' && !systemSpecs) {
      scanHardware();
    }
  }, [activeTab, systemSpecs]);

  const scanHardware = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/compatibility/scan/');
      const data = await response.json();
      
      if (data.success) {
        setSystemSpecs(data.hardware_specs);
        setMissingFields(data.missing_fields || []);
      } else {
        alert('Failed to scan hardware: ' + data.error);
      }
    } catch (error) {
      alert('Error scanning hardware: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const checkCompatibility = async () => {
    if (!proposedUpgrade.trim()) {
      alert('Please enter the upgrade you want to check');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/compatibility/check/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          current_system: systemSpecs,
          proposed_upgrade: {
            description: proposedUpgrade,
          },
          user_inputs: userInputs,
        }),
      });

      const data = await response.json();
      
      if (data.success) {
        setCompatibilityResult(data);
      } else {
        alert('Failed to check compatibility: ' + data.error);
      }
    } catch (error) {
      alert('Error checking compatibility: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const getRecommendations = async () => {
    if (!budget || isNaN(budget)) {
      alert('Please enter a valid budget');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/compatibility/recommendations/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          current_system: systemSpecs,
          budget: parseFloat(budget),
          goal: upgradeGoal,
          user_inputs: userInputs,
        }),
      });

      const data = await response.json();
      
      if (data.success) {
        setRecommendations(data);
      } else {
        alert('Failed to get recommendations: ' + data.error);
      }
    } catch (error) {
      alert('Error getting recommendations: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleUserInput = (category, field, value) => {
    setUserInputs(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [field]: value,
      },
    }));
  };

  const renderSystemSpecs = () => {
    if (!systemSpecs) return null;

    return (
      <div className="system-specs">
        <h3>🖥️ Detected Hardware</h3>
        
        <div className="spec-section">
          <h4>Processor (CPU)</h4>
          <div className="spec-details">
            <p><strong>Model:</strong> {systemSpecs.cpu?.model || 'Unknown'}</p>
            <p><strong>Cores:</strong> {systemSpecs.cpu?.cores} / <strong>Threads:</strong> {systemSpecs.cpu?.threads}</p>
            {systemSpecs.cpu?.socket && <p><strong>Socket:</strong> {systemSpecs.cpu.socket}</p>}
            {systemSpecs.cpu?.base_clock_ghz && <p><strong>Clock:</strong> {systemSpecs.cpu.base_clock_ghz} GHz</p>}
          </div>
        </div>

        <div className="spec-section">
          <h4>Memory (RAM)</h4>
          <div className="spec-details">
            <p><strong>Total:</strong> {systemSpecs.ram?.total_gb} GB</p>
            <p><strong>Used:</strong> {systemSpecs.ram?.used_gb} GB ({systemSpecs.ram?.percentage_used}%)</p>
            {systemSpecs.ram?.type && <p><strong>Type:</strong> {systemSpecs.ram.type}</p>}
            {systemSpecs.ram?.speed_mhz && <p><strong>Speed:</strong> {systemSpecs.ram.speed_mhz} MHz</p>}
            {systemSpecs.ram?.slots_used && <p><strong>Slots Used:</strong> {systemSpecs.ram.slots_used}</p>}
          </div>
        </div>

        <div className="spec-section">
          <h4>Graphics (GPU)</h4>
          {systemSpecs.gpu && systemSpecs.gpu.length > 0 ? (
            systemSpecs.gpu.map((gpu, idx) => (
              <div key={idx} className="spec-details">
                <p><strong>Model:</strong> {gpu.model}</p>
                {gpu.manufacturer && <p><strong>Manufacturer:</strong> {gpu.manufacturer}</p>}
                {gpu.vram_gb && <p><strong>VRAM:</strong> {gpu.vram_gb} GB</p>}
              </div>
            ))
          ) : (
            <p>No dedicated GPU detected</p>
          )}
        </div>

        <div className="spec-section">
          <h4>Motherboard</h4>
          <div className="spec-details">
            {systemSpecs.motherboard?.manufacturer && (
              <p><strong>Manufacturer:</strong> {systemSpecs.motherboard.manufacturer}</p>
            )}
            {systemSpecs.motherboard?.model && (
              <p><strong>Model:</strong> {systemSpecs.motherboard.model}</p>
            )}
            {systemSpecs.motherboard?.bios_version && (
              <p><strong>BIOS:</strong> {systemSpecs.motherboard.bios_version}</p>
            )}
          </div>
        </div>

        {systemSpecs.power_requirements && (
          <div className="spec-section power-section">
            <h4>⚡ Power Requirements</h4>
            <div className="spec-details">
              <p><strong>Estimated TDP:</strong> {systemSpecs.power_requirements.estimated_tdp_watts}W</p>
              <p><strong>Recommended PSU:</strong> {systemSpecs.power_requirements.recommended_psu_min}W - {systemSpecs.power_requirements.recommended_psu_ideal}W</p>
              <p><strong>Efficiency:</strong> {systemSpecs.power_requirements.efficiency_recommendation}</p>
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderMissingFields = () => {
    if (missingFields.length === 0) return null;

    return (
      <div className="missing-fields">
        <h3>📝 Additional Information Needed</h3>
        <p className="info-text">
          Some hardware details couldn't be auto-detected. Please fill in the information below:
        </p>

        <div className="input-grid">
          <div className="input-group">
            <label>PSU Wattage (e.g., 650)</label>
            <input
              type="number"
              placeholder="650"
              value={userInputs.psu.wattage}
              onChange={(e) => handleUserInput('psu', 'wattage', e.target.value)}
            />
          </div>

          <div className="input-group">
            <label>PSU Efficiency (e.g., 80+ Gold)</label>
            <input
              type="text"
              placeholder="80+ Gold"
              value={userInputs.psu.efficiency}
              onChange={(e) => handleUserInput('psu', 'efficiency', e.target.value)}
            />
          </div>

          <div className="input-group">
            <label>Case Form Factor</label>
            <select
              value={userInputs.case.form_factor}
              onChange={(e) => handleUserInput('case', 'form_factor', e.target.value)}
            >
              <option value="">Select...</option>
              <option value="Mini-ITX">Mini-ITX</option>
              <option value="Micro-ATX">Micro-ATX</option>
              <option value="ATX">ATX (Standard)</option>
              <option value="E-ATX">E-ATX (Extended)</option>
              <option value="Full Tower">Full Tower</option>
            </select>
          </div>

          <div className="input-group">
            <label>GPU Clearance (mm)</label>
            <input
              type="number"
              placeholder="320"
              value={userInputs.case.gpu_clearance_mm}
              onChange={(e) => handleUserInput('case', 'gpu_clearance_mm', e.target.value)}
            />
          </div>

          <div className="input-group">
            <label>Motherboard RAM Slots</label>
            <input
              type="number"
              placeholder="4"
              value={userInputs.motherboard.ram_slots}
              onChange={(e) => handleUserInput('motherboard', 'ram_slots', e.target.value)}
            />
          </div>

          <div className="input-group">
            <label>Max RAM Capacity (GB)</label>
            <input
              type="number"
              placeholder="64"
              value={userInputs.motherboard.max_ram_gb}
              onChange={(e) => handleUserInput('motherboard', 'max_ram_gb', e.target.value)}
            />
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="compatibility-checker">
      <div className="page-header">
        <h1>🔧 PC Upgrade Compatibility Checker</h1>
        <p>Check if upgrades are compatible with your system and get AI-powered recommendations</p>
      </div>

      <div className="tabs">
        <button
          className={`tab ${activeTab === 'scan' ? 'active' : ''}`}
          onClick={() => setActiveTab('scan')}
        >
          📊 Scan System
        </button>
        <button
          className={`tab ${activeTab === 'check' ? 'active' : ''}`}
          onClick={() => setActiveTab('check')}
        >
          ✅ Check Compatibility
        </button>
        <button
          className={`tab ${activeTab === 'recommend' ? 'active' : ''}`}
          onClick={() => setActiveTab('recommend')}
        >
          💡 Get Recommendations
        </button>
      </div>

      <div className="tab-content">
        {/* SCAN TAB */}
        {activeTab === 'scan' && (
          <div className="scan-tab">
            <div className="action-section">
              <button
                className="primary-button"
                onClick={scanHardware}
                disabled={loading}
              >
                {loading ? 'Scanning...' : '🔍 Scan My PC'}
              </button>
              <p className="help-text">
                This will auto-detect your hardware specifications
              </p>
            </div>

            {systemSpecs && renderSystemSpecs()}
            {systemSpecs && renderMissingFields()}
          </div>
        )}

        {/* COMPATIBILITY CHECK TAB */}
        {activeTab === 'check' && (
          <div className="check-tab">
            {!systemSpecs ? (
              <div className="warning-box">
                <p>⚠️ Please scan your system first in the "Scan System" tab</p>
              </div>
            ) : (
              <>
                <div className="upgrade-input-section">
                  <h3>What do you want to upgrade?</h3>
                  <textarea
                    className="upgrade-input"
                    placeholder="Example: NVIDIA RTX 4070 Ti&#10;Example: 32GB DDR5 RAM (2x16GB)&#10;Example: AMD Ryzen 7 7800X3D"
                    value={proposedUpgrade}
                    onChange={(e) => setProposedUpgrade(e.target.value)}
                    rows={4}
                  />
                  <button
                    className="primary-button"
                    onClick={checkCompatibility}
                    disabled={loading}
                  >
                    {loading ? 'Analyzing...' : '🔍 Check Compatibility'}
                  </button>
                </div>

                {compatibilityResult && (
                  <div className={`result-box ${compatibilityResult.compatible ? 'success' : 'warning'}`}>
                    <div className="result-header">
                      <h3>
                        {compatibilityResult.compatible ? '✅ Compatible!' : '⚠️ Compatibility Issues'}
                      </h3>
                    </div>
                    <div className="result-content">
                      <div 
                        className="analysis-text"
                        dangerouslySetInnerHTML={{ __html: formatAnalysisText(compatibilityResult.analysis) }}
                      />
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* RECOMMENDATIONS TAB */}
        {activeTab === 'recommend' && (
          <div className="recommend-tab">
            {!systemSpecs ? (
              <div className="warning-box">
                <p>⚠️ Please scan your system first in the "Scan System" tab</p>
              </div>
            ) : (
              <>
                <div className="recommendations-input-section">
                  <h3>Get Personalized Upgrade Recommendations</h3>
                  
                  <div className="input-row">
                    <div className="input-group">
                      <label>Budget (INR)</label>
                      <input
                        type="number"
                        placeholder="40000"
                        value={budget}
                        onChange={(e) => setBudget(e.target.value)}
                      />
                    </div>

                    <div className="input-group">
                      <label>Upgrade Goal</label>
                      <select
                        value={upgradeGoal}
                        onChange={(e) => setUpgradeGoal(e.target.value)}
                      >
                        <option value="general performance">General Performance</option>
                        <option value="gaming">Gaming</option>
                        <option value="content creation">Content Creation</option>
                        <option value="video editing">Video Editing</option>
                        <option value="3d rendering">3D Rendering</option>
                        <option value="programming">Programming/Development</option>
                        <option value="streaming">Streaming</option>
                        <option value="workstation">Workstation</option>
                      </select>
                    </div>
                  </div>

                  <button
                    className="primary-button"
                    onClick={getRecommendations}
                    disabled={loading}
                  >
                    {loading ? 'Analyzing...' : '💡 Get Recommendations'}
                  </button>
                </div>

                {recommendations && (
                  <div className="result-box recommendations-result">
                    <div className="result-header">
                      <h3>💡 Upgrade Recommendations</h3>
                    </div>
                    <div className="result-content">
                      <div className="recommendation-meta">
                        <p><strong>Budget:</strong> ₹{recommendations.budget.toLocaleString('en-IN')}</p>
                        <p><strong>Goal:</strong> {recommendations.goal}</p>
                      </div>
                      <div 
                        className="analysis-text"
                        dangerouslySetInnerHTML={{ __html: formatAnalysisText(recommendations.recommendations) }}
                      />
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default CompatibilityChecker;
