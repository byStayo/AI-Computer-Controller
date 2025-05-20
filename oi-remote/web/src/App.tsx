import React, { useState, useEffect, useCallback } from 'react';
import QRLanding from './components/QRLanding';
import ChatBox from './components/ChatBox';
import VideoCanvas from './components/VideoCanvas';
import { jwtDecode } from 'jwt-decode';

interface DecodedToken {
  exp: number;
  sub: string;
  // Add other fields if present in your JWT
}

const APP_STATE_KEY = 'oiRemoteAppState';

interface StoredAppState {
  wsUrl: string;
  token: string;
  streamUrl: string;
}

function App() {
  const [wsUrl, setWsUrl] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isPaired, setIsPaired] = useState(false);
  const [showStream, setShowStream] = useState(false);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);

  const constructStreamUrl = useCallback((currentWsUrl: string | null) => {
    if (!currentWsUrl) return null;
    try {
      const url = new URL(currentWsUrl);
      // Assuming gateway is on http/https on same host/port as ws endpoint, but path is /stream
      const httpProtocol = url.protocol === 'wss:' ? 'https:' : 'http:';
      // Include token for stream URL for potential auth on stream endpoint
      const currentToken = localStorage.getItem('oiRemoteToken'); // Get fresh token
      return `${httpProtocol}//${url.host}/stream${currentToken ? '?token='+currentToken : ''}`;
    } catch (e) {
      console.error("Error constructing stream URL:", e);
      return null;
    }
  }, []);

  useEffect(() => {
    // Load saved state from localStorage
    const savedStateRaw = localStorage.getItem(APP_STATE_KEY);
    if (savedStateRaw) {
      try {
        const savedState = JSON.parse(savedStateRaw) as StoredAppState;
        if (savedState.token && savedState.wsUrl) {
          const decoded: DecodedToken = jwtDecode(savedState.token);
          if (decoded.exp * 1000 > Date.now()) {
            setToken(savedState.token);
            setWsUrl(savedState.wsUrl);
            setStreamUrl(constructStreamUrl(savedState.wsUrl));
            setIsPaired(true);
            console.log("Restored session from localStorage.")
          } else {
            console.log("Token from localStorage expired.");
            localStorage.removeItem(APP_STATE_KEY);
          }
        }
      } catch (error) {
        console.error("Error loading state from localStorage:", error);
        localStorage.removeItem(APP_STATE_KEY);
      }
    }
  }, [constructStreamUrl]);

  const handleSuccessfulPairing = (newWsUrl: string, newToken: string) => {
    const newStreamUrl = constructStreamUrl(newWsUrl);
    setWsUrl(newWsUrl);
    setToken(newToken);
    setStreamUrl(newStreamUrl);
    setIsPaired(true);
    // Save to localStorage
    localStorage.setItem(APP_STATE_KEY, JSON.stringify({ wsUrl: newWsUrl, token: newToken, streamUrl: newStreamUrl }));
    console.log("Pairing successful, session saved.");
  };

  const handleDisconnect = useCallback(() => {
    setIsPaired(false);
    setWsUrl(null);
    setToken(null);
    setStreamUrl(null);
    setShowStream(false);
    localStorage.removeItem(APP_STATE_KEY);
    console.log("Disconnected, session cleared.");
    // QRLanding will attempt to fetch a new pairing URL
  }, []);

  const toggleStreamVisibility = () => {
    setShowStream(prev => !prev);
  };

  if (!isPaired || !wsUrl || !token) {
    return <QRLanding onTokenAndUrlReceived={handleSuccessfulPairing} />;
  }

  return (
    <div className="h-screen flex flex-col bg-gray-900">
      <ChatBox 
        wsUrl={wsUrl} 
        token={token} 
        onDisconnect={handleDisconnect} 
        toggleStream={toggleStreamVisibility}
        isStreamVisible={showStream}
      />
      {streamUrl && <VideoCanvas streamUrl={streamUrl} showStream={showStream} />}
    </div>
  );
}

export default App;
