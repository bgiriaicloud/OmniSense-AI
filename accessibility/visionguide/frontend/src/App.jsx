import React, { useState, useEffect, useRef } from 'react';
import { Camera, Mic, Shield, AlertTriangle, Info, Heart, Play, Square } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAccessibility } from './hooks/useAccessibility';
import './App.css';

const App = () => {
    const [mode, setMode] = useState('vision');
    const [isRecording, setIsRecording] = useState(false);
    const [audioResult, setAudioResult] = useState(null);
    const [activeAlert, setActiveAlert] = useState(null);
    const {
        safetyLevel, isAnalyzing, speak,
        videoRef, canvasRef, captureAndAnalyze, analyzeAudio, mediaStreamRef,
        startVoiceCommands, stopVoiceCommands, voiceStatus,
        seniorMode, setSeniorMode, language, setLanguage,
        hasStarted, handleStartSystems, handleStopSystems,
        isLiveStreaming, startLiveStream, stopLiveStream,
        isScanning, autoGuidance, setAutoGuidance
    } = useAccessibility();

    useEffect(() => {
        if (hasStarted && mode === 'vision') {
            startVoiceCommands();
        } else {
            stopVoiceCommands();
        }
    }, [hasStarted, mode, startVoiceCommands, stopVoiceCommands]);

    const handleAudioListen = async () => {
        if (isRecording || isAnalyzing) return;

        // Re-create MediaRecorder each time so state is always 'inactive'
        if (!mediaStreamRef.current) {
            speak("Microphone not available. Please allow microphone access.");
            return;
        }

        const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/ogg';
        const recorder = new MediaRecorder(mediaStreamRef.current, { mimeType });
        const chunks = [];
        setIsRecording(true);
        setAudioResult(null);

        recorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };
        recorder.onstop = async () => {
            const blob = new Blob(chunks, { type: mimeType });
            const result = await analyzeAudio(blob);
            setIsRecording(false);
            if (result) {
                setAudioResult(result);
                if (result.urgency === 'Critical' || result.urgency === 'Caution') {
                    setActiveAlert({
                        title: result.sound_event,
                        message: result.guidance,
                        type: result.urgency
                    });
                    // Auto-clear alert after 8 seconds
                    setTimeout(() => setActiveAlert(null), 8000);
                }
            }
        };

        recorder.start(100);
        setTimeout(() => {
            if (recorder.state === 'recording') {
                recorder.stop();
                console.log("Auto-recording stopped.");
            }
        }, 4000);
    };

    // --- Continuous Audio Monitoring Logic ---
    useEffect(() => {
        if (!hasStarted || mode !== 'audio') return;

        console.log("Initializing continuous audio monitoring...");
        const monitorInterval = setInterval(() => {
            if (!isRecording && !isAnalyzing) {
                console.log("Triggering background audio analysis...");
                handleAudioListen();
            }
        }, 20000); // Cycle every 20 seconds (4s record + 16s wait)

        return () => {
            console.log("Stopping continuous audio monitoring.");
            clearInterval(monitorInterval);
        };
    }, [hasStarted, mode, isRecording, isAnalyzing, handleAudioListen]);

    // --- Continuous Vision Guidance Logic ---
    useEffect(() => {
        if (!hasStarted || mode !== 'vision' || !autoGuidance || isLiveStreaming) return;

        console.log("Initializing continuous vision monitoring...");
        const visionInterval = setInterval(() => {
            console.log("Triggering auto vision analysis...");
            captureAndAnalyze("Provide a safety check and navigation prompt.");
        }, 60000); // 60s for stability

        return () => {
            console.log("Stopping continuous vision monitoring.");
            clearInterval(visionInterval);
        };
    }, [hasStarted, mode, autoGuidance, isLiveStreaming, captureAndAnalyze]);

    const handleSOSTrigger = () => {
        speak("SOS Triggered. Emergency protocol initiated.");
        alert("SOS TRIGGERED! Emergency contacts would be notified.");
    };

    const handleModeSwitch = (newMode) => {
        setMode(newMode);
        if (newMode === 'vision') {
            speak("Vision mode active. Voice guidance enabled. I am analyzing the scene for you now.");
            // Slight delay to ensure video feed is ready/shifted before capture
            setTimeout(() => {
                captureAndAnalyze("Describe my surroundings and guide me.");
            }, 800);
        } else {
            speak(`Switched to ${newMode} mode.`);
        }
    };

    return (
        <div className="app-container">
            <div className="mesh-background" />

            <AnimatePresence mode="wait">
                {!hasStarted ? (
                    <motion.div
                        key="start"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="start-screen glass-morphism"
                    >
                        <Shield size={64} color="var(--primary)" style={{ marginBottom: '2rem' }} />
                        <h1>OmniSense</h1>
                        <h2>System Initialization</h2>
                        <p>
                            To provide real-time accessibility guidance, OmniSense requires access to your
                            camera and microphone.
                        </p>
                        <button className="btn-primary start-button" onClick={() => {
                            handleStartSystems();
                            if (mode === 'vision') {
                                setTimeout(() => captureAndAnalyze("I'm starting. Describe my surroundings."), 1500);
                            }
                        }}>
                            Enable Systems
                        </button>
                        <div className="info-box">
                            <Info size={16} />
                            <span>Privacy First: All processing is secure and transparent.</span>
                        </div>
                    </motion.div>
                ) : (
                    <motion.div
                        key="main"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="main-layout"
                    >
                        <header className="glass-morphism header">
                            <div className="brand">
                                <Shield className="brand-icon" size={24} />
                                <h1>OmniSense</h1>
                            </div>

                            <div className={`safety-badge ${safetyLevel.toLowerCase()}`}>
                                <Shield size={16} />
                                <span>{safetyLevel}</span>
                            </div>

                            <div className="status-indicators">
                                {hasStarted && mode === 'audio' && (
                                    <div className="status-chip pulse">
                                        <Mic size={12} />
                                        <span>Auto-Monitor Active</span>
                                    </div>
                                )}
                                {hasStarted && seniorMode && (
                                    <div className="status-chip gold">
                                        <Heart size={12} fill="currentColor" />
                                        <span>Wellness Care Active</span>
                                    </div>
                                )}
                                {hasStarted && isLiveStreaming && (
                                    <div className="status-chip live">
                                        <div className="live-dot" />
                                        <span>Live Session Active</span>
                                    </div>
                                )}
                            </div>

                            <div className="settings-compact">
                                <select
                                    value={language}
                                    onChange={(e) => setLanguage(e.target.value)}
                                    className="lang-select"
                                >
                                    <option value="en">EN</option>
                                    <option value="fr">FR</option>
                                    <option value="hi">HI</option>
                                    <option value="or">OR</option>
                                </select>
                                <button
                                    className={`senior-toggle ${seniorMode ? 'active' : ''}`}
                                    onClick={() => setSeniorMode(!seniorMode)}
                                    title="Senior Citizen Mode"
                                >
                                    <Heart size={16} fill={seniorMode ? "white" : "none"} />
                                    <span>Senior Mode</span>
                                </button>
                                <button className="logout-button" onClick={handleStopSystems} title="Stop Systems">
                                    Logout
                                </button>
                            </div>
                        </header>

                        <nav className="mode-switcher glass-morphism">
                            <button
                                className={mode === 'vision' ? 'active' : ''}
                                onClick={() => handleModeSwitch('vision')}
                            >
                                <Camera size={20} />
                                <span>Vision</span>
                            </button>
                            <button
                                className={mode === 'audio' ? 'active' : ''}
                                onClick={() => handleModeSwitch('audio')}
                            >
                                <Mic size={20} />
                                <span>Audio</span>
                            </button>
                        </nav>

                        <main className="content-area">
                            <AnimatePresence mode="wait">
                                {mode === 'vision' ? (
                                    <motion.div
                                        key="vision"
                                        initial={{ opacity: 0, y: 20 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0, y: -20 }}
                                        className="mode-pane"
                                    >
                                        <VisionPane
                                            videoRef={videoRef}
                                            canvasRef={canvasRef}
                                            onCapture={captureAndAnalyze}
                                            isAnalyzing={isAnalyzing}
                                            voiceStatus={voiceStatus}
                                            isLiveStreaming={isLiveStreaming}
                                            startLiveStream={startLiveStream}
                                            stopLiveStream={stopLiveStream}
                                            autoGuidance={autoGuidance}
                                            setAutoGuidance={setAutoGuidance}
                                            speak={speak}
                                            isScanning={isScanning}
                                        />
                                    </motion.div>
                                ) : (
                                    <motion.div
                                        key="audio"
                                        initial={{ opacity: 0, y: 20 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0, y: -20 }}
                                        className="mode-pane"
                                    >
                                        <AudioPane
                                            audioStatus={audioStatus}
                                            onListen={handleAudioListen}
                                            isAnalyzing={isAnalyzing}
                                            isRecording={isRecording}
                                            audioResult={audioResult}
                                        />
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </main>

                        <footer className="footer-controls">
                            <div className="sos-wrapper">
                                <SOSButton onTrigger={handleSOSTrigger} />
                            </div>
                        </footer>

                        {activeAlert && (
                            <AudioAlertOverlay
                                alert={activeAlert}
                                onDismiss={() => setActiveAlert(null)}
                            />
                        )}

                        {(isAnalyzing || isScanning) && (
                            <div className={`analyzing-overlay ${isScanning ? 'scanning' : ''}`}>
                                <div className="loader">
                                    <div className="pulse-ring" />
                                    <span>{isScanning ? 'Scanning...' : 'Analyzing...'}</span>
                                </div>
                            </div>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

// Placeholder components to be implemented next
const VisionPane = ({
    videoRef, canvasRef, onCapture, isAnalyzing, voiceStatus,
    isLiveStreaming, startLiveStream, stopLiveStream,
    autoGuidance, setAutoGuidance, speak, isScanning
}) => {
    const handleFile = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (evt) => onCapture("Describe this image in detail.", evt.target.result);
        reader.readAsDataURL(file);
    };

    return (
        <div className="glass-morphism pane-card">
            <div className="camera-preview-box">
                <video ref={videoRef} autoPlay playsInline muted className="video-feed" />
                <canvas ref={canvasRef} style={{ display: 'none' }} />
            </div>

            <div className="live-trigger-container">
                <button
                    className={`live-btn ${isLiveStreaming ? 'active' : ''}`}
                    onClick={isLiveStreaming ? stopLiveStream : startLiveStream}
                >
                    {isLiveStreaming ? <Square size={20} fill="currentColor" /> : <Play size={20} fill="currentColor" />}
                    <span>{isLiveStreaming ? "Stop Real-time Navigation" : "Start Real-time Live Navigation (Recommended)"}</span>
                </button>
                <p className="live-hint">
                    {isLiveStreaming
                        ? "I am watching and listening. Just speak to me."
                        : "Use this mode for the most fluid, continuous guidance."}
                </p>
            </div>

            <div className="action-grid alternate">
                <button
                    className={`btn-toggle ${autoGuidance ? 'active' : ''}`}
                    onClick={() => {
                        setAutoGuidance(!autoGuidance);
                        speak(autoGuidance ? "Auto guidance disabled." : "Auto guidance enabled. I will analyze your surroundings every 45 seconds to stay within your service limits.");
                    }}
                    disabled={isLiveStreaming}
                >
                    <Shield size={18} />
                    <span>{autoGuidance ? "Stop Auto-Guidance" : "Enable Auto-Guidance"}</span>
                </button>

                <button
                    className="btn-secondary"
                    onClick={() => onCapture()}
                    disabled={isAnalyzing || isLiveStreaming || isScanning}
                >
                    <Camera size={18} />
                    Check Once
                </button>
            </div>

            <section className="highlights">
                <div className="voice-badge">
                    <Mic size={14} />
                    <span>Voice: {voiceStatus}</span>
                </div>
                <div className="highlight-item">
                    <Info size={16} />
                    <span>Say <b>"Describe"</b> for a full update.</span>
                </div>
            </section>
        </div>
    );
};

const AudioPane = ({ audioStatus, onListen, isAnalyzing, isRecording, audioResult }) => (
    <div className="glass-morphism pane-card audio-hub">
        <div className="mic-viz-container">
            <div className={`mic-circle ${isRecording || isAnalyzing ? 'active' : ''}`}>
                <Mic size={48} className={isRecording ? 'animate-pulse' : ''} />
            </div>
        </div>
        <div className="audio-meta">
            <h3>{isRecording ? 'Recording...' : isAnalyzing ? 'Analyzing...' : audioStatus}</h3>
            <p className="text-muted">
                {isRecording ? 'Listening for 4 seconds...' : 'Tap to analyze environmental sounds'}
            </p>
        </div>
        {audioResult && (
            <div className="audio-result">
                <div className="result-event">
                    <AlertTriangle size={16} />
                    <strong>{audioResult.sound_event}</strong>
                </div>
                <p>{audioResult.guidance}</p>
            </div>
        )}
        <button
            className="btn-primary btn-wide"
            onClick={onListen}
            disabled={isAnalyzing || isRecording}
        >
            {isAnalyzing ? 'Processing...' : isRecording ? '🎙 Recording...' : 'Start Listening'}
        </button>
    </div>
);

const SOSButton = ({ onTrigger }) => {
    const [pressing, setPressing] = useState(false);
    const timerRef = useRef(null);

    const startTimer = () => {
        setPressing(true);
        timerRef.current = setTimeout(() => {
            onTrigger();
            setPressing(false);
        }, 3000);
    };

    const cancelTimer = () => {
        clearTimeout(timerRef.current);
        setPressing(false);
    };

    return (
        <button
            className={`sos-btn ${pressing ? 'pressing' : ''}`}
            onMouseDown={startTimer}
            onMouseUp={cancelTimer}
            onMouseLeave={cancelTimer}
            onTouchStart={startTimer}
            onTouchEnd={cancelTimer}
        >
            SOS
        </button>
    );
};

const AudioAlertOverlay = ({ alert, onDismiss }) => (
    <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        className={`audio-alert-overlay ${alert.type.toLowerCase()}`}
        onClick={onDismiss}
    >
        <div className="alert-content">
            <AlertTriangle size={48} />
            <h2>{alert.title}</h2>
            <p>{alert.message}</p>
            <span className="dismiss-hint">Tap to dismiss</span>
        </div>
    </motion.div>
);

export default App;
