import { useState, useEffect, useRef } from 'react';
import {
    Camera, Mic, Shield,
    LayoutDashboard, History, BarChart2, Settings, Search, Bell, User,
    MoreVertical, Send, Loader2, Menu, X
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAccessibility } from './hooks/useAccessibility';

const App = () => {
    const {
        safetyLevel, isAnalyzing, speak,
        videoRef, canvasRef, captureAndAnalyze, analyzeAudio, mediaStreamRef,
        audioStatus, voiceStatus,
        handleStartSystems, sensoryProfile, setSensoryProfile,
        isLiveStreaming, startLiveStream, stopLiveStream,
        startVoiceCommands, stopVoiceCommands,
        startActivationListener
    } = useAccessibility();

    const [isVoiceActive, setIsVoiceActive] = useState(false);
    const [isSystemEnabled, setIsSystemEnabled] = useState(false);
    const [activeTab, setActiveTab] = useState('dashboard');
    const [messages, setMessages] = useState([]);
    const [chatInput, setChatInput] = useState('');
    const [activityLog, setActivityLog] = useState([]);
    const [isRecording, setIsRecording] = useState(false);
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const activeRecordingRef = useRef(false);

    useEffect(() => {
        if (!isSystemEnabled) {
            const cleanup = startActivationListener(() => handleEnableSystem());
            const timer = setTimeout(() => speak("Please enable the system to begin."), 1500);
            return () => {
                clearTimeout(timer);
                if (cleanup) cleanup();
            };
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isSystemEnabled, startActivationListener]);

    const handleEnableSystem = () => {
        setIsSystemEnabled(true);
        handleStartSystems('dual');
        setTimeout(() => speak("OmniSense system enabled. Voice and vision agents are now active."), 200);
        addToLog('SYSTEM', 'INITIALIZED', 'SUCCESS');
    };

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

    useEffect(() => {
        if (voiceStatus && voiceStatus !== 'Off' && !voiceStatus.startsWith('Listening') && !voiceStatus.startsWith('Matched')) {
            const text = voiceStatus.startsWith('AI:') ? voiceStatus.substring(4) : voiceStatus;
            setMessages(prev => [...prev, { role: 'assistant', text, id: Date.now() }]);
            addToLog('VOICE', 'COMMAND', 'SUCCESS');
        }
    }, [voiceStatus]);

    const handleSendChat = async () => {
        if (!chatInput.trim()) return;
        const query = chatInput.trim();
        setChatInput('');
        // Add user message immediately so it's visible
        const userMsgId = Date.now();
        setMessages(prev => [...prev, { role: 'user', text: query, id: userMsgId }]);
        // Add a pending assistant message
        const pendingId = Date.now() + 1;
        setMessages(prev => [...prev, { role: 'assistant', text: '⏳ Analyzing...', id: pendingId, pending: true }]);
        addToLog('CHAT', 'QUERY', 'PROCESSING');
        const result = await captureAndAnalyze(query);
        // Replace the pending message with the actual response
        if (result) {
            const feedback = `${result.scene || ''} ${result.guidance || ''}`.trim();
            setMessages(prev => prev.map(m => m.id === pendingId
                ? { ...m, text: feedback, pending: false }
                : m
            ));
            addToLog('CHAT', 'RESPONSE', 'SUCCESS');
        } else {
            setMessages(prev => prev.map(m => m.id === pendingId
                ? { ...m, text: 'Could not analyze scene. Please try again.', pending: false }
                : m
            ));
        }
    };

    const handleAudioListen = async () => {
        if (isRecording) {
            setIsRecording(false);
            activeRecordingRef.current = false;
            return;
        }

        if (isAnalyzing || !mediaStreamRef.current) return;
        setIsRecording(true);
        activeRecordingRef.current = true;
        addToLog('AUDIO', 'LISTENING', 'ACTIVE');

        const recordCycle = async () => {
            if (!mediaStreamRef.current) return;

            const recorder = new MediaRecorder(mediaStreamRef.current, { mimeType: 'audio/webm' });
            const chunks = [];
            recorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };

            recorder.onstop = async () => {
                const blob = new Blob(chunks, { type: 'audio/webm' });
                const result = await analyzeAudio(blob);

                if (result) {
                    const urgencyIcon = result.urgency === 'Critical' ? '🚨' : result.urgency === 'Caution' ? '⚠️' : '✅';
                    // Only display/speak if an event was actually detected to avoid noise
                    if (result.event_detected) {
                        const displayText = `${urgencyIcon} ${result.sound_event || result.sound_type}\n\n${result.guidance}`;
                        setMessages(prev => [...prev, {
                            role: 'assistant',
                            text: displayText,
                            urgency: result.urgency,
                            id: Date.now()
                        }]);
                        speak(result.guidance);
                        addToLog('AUDIO', result.sound_event || result.sound_type, result.urgency || 'PROCESSED');
                    }
                }

                // Check the ref (which we should add) or just use a boolean flag
                if (activeRecordingRef.current) {
                    setTimeout(recordCycle, 200);
                }
            };

            recorder.start();
            setTimeout(() => recorder.stop(), 5000); // 5 second chunks for better recognition
        };

        recordCycle();
    };

    if (!isSystemEnabled) {
        return (
            <div className="fixed inset-0 bg-background flex flex-col items-center justify-center p-6 text-center z-[1000]">
                <motion.div
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="mb-8"
                >
                    <Shield size={120} className="text-primary mx-auto mb-6 filter drop-shadow-[0_0_30px_rgba(58,134,255,0.4)]" />
                    <h1 className="text-5xl font-black mb-2 tracking-tight text-white">Omnisense AI</h1>
                    <p className="text-muted-foreground text-xl">Secure Multimodal Accessibility Engine</p>
                    <div className="mt-4 flex items-center justify-center gap-2 text-primary/60 text-sm font-bold animate-pulse">
                        <Mic size={16} /> 
                        <span>Voice activation active: Say &quot;Enable system&quot;</span>
                    </div>
                </motion.div>
                <button
                    className="bg-primary text-primary-foreground px-10 py-5 rounded-2xl font-black text-2xl shadow-[0_0_50px_-10px_rgba(58,134,255,0.5)] hover:scale-105 transition-transform"
                    onClick={handleEnableSystem}
                >
                    ENABLE SYSTEM
                </button>
            </div>
        );
    }

    return (
        <div className="flex flex-col lg:flex-row h-screen bg-background text-foreground overflow-hidden">
            {/* Sidebar Overlay for Mobile */}
            <AnimatePresence>
                {isSidebarOpen && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={() => setIsSidebarOpen(false)}
                        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
                    />
                )}
            </AnimatePresence>

            {/* Sidebar */}
            <aside className={`
                fixed lg:static inset-y-0 left-0 w-64 bg-card border-r border-border z-50 transform transition-transform duration-300 ease-in-out
                ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
            `}>
                <div className="p-6 flex flex-col h-full">
                    <div className="flex items-center justify-between mb-10">
                        <div className="flex items-center gap-3">
                            <Shield size={28} className="text-primary fill-primary" />
                            <span className="text-xl font-bold text-white tracking-tight">Omnisense</span>
                        </div>
                        <button onClick={() => setIsSidebarOpen(false)} className="lg:hidden">
                            <X size={24} />
                        </button>
                    </div>

                    <nav className="space-y-1 flex-1">
                        {[
                            { id: 'dashboard', icon: LayoutDashboard, label: 'Dashboard' },
                            { id: 'history', icon: History, label: 'History' },
                            { id: 'analytics', icon: BarChart2, label: 'Analytics' },
                            { id: 'settings', icon: Settings, label: 'Settings' }
                        ].map(item => (
                            <button
                                key={item.id}
                                onClick={() => { setActiveTab(item.id); setIsSidebarOpen(false); }}
                                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${activeTab === item.id ? 'bg-primary/10 text-primary border-l-4 border-primary' : 'text-muted-foreground hover:bg-white/5 hover:text-white'}`}
                            >
                                <item.icon size={20} />
                                <span className="font-semibold text-sm">{item.label}</span>
                            </button>
                        ))}
                    </nav>

                    <div className="mt-auto space-y-6">
                        <div className="pt-6 border-t border-border">
                            <p className="text-[10px] uppercase font-black text-muted-foreground tracking-widest mb-4">Mode Selection</p>
                            <div className="grid grid-cols-2 gap-2">
                                <button
                                    onClick={() => setSensoryProfile('vision')}
                                    className={`flex flex-col items-center gap-2 p-3 rounded-xl border transition-all ${sensoryProfile === 'vision' ? 'bg-primary/20 border-primary text-primary' : 'bg-background border-border text-muted-foreground'}`}
                                >
                                    <Camera size={20} />
                                    <span className="text-[10px] font-bold">VISION</span>
                                </button>
                                <button
                                    onClick={() => setSensoryProfile('hearing')}
                                    className={`flex flex-col items-center gap-2 p-3 rounded-xl border transition-all ${sensoryProfile === 'hearing' ? 'bg-primary/20 border-primary text-primary' : 'bg-background border-border text-muted-foreground'}`}
                                >
                                    <Mic size={20} />
                                    <span className="text-[10px] font-bold">AUDIO</span>
                                </button>
                            </div>
                        </div>

                        <button
                            onClick={() => alert("EMERGENCY SOS ACTIVATED")}
                            className="w-full bg-critical text-white py-4 rounded-2xl font-black text-xs shadow-lg shadow-critical/20 hover:scale-[1.02] transition-transform flex items-center justify-center gap-2"
                        >
                            <Shield size={16} fill="white" />
                            EMERGENCY SOS
                        </button>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
                {/* Header */}
                <header className="h-16 border-b border-border bg-card/50 backdrop-blur-md flex items-center justify-between px-4 lg:px-8">
                    <div className="flex items-center gap-4 flex-1">
                        <button onClick={() => setIsSidebarOpen(true)} className="lg:hidden p-2 hover:bg-white/5 rounded-lg">
                            <Menu size={24} />
                        </button>
                        <div className="relative flex-1 max-w-md hidden md:block">
                            <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                            <input
                                type="text"
                                placeholder="Global search..."
                                className="w-full bg-background border border-border rounded-xl pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                            />
                        </div>
                    </div>

                    <div className="flex items-center gap-3 lg:gap-6">
                        <button
                            onClick={isLiveStreaming ? stopLiveStream : startLiveStream}
                            className={`hidden sm:flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-black shadow-lg transition-all ${isLiveStreaming ? 'bg-critical text-white shadow-critical/20' : 'bg-primary text-primary-foreground shadow-primary/20'}`}
                        >
                            {isLiveStreaming ? 'STOP STREAM' : 'START LIVE STREAM'}
                        </button>
                        <button
                            onClick={() => {
                                if (isVoiceActive) {
                                    stopVoiceCommands();
                                    setIsVoiceActive(false);
                                } else {
                                    startVoiceCommands();
                                    setIsVoiceActive(true);
                                }
                            }}
                            className={`hidden sm:flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-black shadow-lg transition-all ${isVoiceActive ? 'bg-primary text-white' : 'bg-card border border-border text-muted-foreground'}`}
                        >
                            {isVoiceActive ? 'VOICE ASST ON' : 'ENABLE VOICE ASST'}
                        </button>
                        <button
                            onClick={() => window.speechSynthesis.cancel()}
                            className="hidden sm:flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-black bg-card border border-border text-muted-foreground hover:text-white"
                            title="Stop current speech"
                        >
                            <X size={14} /> MUTE
                        </button>
                        <div className="flex items-center gap-4 text-muted-foreground">
                            <Bell size={20} className="cursor-pointer hover:text-white" />
                            <div className="w-px h-6 bg-border hidden sm:block" />
                            <div className="flex items-center gap-2 cursor-pointer hover:text-white">
                                <User size={20} />
                                <span className="text-sm font-bold hidden lg:block">Agent_01</span>
                            </div>
                        </div>
                    </div>
                </header>

                {/* Dashboard Area */}
                <main className="flex-1 overflow-y-auto p-4 lg:p-8 space-y-8">
                    {/* Stats Grid */}
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                        {[
                            { label: 'Model Confidence', value: '98.4%', color: 'text-primary' },
                            { label: 'Latency', value: '42ms', color: 'text-primary' },
                            { label: 'Safety Rating', value: safetyLevel, color: safetyLevel === 'Safe' ? 'text-safe' : 'text-critical' },
                            { label: 'Live FPS', value: '30.2', color: 'text-primary' }
                        ].map((stat, i) => (
                            <div key={i} className="bg-card p-4 rounded-2xl border border-border shadow-sm">
                                <p className="text-[10px] uppercase font-black text-muted-foreground tracking-wider mb-1">{stat.label}</p>
                                <p className={`text-xl lg:text-2xl font-bold ${stat.color}`}>{stat.value}</p>
                            </div>
                        ))}
                    </div>

                    {/* Content Grid */}
                    <div className="grid grid-cols-1 xl:grid-cols-3 gap-8 h-fit lg:h-[600px]">
                        {/* Main Feed Card */}
                        <div className="xl:col-span-2 flex flex-col bg-card rounded-3xl border border-border overflow-hidden shadow-xl">
                            <div className="p-4 lg:p-6 border-b border-border flex items-center justify-between">
                                <div className="flex items-center gap-3 font-black text-sm tracking-tighter">
                                    {sensoryProfile === 'vision' ? <Camera size={18} className="text-primary" /> : <Mic size={18} className="text-primary" />}
                                    REAL-TIME {sensoryProfile.toUpperCase()} INTELLIGENCE
                                </div>
                                <div className="flex items-center gap-4">
                                    <span className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-[10px] font-black animate-pulse">
                                        <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                                        GEMINI 3 FLASH
                                    </span>
                                    <MoreVertical size={18} className="text-muted-foreground cursor-pointer" />
                                </div>
                            </div>

                            <div className="flex-1 bg-black relative flex items-center justify-center min-h-[300px] lg:min-h-0 aspect-video">
                                {sensoryProfile === 'vision' ? (
                                    <>
                                        <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover rounded-b-3xl" />
                                        <canvas ref={canvasRef} className="hidden" />
                                        <button
                                            onClick={() => captureAndAnalyze()}
                                            className="absolute bottom-8 bg-primary/90 backdrop-blur-md text-primary-foreground px-8 py-3 rounded-2xl font-black text-sm shadow-2xl hover:scale-105 transition-transform"
                                        >
                                            SCAN SCENE
                                        </button>
                                    </>
                                ) : (
                                    <div className="flex flex-col items-center gap-8 text-center px-6">
                                        <div className={`w-32 h-32 rounded-full flex items-center justify-center transition-all duration-500 ${isRecording ? 'bg-primary scale-110 shadow-[0_0_50px_rgba(58,134,255,0.4)]' : 'bg-primary/20 shadow-none'}`}>
                                            <Mic size={48} className={isRecording ? 'text-white' : 'text-primary'} />
                                        </div>
                                        <div>
                                            <p className="text-2xl font-bold mb-2">{isRecording ? 'Listening...' : 'System Idle'}</p>
                                            <p className="text-2xl font-bold mb-2">{audioStatus}</p>
                                            <p className="text-muted-foreground text-sm max-w-xs">AI is monitoring for environmental sounds and safety alerts.</p>
                                        </div>
                                        <button
                                            onClick={handleAudioListen}
                                            className={`px-10 py-4 rounded-2xl font-black transition-all ${isRecording ? 'bg-critical text-white' : 'bg-primary text-white shadow-xl shadow-primary/20 hover:scale-105'}`}
                                        >
                                            {isRecording ? 'STOP LISTENING' : 'START LISTENING'}
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Session Intelligence Card */}
                        <div className="flex flex-col bg-card rounded-3xl border border-border overflow-hidden shadow-xl h-[500px] xl:h-full">
                            <div className="p-6 border-b border-border flex items-center justify-between">
                                <span className="font-black text-sm tracking-tighter">SESSION INTELLIGENCE</span>
                                <span className="w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-[10px] font-black">{messages.length}</span>
                            </div>

                            <div className="flex-1 overflow-y-auto p-6 space-y-4">
                                {messages.length === 0 ? (
                                    <div className="flex flex-col items-center justify-center h-full text-muted-foreground opacity-50 space-y-4">
                                        <Loader2 size={32} className="animate-spin text-primary" />
                                        <p className="text-xs font-bold tracking-widest uppercase">Establishing Link</p>
                                    </div>
                                ) : (
                                    messages.map(m => (
                                        <div key={m.id} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
                                            <span className="text-[9px] font-black text-muted-foreground mb-1 uppercase tracking-tighter">{m.role}</span>
                                            <div className={`max-w-[85%] p-4 rounded-2xl text-sm leading-relaxed ${m.role === 'user' ? 'bg-primary text-white rounded-tr-none' : 'bg-background border border-border text-foreground rounded-tl-none'}`}>
                                                {m.text}
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>

                            <div className="p-6 bg-background/50 border-t border-border">
                                <div className="flex gap-3">
                                    <input
                                        value={chatInput}
                                        onChange={(e) => setChatInput(e.target.value)}
                                        onKeyDown={(e) => e.key === 'Enter' && handleSendChat()}
                                        placeholder="Ask Omni..."
                                        className="flex-1 bg-card border border-border rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                                    />
                                    <button
                                        onClick={handleSendChat}
                                        className="p-3 bg-primary text-primary-foreground rounded-xl hover:scale-105 transition-transform shadow-lg shadow-primary/20"
                                    >
                                        <Send size={20} />
                                    </button>
                                </div>
                                <div className="grid grid-cols-2 gap-2 mt-4">
                                    {['Describe scene', 'Are there hazards?', 'Who is near me?', 'How do I exit?'].map(q => (
                                        <button
                                            key={q}
                                            onClick={() => {
                                                // Add question to chat thread
                                                const pendingId = Date.now() + 1;
                                                setMessages(prev => [
                                                    ...prev,
                                                    { role: 'user', text: q, id: Date.now() },
                                                    { role: 'assistant', text: '⏳ Analyzing...', id: pendingId, pending: true }
                                                ]);
                                                captureAndAnalyze(q).then(result => {
                                                    if (result) {
                                                        const feedback = `${result.scene || ''} ${result.guidance || ''}`.trim();
                                                        setMessages(prev => prev.map(m => m.id === pendingId
                                                            ? { ...m, text: feedback, pending: false }
                                                            : m
                                                        ));
                                                    }
                                                });
                                            }}
                                            className="text-[10px] font-black uppercase tracking-tight py-2 rounded-lg border border-border hover:bg-primary/10 hover:text-primary transition-all"
                                        >
                                            {q}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Activity Log - Scrollable Table on Mobile */}
                    <div className="bg-card rounded-3xl border border-border overflow-hidden shadow-xl mb-12">
                        <div className="p-6 border-b border-border flex items-center justify-between">
                            <span className="font-black text-sm tracking-tighter uppercase">Sensor Activity Log</span>
                            <button className="text-xs font-black text-primary hover:underline">VIEW ALL</button>
                        </div>
                        <div className="overflow-x-auto">
                            <table className="w-full text-left border-collapse">
                                <thead>
                                    <tr className="text-[10px] font-black text-muted-foreground tracking-widest border-b border-border bg-background/50">
                                        <th className="px-6 py-4 uppercase">Event Type</th>
                                        <th className="px-6 py-4 uppercase">Timestamp</th>
                                        <th className="px-6 py-4 uppercase">Severity</th>
                                        <th className="px-6 py-4 uppercase text-right">Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {activityLog.length === 0 ? (
                                        <tr><td colSpan="4" className="px-6 py-12 text-center text-muted-foreground text-sm">No recent neural activity detected</td></tr>
                                    ) : (
                                        activityLog.map(log => (
                                            <tr key={log.id} className="border-b border-border/50 hover:bg-white/[0.02] transition-colors">
                                                <td className="px-6 py-4 font-bold text-sm flex items-center gap-3 whitespace-nowrap text-white">
                                                    <div className={`w-2 h-2 rounded-full ${log.severity === 'WARNING' ? 'bg-critical' : 'bg-primary'}`} />
                                                    {log.type}
                                                </td>
                                                <td className="px-6 py-4 text-xs font-semibold text-muted-foreground whitespace-nowrap">{log.timestamp}</td>
                                                <td className="px-6 py-4">
                                                    <span className={`px-2 py-0.5 rounded-full text-[9px] font-black uppercase ${log.severity === 'WARNING' ? 'bg-critical/20 text-critical' : 'bg-primary/20 text-primary'}`}>
                                                        {log.severity}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 text-xs font-black text-right whitespace-nowrap text-white">{log.status}</td>
                                            </tr>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </main>
            </div>

            {/* Floating SOS button for mobile */}
            <button
                onClick={() => alert("EMERGENCY SOS ACTIVATED")}
                className="fixed bottom-6 right-6 lg:left-6 lg:right-auto lg:bottom-6 w-16 h-16 bg-critical text-white rounded-full flex items-center justify-center font-black text-xs shadow-2xl z-50 hover:scale-110 transition-transform lg:w-32 lg:h-12 lg:rounded-xl"
            >
                {/* Mobile: Text only icon on large circle, Desktop: Text only */}
                <span className="lg:block">EMERGENCY SOS</span>
            </button>
        </div>
    );
};

export default App;
