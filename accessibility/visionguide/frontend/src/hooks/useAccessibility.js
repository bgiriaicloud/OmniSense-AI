import { useState, useEffect, useRef, useCallback } from 'react';

export const useAccessibility = () => {
    const [cameraStream, setCameraStream] = useState(null);
    const [micStream, setMicStream] = useState(null);
    const [safetyLevel, setSafetyLevel] = useState('Safe');
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [audioStatus, setAudioStatus] = useState('Environmental Listener');
    const [voiceStatus, setVoiceStatus] = useState('Off');
    const [seniorMode, setSeniorMode] = useState(false);
    const [language, setLanguage] = useState('en');
    const [hasStarted, setHasStarted] = useState(false);

    const [isLiveStreaming, setIsLiveStreaming] = useState(false);
    const [isScanning, setIsScanning] = useState(false);
    const [isCoolingDown, setIsCoolingDown] = useState(false);
    const [autoGuidance, setAutoGuidance] = useState(false);

    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const mediaRecorderRef = useRef(null);
    const mediaStreamRef = useRef(null);  // raw mic stream for re-creating MediaRecorder
    const voiceRecognitionRef = useRef(null);
    const liveSocketRef = useRef(null);
    const audioContextRef = useRef(null);

    // --- Speech Synthesis ---
    const speak = useCallback((text) => {
        if (!text) return;
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);

        // Map app language to BCP47
        const langMap = {
            'en': 'en-US',
            'fr': 'fr-FR',
            'hi': 'hi-IN',
            'or': 'or-IN'
        };
        utterance.lang = langMap[language] || 'en-US';

        window.speechSynthesis.speak(utterance);
    }, [language]);

    // --- Camera Initialization ---
    const initCamera = useCallback(async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: "environment" },
                audio: false
            });
            setCameraStream(stream);

            // Resilient srcObject setting
            const setStream = () => {
                if (videoRef.current) {
                    videoRef.current.srcObject = stream;
                } else {
                    setTimeout(setStream, 100); // Retry if element not ready
                }
            };
            setStream();

        } catch (err) {
            console.error("Camera error:", err);
            if (!window.isSecureContext) {
                speak("Camera failed because this connection is not secure. Please use localhost or HTTPS.");
            } else if (err.name === 'NotAllowedError') {
                speak("Camera access was denied. Please allow camera permissions in your browser.");
            } else {
                speak("Camera access error. Please check your hardware.");
            }
        }
    }, [speak]);

    // --- Microphone Initialization ---
    const initMic = useCallback(async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            setMicStream(stream);
            mediaStreamRef.current = stream;

            const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
                ? 'audio/webm;codecs=opus'
                : 'audio/webm';

            const recorder = new MediaRecorder(stream, { mimeType });
            mediaRecorderRef.current = recorder;
        } catch (err) {
            console.error("Mic error:", err);
            if (!window.isSecureContext) {
                speak("Microphone failed because this connection is not secure.");
            } else if (err.name === 'NotAllowedError') {
                speak("Microphone access was denied.");
            } else {
                speak("Microphone access error.");
            }
        }
    }, [speak]);

    const handleStartSystems = useCallback(() => {
        setHasStarted(true);
        initCamera();
        initMic();
        speak("OmniSense systems initialized. How can I help you today?");
    }, [initCamera, initMic, speak]);

    const handleStopSystems = useCallback(() => {
        setHasStarted(false);
        stopAllHardware();
        stopVoiceCommands();
        speak("OmniSense systems deactivated. You have been logged out.");
    }, [stopAllHardware, stopVoiceCommands, speak]);

    // --- API Interactions ---
    const analyzeScene = useCallback(async (base64Image, query = "Describe my surroundings.") => {
        if (!base64Image || base64Image.length < 200) {
            console.error("Invalid image data captured.");
            speak("I was unable to capture a clear picture. Please ensure your camera is enabled.");
            return null;
        }
        setIsAnalyzing(true);
        try {
            const formData = new FormData();
            const blob = await (await fetch(base64Image)).blob();

            // Explicitly set the type to image/jpeg to avoid text/plain 400 errors
            const finalBlob = blob.type.startsWith('image/') ? blob : new Blob([blob], { type: 'image/jpeg' });

            formData.append('file', finalBlob, 'capture.jpg');
            formData.append('query', query);
            formData.append('senior_mode', seniorMode);
            formData.append('language', language);

            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 20000); // 20s timeout

            const response = await fetch('/analyze_scene', {
                method: 'POST',
                body: formData,
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            const data = await response.json();

            // Handle Quota/Rate Limit signature from backend
            if (data.hazard === "System is cooling down." || data.hazard === "High demand.") {
                setIsCoolingDown(true);
                setTimeout(() => setIsCoolingDown(false), 30000); // 30s cooldown
            }

            const hazardInfo = (data.hazard && data.hazard.toLowerCase() !== "path is clear.") ? `Caution: ${data.hazard}` : "";
            const feedback = `${data.scene} ${hazardInfo} ${data.guidance}`;
            setVoiceStatus(`AI: ${feedback}`);
            speak(feedback);
            return data;
        } catch (error) {
            console.error("Analysis failed:", error);
            if (error.name === 'AbortError') {
                speak("The analysis is taking longer than usual. Please try again or switch to Real-time mode.");
            } else {
                speak("I encountered an error while analyzing the scene.");
            }
            return null;
        } finally {
            setIsAnalyzing(false);
        }
    }, [seniorMode, language, speak]);

    const captureAndAnalyze = useCallback(async (query, preloadedDataUrl, delay = 0) => {
        if (isCoolingDown) {
            speak("I am currently cooling down after many requests. Please use real-time navigation or wait a moment.");
            return;
        }
        if (isScanning && !preloadedDataUrl) return;

        // If a preloaded base64 image data URL is provided (e.g. from file upload), use it directly
        if (preloadedDataUrl) {
            return analyzeScene(preloadedDataUrl, query || "Describe this image in detail.");
        }

        if (delay > 0) {
            setIsScanning(true);
            speak("Scanning environment. Please pan your camera slowly.");
            await new Promise(resolve => setTimeout(resolve, delay));
            setIsScanning(false);
        }

        if (!videoRef.current || !canvasRef.current) return;
        const context = canvasRef.current.getContext('2d');
        canvasRef.current.width = videoRef.current.videoWidth;
        canvasRef.current.height = videoRef.current.videoHeight;
        context.drawImage(videoRef.current, 0, 0, canvasRef.current.width, canvasRef.current.height);

        const base64Image = canvasRef.current.toDataURL('image/jpeg', 0.8);
        return analyzeScene(base64Image, query || "Describe my surroundings.");
    }, [analyzeScene, videoRef, canvasRef, speak, isScanning, isCoolingDown]);

    const analyzeAudio = useCallback(async (audioBlob) => {
        setIsAnalyzing(true);
        setAudioStatus('Analyzing sounds...');
        try {
            const formData = new FormData();
            formData.append('file', audioBlob, 'audio.webm');
            formData.append('senior_mode', seniorMode);
            formData.append('language', language);

            const response = await fetch('/analyze_audio', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            const feedback = data.guidance || data.sound_event;
            if (data.urgency) setSafetyLevel(data.urgency);
            speak(feedback);
            return data;
        } catch (error) {
            console.error("Audio analysis failed:", error);
            speak("I encountered an error while analyzing the audio.");
            return null;
        } finally {
            setIsAnalyzing(false);
            setAudioStatus('Environmental Listener');
        }
    }, [seniorMode, language, speak]);

    // --- Voice Command Engine ---
    const startVoiceCommands = useCallback(() => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) return;

        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        // Map app language to BCP47
        const langMap = {
            'en': 'en-US',
            'fr': 'fr-FR',
            'hi': 'hi-IN',
            'or': 'or-IN'
        };
        recognition.lang = langMap[language] || 'en-US';

        recognition.onresult = (event) => {
            const transcript = event.results[event.results.length - 1][0].transcript.trim().toLowerCase();
            console.log("Voice command:", transcript);
            setVoiceStatus(`Matched: ${transcript}`);

            // Scene description triggers
            if (
                transcript.includes("describe") ||
                transcript.includes("look") ||
                transcript.includes("what is around") ||
                transcript.includes("what do you see") ||
                transcript.includes("what's around") ||
                transcript.includes("where am i") ||
                transcript.includes("where are we") ||
                transcript.includes("surroundings") ||
                transcript.includes("environment") ||
                transcript.includes("what is here")
            ) {
                captureAndAnalyze("Describe my surroundings in detail. Tell me where I am.");

                // Safety / navigation triggers
            } else if (
                transcript.includes("safe") ||
                transcript.includes("walk") ||
                transcript.includes("navigate") ||
                transcript.includes("can i go") ||
                transcript.includes("is it okay") ||
                transcript.includes("obstacle") ||
                transcript.includes("path")
            ) {
                // Navigation and Safety get a 2-second buffer to allow panning
                captureAndAnalyze("Is it safe for me to walk? Identify any obstacles, hazards, or barriers in my path.", null, 2000);

                // Hazard triggers
            } else if (
                transcript.includes("hazard") ||
                transcript.includes("danger") ||
                transcript.includes("warning") ||
                transcript.includes("alert") ||
                transcript.includes("emergency")
            ) {
                captureAndAnalyze("Identify all hazards, dangers, or obstacles in this scene. Be very specific.", null, 2000);

                // Help / assistance trigger
            } else if (
                transcript.includes("help") ||
                transcript.includes("assist") ||
                transcript.includes("guide")
            ) {
                captureAndAnalyze("I need help. Describe this scene and what I should do next.", null, 2000);

                // Fallback: capture scene for any other spoken phrase
            } else if (transcript.length > 3) {
                captureAndAnalyze(`User asked: "${transcript}". Please answer based on what you see in the image.`, null, 2000);
            }
        };

        recognition.onstart = () => {
            console.log("Voice recognition started");
            setVoiceStatus('Listening...');
        };
        recognition.onerror = (event) => {
            console.error("Speech recognition error", event.error);
            setVoiceStatus(`Error: ${event.error}`);
            if (event.error === 'not-allowed') {
                speak("Microphone permission denied. Please allow microphone access for voice commands.");
            }
        };
        recognition.onend = () => {
            console.log("Voice recognition ended");
            // If the ref still exists, we want to be listening
            if (voiceRecognitionRef.current) {
                try {
                    console.log("Attempting to restart voice recognition...");
                    recognition.start();
                } catch (e) {
                    if (e.name === 'InvalidStateError') {
                        // Already started, ignore
                    } else {
                        console.error("Recognition restart failed", e);
                        setVoiceStatus('Restarting...');
                        setTimeout(() => {
                            if (voiceRecognitionRef.current) recognition.start();
                        }, 1000);
                    }
                }
            } else {
                setVoiceStatus('Off');
            }
        };

        recognition.start();
        voiceRecognitionRef.current = recognition;
    }, [captureAndAnalyze, language]);

    const stopVoiceCommands = useCallback(() => {
        if (voiceRecognitionRef.current) {
            voiceRecognitionRef.current.onend = null;
            voiceRecognitionRef.current.stop();
            voiceRecognitionRef.current = null;
        }
        setVoiceStatus('Off');
    }, []);

    // --- Multimodal Live Stream ---
    const startLiveStream = useCallback(async () => {
        if (isLiveStreaming) return;

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const socket = new WebSocket(`${protocol}//${host}/ws/live`);
        liveSocketRef.current = socket;
        setIsLiveStreaming(true);

        socket.onopen = () => {
            console.log("Live stream WebSocket connected.");
            speak("Live vision session established. I am watching and listening to you in real-time.");

            // Start the frame loop (Video: Type 0x01)
            const frameLoop = setInterval(() => {
                if (socket.readyState === WebSocket.OPEN && videoRef.current && canvasRef.current) {
                    const context = canvasRef.current.getContext('2d');
                    canvasRef.current.width = videoRef.current.videoWidth;
                    canvasRef.current.height = videoRef.current.videoHeight;
                    context.drawImage(videoRef.current, 0, 0, canvasRef.current.width, canvasRef.current.height);

                    canvasRef.current.toBlob(async (blob) => {
                        if (blob && socket.readyState === WebSocket.OPEN) {
                            // Prefix with 0x01 for Video
                            const arrayBuffer = await blob.arrayBuffer();
                            const prefixed = new Uint8Array(arrayBuffer.byteLength + 1);
                            prefixed[0] = 0x01;
                            prefixed.set(new Uint8Array(arrayBuffer), 1);
                            socket.send(prefixed);
                        }
                    }, 'image/jpeg', 0.4);
                } else {
                    clearInterval(frameLoop);
                }
            }, 1000);

            // Start the audio loop (Audio: Type 0x02)
            // Using a simpler approach for the bridge: capture small chunks
            if (mediaStreamRef.current) {
                const audioChunks = [];
                const audioRecorder = new MediaRecorder(mediaStreamRef.current, { mimeType: 'audio/webm' });
                audioRecorder.ondataavailable = async (e) => {
                    if (e.data.size > 0 && socket.readyState === WebSocket.OPEN) {
                        const arrayBuffer = await e.data.arrayBuffer();
                        const prefixed = new Uint8Array(arrayBuffer.byteLength + 1);
                        prefixed[0] = 0x02;
                        prefixed.set(new Uint8Array(arrayBuffer), 1);
                        socket.send(prefixed);
                    }
                };
                audioRecorder.start(500); // 500ms chunks
                socket.audioRecorder = audioRecorder;
            }

            socket.frameInterval = frameLoop;
        };

        socket.onerror = (error) => {
            console.error("WebSocket error:", error);
            speak("Connection error. Real-time navigation failed to establish.");
            setIsLiveStreaming(false);
        };

        socket.onmessage = async (event) => {
            // Receive PCM audio data
            const arrayBuffer = await event.data.arrayBuffer();
            playLiveAudio(arrayBuffer);
        };

        socket.onclose = () => {
            console.log("Live stream WebSocket closed.");
            setIsLiveStreaming(false);
            if (socket.frameInterval) clearInterval(socket.frameInterval);
            if (socket.audioRecorder) socket.audioRecorder.stop();
        };
    }, [isLiveStreaming, speak, videoRef, canvasRef]);

    const stopLiveStream = useCallback(() => {
        if (liveSocketRef.current) {
            liveSocketRef.current.close();
            liveSocketRef.current = null;
        }
        setIsLiveStreaming(false);
    }, []);

    const playLiveAudio = (arrayBuffer) => {
        if (!audioContextRef.current) {
            audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
        }
        const ctx = audioContextRef.current;

        // Gemini returns 24kHz Mono PCM16
        const floatData = new Float32Array(arrayBuffer.byteLength / 2);
        const intData = new Int16Array(arrayBuffer);
        for (let i = 0; i < intData.length; i++) {
            floatData[i] = intData[i] / 32768.0;
        }

        const audioBuffer = ctx.createBuffer(1, floatData.length, 24000);
        audioBuffer.getChannelData(0).set(floatData);

        const source = ctx.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(ctx.destination);
        source.start();
    };

    // --- Stop all camera/mic tracks ---
    const stopAllHardware = useCallback(() => {
        if (mediaStreamRef.current) {
            mediaStreamRef.current.getTracks().forEach(t => t.stop());
        }
        // Stop camera tracks via videoRef srcObject
        if (videoRef.current && videoRef.current.srcObject) {
            videoRef.current.srcObject.getTracks().forEach(t => t.stop());
            videoRef.current.srcObject = null;
        }
    }, []);

    // --- Page Visibility: pause hardware when tab is hidden ---
    useEffect(() => {
        const handleVisibility = () => {
            if (!hasStarted) return;
            if (document.hidden) {
                stopAllHardware();
                stopVoiceCommands();
            } else {
                initCamera();
                initMic();
            }
        };
        document.addEventListener('visibilitychange', handleVisibility);
        return () => {
            document.removeEventListener('visibilitychange', handleVisibility);
            stopAllHardware();
            stopVoiceCommands();
        };
    }, [hasStarted, stopAllHardware, stopVoiceCommands, initCamera, initMic]);

    // --- Advanced Spec: Continuous Vision Guidance ---
    useEffect(() => {
        if (!hasStarted || !autoGuidance || isLiveStreaming) return; // Removed 'mode !== 'vision'' as 'mode' is not defined.
        console.log("Initializing continuous vision monitoring...");
        const visionInterval = setInterval(() => {
            // The original logic checked !isAnalyzing && !isScanning, but the instruction implies a simpler call.
            // Keeping the simpler call as per instruction.
            console.log("Triggering auto vision analysis...");
            captureAndAnalyze("Provide a safety check and navigation prompt.");
        }, 60000); // Increase to 60s for Free Tier stability

        return () => {
            console.log("Stopping continuous vision monitoring.");
            clearInterval(visionInterval);
        };
    }, [hasStarted, mode, autoGuidance, isLiveStreaming, isAnalyzing, isScanning, captureAndAnalyze]);

    // --- Advanced Spec: Wellness Scheduler (Senior Mode) ---
    useEffect(() => {
        if (!hasStarted || !seniorMode) return;

        const wellnessInterval = setInterval(() => {
            const reminders = [
                "It's a great time to take a sip of water and stay hydrated.",
                "How about a gentle stretch to keep your joints moving and your spirit high?",
                "Remember to check if it's time for any scheduled medication.",
                "You're doing great today. I'm here if you'd like to talk about anything.",
                "A positive thought: The best way to predict the future is to create it."
            ];
            const randomReminder = reminders[Math.floor(Math.random() * reminders.length)];
            speak(randomReminder);
        }, 600000); // 10 minutes

        return () => clearInterval(wellnessInterval);
    }, [hasStarted, seniorMode, speak]);

    return {
        cameraStream,
        micStream,
        safetyLevel,
        isAnalyzing,
        audioStatus,
        voiceStatus,
        videoRef,
        canvasRef,
        mediaRecorderRef,
        mediaStreamRef,
        initCamera,
        initMic,
        captureAndAnalyze,
        analyzeAudio,
        speak,
        startVoiceCommands,
        stopVoiceCommands,
        seniorMode,
        setSeniorMode,
        language,
        setLanguage,
        hasStarted,
        handleStartSystems,
        handleStopSystems,

        isLiveStreaming,
        startLiveStream,
        stopLiveStream,
        isScanning, autoGuidance, setAutoGuidance,
        isCoolingDown
    };
};
