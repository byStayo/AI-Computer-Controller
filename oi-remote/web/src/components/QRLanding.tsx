import React, { useEffect, useState } from 'react';
import QRCodeStylized from 'qrcode.react'; // Using qrcode.react for better styling options if needed

interface QRLandingProps {
  onTokenAndUrlReceived: (wsUrl: string, token: string) => void;
  initialPairingUrl?: string; // Optional: if a pairing URL is fetched once
}

const QRLanding: React.FC<QRLandingProps> = ({ onTokenAndUrlReceived, initialPairingUrl }) => {
  const [pairingUrl, setPairingUrl] = useState<string | null>(initialPairingUrl || null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(!initialPairingUrl);

  const gatewayHttpUrl = `${window.location.protocol}//${window.location.hostname}:3333`; // Assuming gateway is on same host, port 3333

  useEffect(() => {
    if (initialPairingUrl) return; // Don't fetch if already provided

    const fetchPairingUrl = async () => {
      setIsLoading(true);
      try {
        // Fetch the text URL which includes the token directly from the gateway
        const response = await fetch(`${gatewayHttpUrl}/pair/url`);
        if (!response.ok) {
          throw new Error(`Failed to fetch pairing URL: ${response.status} ${response.statusText}`);
        }
        const url = await response.text();
        setPairingUrl(url);
        setError(null);
      } catch (err: any) {
        console.error("Error fetching pairing URL:", err);
        setError(err.message || 'Could not connect to the desktop gateway. Ensure it is running.');
        setPairingUrl(null);
      }
      setIsLoading(false);
    };

    fetchPairingUrl();
    // Optional: Set up a poller if the URL/token can expire or change, or a refresh button
  }, [initialPairingUrl, gatewayHttpUrl]);

  useEffect(() => {
    // This effect simulates 'scanning' by trying to parse the URL and extract token
    // In a real mobile app, you'd use a camera QR scanner library.
    // For web, this component shows the QR for a mobile device to scan.
    // If the PWA itself is MEANT to be the mobile client, then after showing the QR,
    // it should wait for the user to effectively say "I've set up the desktop app".
    // The current logic is for the PWA to *display* the QR that a *phone* scans.
    // However, the prompt implies the PWA *is* the phone client.
    // Let's adjust: The PWA needs to GET the ws_url and token to connect.
    // So, the QR displayed by desktop app would contain `http://PWA_HOST/connect?ws_url=...&token=...`
    // OR, the desktop app shows a QR for `ws://desktop_ip:3333/ws?token=...`
    // and THIS PWA allows pasting or scanning that URL.

    // For this MVP, let's assume PWA gets the `pairingUrl` (which is `ws://...token=...`)
    // and then uses it.
    if (pairingUrl) {
      try {
        const url = new URL(pairingUrl);
        const token = url.searchParams.get('token');
        if (token) {
          // Automatically call onTokenAndUrlReceived once we have a valid pairingUrl
          // This simulates successful 'acquisition' of the connection details.
          onTokenAndUrlReceived(pairingUrl, token);
        }
      } catch (e) {
        console.error("Invalid pairing URL format", e);
        setError("Received an invalid pairing URL from the gateway.");
      }
    }
  }, [pairingUrl, onTokenAndUrlReceived]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-4 bg-gray-800">
        <p className="text-xl text-gray-300">Connecting to desktop gateway...</p>
        <div className="mt-4 w-12 h-12 border-4 border-dashed rounded-full animate-spin border-sky-400"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 bg-red-900 text-white">
        <h2 className="text-2xl font-semibold mb-4">Pairing Error</h2>
        <p className="text-center mb-6">{error}</p>
        <p className="text-sm text-red-200">Please ensure the Stupidly-Simple Remote AI desktop application is running on your computer and accessible on your local network.</p>
        <button 
          onClick={() => window.location.reload()} 
          className="mt-6 px-6 py-2 bg-red-600 hover:bg-red-500 rounded-lg text-white font-semibold transition-colors duration-150"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  if (!pairingUrl) {
    // This state should ideally be covered by isLoading or error
    return <div className="flex items-center justify-center h-full p-4 bg-gray-800 text-gray-400">Waiting for pairing URL...</div>;
  }

  // If the PWA itself is the client, it doesn't need to *show* this QR.
  // It would have *received* this URL (e.g. by user scanning QR from desktop and PWA capturing it, or manual paste)
  // Since we're automatically calling onTokenAndUrlReceived, this visual display is more for fallback/info.
  // In a typical flow, this component might not even be visible if pairingUrl is obtained quickly.
  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-6 bg-gradient-to-br from-gray-900 to-gray-800 text-gray-100">
      <div className="bg-gray-800 p-8 rounded-xl shadow-2xl text-center max-w-md">
        <h1 className="text-3xl font-bold mb-3 text-sky-400">Pair with Desktop</h1>
        <p className="mb-6 text-gray-300">
          The desktop application should display a QR code. If this PWA were on a separate phone, you'd scan it. 
          Since this PWA is the client, it has automatically fetched the connection details below.
        </p>
        
        <div className="p-4 bg-white rounded-lg inline-block shadow-md mb-6">
          <QRCodeStylized value={pairingUrl} size={200} level="M" fgColor="#000000" bgColor="#FFFFFF" />
        </div>
        
        <p className="text-xs text-gray-400 break-all mb-2">Connection URL (auto-used):</p>
        <p className="text-xs text-sky-500 break-all font-mono bg-gray-700 p-2 rounded mb-6">{pairingUrl}</p>

        <p className="text-sm text-gray-300">
          If pairing succeeds, you'll be redirected to the chat interface shortly.
        </p>
        <div className="mt-6 w-8 h-8 border-2 border-dashed rounded-full animate-spin border-sky-400 mx-auto"></div>
      </div>
    </div>
  );
};

export default QRLanding;
