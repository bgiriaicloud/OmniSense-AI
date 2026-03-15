import React, { useState, useEffect, useRef } from 'react';
import { 
  Camera, Mic, Shield, AlertTriangle, Info, Heart, Play, Square, 
  LayoutDashboard, History, BarChart2, Settings, Search, Bell, User,
  MoreVertical, Send, Loader2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAccessibility } from './hooks/useAccessibility';
import './App.css';

const App = () => {
    const {
        safetyLevel, isAnalyzing, speak,
        videoRef, canvasRef, captureAndAnalyze, analyzeAudio, mediaStreamRef,
        startVoiceCommands, stopVoiceCommands, voiceStatus,
        seniorMode, setSeniorMode, language, setLanguage,
        hasStarted, handleStartSystems, handleStopSystems,
        isLiveStreaming, startLiveStream, stopLiveStream,
        isScanning, autoGuidance, setAutoGuidance,
        sensoryProfile, setSensoryProfile
    } = useAccessibility();

    const [isSystemEnabled, setIsSystemEnabled] = useState(false);
    const [activeTab, setActiveTab] = useState('dashboard');
    const [messages, setMessages] = useState([]);
    const [chatInput, setChatInput] = useState('');
    const [activityLog, setActivityLog] = useState([]);
    const [isRecording, setIsRecording] = useState(false);

    // Initial "Enable the system" prompt
    useEffect(() => {
        if (!isSystemEnabled) {
            // Slight delay before speaking to ensure engine is ready
            const timer = setTimeout(() => speak("Please enable the system to begin."), 1000);
            return () => clearTimeout(timer);
        }
    }, [isSystemEnabled, speak]);

    // Handle system initialization
    const handleEnableSystem = () => {
        setIsSystemEnabled(true);
        handleStartSystems('dual'); // Default to dual for full capability
        speak("System enabled. Voice and vision agents are now active.");
        addToLog('SYSTEM', 'INITIALIZED', 'SUCCESS');
    };

    // Log helper
    const addToLog = (type, event, status) => {
        const entry = {
            id: Date.now(),
            type,
            timestamp: new Date().toLocaleTimeString(),
            severity: event === 'HAZARD' ? 'WARNING' : 'INFO',
            status
        };
        setActivityLog(prev => [entry, ...prev].slice(0, 10));
    };

    // Update history/chat from voice/audio
    useEffect(() => {
        if (voiceStatus && voiceStatus !== 'Off' && !voiceStatus.startsWith('Listening') && !voiceStatus.startsWith('Matched')) {
            const text = voiceStatus.startsWith('AI:') ? voiceStatus.substring(4) : voiceStatus;
            setMessages(prev => [...prev, { role: 'assistant', text, id: Date.now() }]);
            addToLog('VOICE', 'COMMAND', 'SUCCESS');
        }
    }, [voiceStatus]);

    const handleSendChat = async () => {
        if (!chatInput.trim()) return;
        const userMsg = { role: 'user', text: chatInput, id: Date.now() };
        setMessages(prev => [...prev, userMsg]);
        const query = chatInput;
        setChatInput('');

        // Trigger vision analysis with user query
        addToLog('CHAT', 'QUERY', 'PROCESSING');
        const result = await captureAndAnalyze(query);
        if (result) {
            addToLog('CHAT', 'RESPONSE', 'SUCCESS');
        }
    };

    const handleAudioListen = async () => {
        if (isRecording || isAnalyzing) return;
        if (!mediaStreamRef.current) return;

        setIsRecording(true);
        addToLog('AUDIO', 'LISTENING', 'ACTIVE');
        
        const recorder = new MediaRecorder(mediaStreamRef.current, { mimeType: 'audio/webm' });
        const chunks = [];
        recorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };
        recorder.onstop = async () => {
            const blob = new Blob(chunks, { type: 'audio/webm' });
            const result = await analyzeAudio(blob);
            setIsRecording(false);
            if (result) {
                setMessages(prev => [...prev, { 
                    role: 'assistant', 
                    text: `Sound detected: ${result.sound_event}. ${result.guidance}`, 
                    id: Date.now() 
                }]);
                addToLog('AUDIO', 'EVENT', 'PROCESSED');
            }
        };
        recorder.start();
        setTimeout(() => recorder.stop(), 3000);
    };

    if (!isSystemEnabled) {
        return (
            <div className="enable-overlay">
                <Shield size={100} color="var(--primary)" />
                <h1 style={{fontSize: '3rem', margin: 0}}>Omniscience AI</h1>
                <p style={{opacity: 0.6, fontSize: '1.2rem'}}>Secure Multimodal Accessibility Engine</p>
                <button className="enable-btn" onClick={handleEnableSystem}>
                    ENABLE SYSTEM
                </button>
            </div>
        );
    }

    return (
        <div className="app-layout">
            {/* Left Sidebar */}
            <aside className="sidebar">
                <div className="logo">
                    <Shield size={24} color="var(--primary)" fill="var(--primary)" />
                    <span>Omniscience AI</span>
                </div>

                <nav className="nav-section">
                    <button className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>
                        <LayoutDashboard size={18} /> Dashboard
                    </button>
                    <button className={`nav-item ${activeTab === 'history' ? 'active' : ''}`} onClick={() => setActiveTab('history')}>
                        <History size={18} /> History
                    </button>
                    <button className={`nav-item ${activeTab === 'analytics' ? 'active' : ''}`} onClick={() => setActiveTab('analytics')}>
                        <BarChart2 size={18} /> Analytics
                    </button>
                    <button className={`nav-item ${activeTab === 'settings' ? 'active' : ''}`} onClick={() => setActiveTab('settings')}>
                        <Settings size={18} /> Settings
                    </button>
                </nav>

                <div className="mode-selector">
                    <div className="stat-label">Mode Selection</div>
                    <div className="mode-grid">
                        <button 
                          className={`mode-btn ${sensoryProfile === 'vision' ? 'active' : ''}`}
                          onClick={() => setSensoryProfile('vision')}
                        >
                            <Camera size={20} />
                            <span>VISION</span>
                        </button>
                        <button 
                          className={`mode-btn ${sensoryProfile === 'hearing' ? 'active' : ''}`}
                          onClick={() => setSensoryProfile('hearing')}
                        >
                            <Mic size={20} />
                            <span>AUDIO</span>
                        </button>
                    </div>
                </div>
            </aside>

            {/* Top Header */}
            <header className="top-header">
                <div className="search-wrapper">
                    <Search size={16} style={{position: 'absolute', margin: '10px', color: 'var(--text-muted)'}} />
                    <input type="text" className="search-bar" placeholder="Global search..." style={{paddingLeft: '35px'}} />
                </div>
                <div className="header-actions">
                    <button className="nav-btn" style={{background: 'var(--primary)', border: 'none', color: 'white', padding: '0.5rem 1rem', borderRadius: '6px', fontSize: '0.8rem', fontWeight: 700}}>
                        STREAM STANDBY
                    </button>
                    <Bell size={20} color="var(--text-muted)" />
                    <div style={{height: '24px', width: '1px', background: 'var(--border-color)'}} />
                    <User size={20} color="var(--text-muted)" />
                </div>
            </header>

            {/* Stats Row */}
            <div className="stats-row">
                <div className="stat-card">
                    <div className="stat-label">Model Confidence</div>
                    <div className="stat-value">---</div>
                </div>
                <div className="stat-card">
                    <div className="stat-label">Latency</div>
                    <div className="stat-value">---</div>
                </div>
                <div className="stat-card">
                    <div className="stat-label">Safety Rating</div>
                    <div className="stat-value" style={{color: safetyLevel === 'Safe' ? 'var(--safe)' : 'var(--critical)'}}>
                        {safetyLevel}
                    </div>
                </div>
                <div className="stat-card">
                    <div className="stat-label">Live FPS</div>
                    <div className="stat-value">0.0</div>
                </div>
            </div>

            {/* Main Content Area */}
            <main className="main-view">
                <div className="content-card">
                    <div className="card-header">
                        <div className="card-title">
                            {sensoryProfile === 'vision' ? <Camera size={16} color="var(--primary)" /> : <Mic size={16} color="var(--primary)" />}
                            REAL-TIME {sensoryProfile.toUpperCase()} INTELLIGENCE
                        </div>
                        <div style={{display: 'flex', gap: '10px', alignItems: 'center'}}>
                            <div className="status-chip pulse">GEMINI 3 FLASH</div>
                            <MoreVertical size={16} color="var(--text-muted)" />
                        </div>
                    </div>
                    
                    <div className="visual-feed">
                        {sensoryProfile === 'vision' ? (
                            <>
                                <video ref={videoRef} autoPlay playsInline muted className="video-feed" />
                                <canvas ref={canvasRef} style={{ display: 'none' }} />
                                {isScanning && <div className="scan-line" />}
                                <button 
                                    className="sos-btn" 
                                    style={{position: 'absolute', bottom: '2rem'}}
                                    onClick={() => captureAndAnalyze()}
                                >
                                    SCAN SCENE
                                </button>
                            </>
                        ) : (
                            <div className="audio-listening-ui">
                                <div className={`listening-circle ${isRecording ? 'pulse' : ''}`}>
                                    <Mic size={40} color="white" />
                                </div>
                                <div className="stat-value">{isRecording ? 'Listening...' : 'System Idle'}</div>
                                <button 
                                    className={isRecording ? "btn-stop-listening" : "nav-btn"}
                                    onClick={handleAudioListen}
                                    style={!isRecording ? {background: 'var(--primary)', color: 'white', padding: '1rem 2rem'} : {}}
                                >
                                    {isRecording ? 'STOP LISTENING' : 'START LISTENING'}
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </main>

            {/* Right Sidebar Intelligence */}
            <aside className="intelligence-panel">
                <div className="session-intel-header">
                    <div className="card-title">SESSION INTELLIGENCE</div>
                    <div className="status-chip" style={{borderRadius: '50%', width: '24px', height: '24px', padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>3</div>
                </div>
                
                <div className="chat-box">
                    {messages.length === 0 && (
                        <div style={{textAlign: 'center', marginTop: '50%', color: 'var(--text-muted)'}}>
                            <Loader2 className="animate-spin" style={{margin: '0 auto 1rem'}} />
                            <p>Establishing neural link...</p>
                        </div>
                    )}
                    {messages.map(m => (
                        <div key={m.id} className={`chat-msg ${m.role}`}>
                            <strong>{m.role.toUpperCase()}:</strong> {m.text}
                        </div>
                    ))}
                </div>

                <div className="chat-input-wrapper">
                    <input 
                      type="text" 
                      className="chat-input" 
                      placeholder="Ask Omni..." 
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSendChat()}
                    />
                    <button 
                      onClick={handleSendChat}
                      style={{background: 'var(--primary)', border: 'none', borderRadius: '6px', width: '36px', height: '36px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white'}}
                    >
                        <Send size={16} />
                    </button>
                </div>

                <div style={{marginTop: '2rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem'}}>
                    <button className="mode-btn" style={{fontSize: '0.7rem'}} onClick={() => captureAndAnalyze("Describe scene")}>DESCRIBE SCENE</button>
                    <button className="mode-btn" style={{fontSize: '0.7rem'}} onClick={() => captureAndAnalyze("Is it safe?")}>SAFETY CHECK</button>
                    <button className="mode-btn" style={{fontSize: '0.7rem'}} onClick={() => captureAndAnalyze("Are there people?")}>FIND PEOPLE</button>
                    <button className="mode-btn" style={{fontSize: '0.7rem'}} onClick={() => captureAndAnalyze("Where is exit?")}>FIND EXIT</button>
                </div>
            </aside>

            {/* Bottom Activity Log */}
            <section className="activity-log">
                <div className="session-intel-header">
                    <div className="card-title">SENSOR ACTIVITY LOG</div>
                    <div className="stat-label" style={{color: 'var(--primary)', cursor: 'pointer'}}>View All</div>
                </div>
                <table className="log-table">
                    <thead>
                        <tr>
                            <th>EVENT TYPE</th>
                            <th>TIMESTAMP</th>
                            <th>SEVERITY</th>
                            <th>STATUS</th>
                        </tr>
                    </thead>
                    <tbody>
                        {activityLog.length === 0 ? (
                            <tr><td colSpan="4" style={{textAlign: 'center', opacity: 0.5}}>No recent activity</td></tr>
                        ) : (
                            activityLog.map(log => (
                                <tr key={log.id}>
                                    <td>• {log.type}</td>
                                    <td>{log.timestamp}</td>
                                    <td><span className={`status-chip ${log.severity.toLowerCase()}`} style={{fontSize: '0.6rem'}}>{log.severity}</span></td>
                                    <td>{log.status}</td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </section>

            <button className="sos-btn-corner" onClick={() => alert("EMERGENCY SOS ACTIVATED")}>
                EMERGENCY SOS
            </button>
        </div>
    );
};

export default App;
