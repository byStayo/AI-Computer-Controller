import React, { useState, useEffect, useRef, FormEvent } from 'react';
import { FiSend, FiVideo, FiVideoOff, FiPower, FiCopy, FiCheckCircle, FiAlertTriangle } from 'react-icons/fi'; // Example icons

interface Message {
  id: string;
  sender: 'user' | 'ai' | 'system';
  text: string;
  timestamp: Date;
}

interface ChatBoxProps {
  wsUrl: string;
  token: string;
  onDisconnect: () => void;
  toggleStream: () => void;
  isStreamVisible: boolean;
}

const ChatBox: React.FC<ChatBoxProps> = ({ wsUrl, token, onDisconnect, toggleStream, isStreamVisible }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [currentMode, setCurrentMode] = useState<'YOLO' | 'SAFE'>('YOLO');
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!wsUrl || !token) return;

    const connect = () => {
      const socket = new WebSocket(`${wsUrl}`); // Token is already in wsUrl query params
      setError(null);

      socket.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setMessages(prev => [...prev, { id: Date.now().toString(), sender: 'system', text: 'Connected to desktop agent.', timestamp: new Date() }]);
        // Optionally set initial mode or request status
        socket.send(JSON.stringify({ type: 'set_mode', payload: { mode: currentMode } }));
      };

      socket.onmessage = (event) => {
        try {
          const received = JSON.parse(event.data as string);
          console.log('Received from server:', received);

          if (received.type === 'response') {
            setMessages(prev => [...prev, { id: Date.now().toString(), sender: 'ai', text: received.payload.text, timestamp: new Date() }]);
          } else if (received.type === 'stream_status') {
            setMessages(prev => [...prev, { id: Date.now().toString(), sender: 'system', text: `Screen stream ${received.payload.status}.`, timestamp: new Date() }]);
          } else if (received.type === 'mode_status') {
            setMessages(prev => [...prev, { id: Date.now().toString(), sender: 'system', text: `Mode changed to ${received.payload.mode}.`, timestamp: new Date() }]);
            setCurrentMode(received.payload.mode);
          } else if (received.type === 'error') {
            setMessages(prev => [...prev, { id: Date.now().toString(), sender: 'system', text: `Error: ${received.payload}`, timestamp: new Date() }]);
            setError(`Server error: ${received.payload}`);
          }
        } catch (e) {
          console.error("Error processing message from server:", e);
          setMessages(prev => [...prev, { id: Date.now().toString(), sender: 'system', text: "Received unparseable message from server.", timestamp: new Date() }]);
        }
      };

      socket.onerror = (err) => {
        console.error('WebSocket error:', err);
        setError('WebSocket connection error. Attempting to reconnect...');
        setMessages(prev => [...prev, { id: Date.now().toString(), sender: 'system', text: 'Connection error.', timestamp: new Date() }]);
        setIsConnected(false); 
      };

      socket.onclose = (event) => {
        console.log('WebSocket disconnected:', event.reason, event.code);
        setIsConnected(false);
        if (event.code === 4001) { // Custom code for auth failure from gateway
            setError(`Connection closed: ${event.reason || 'Authentication failed'}. Please re-pair.`);
            setMessages(prev => [...prev, { id: Date.now().toString(), sender: 'system', text: `Disconnected: ${event.reason}. Please re-pair.`, timestamp: new Date() }]);
            onDisconnect(); // Trigger re-pairing logic
        } else if (event.wasClean) {
            setMessages(prev => [...prev, { id: Date.now().toString(), sender: 'system', text: 'Disconnected.', timestamp: new Date() }]);
        } else {
            setError('Connection lost. Attempting to reconnect in 5 seconds...');
            setMessages(prev => [...prev, { id: Date.now().toString(), sender: 'system', text: 'Connection lost. Retrying...', timestamp: new Date() }]);
            setTimeout(connect, 5000); // Retry connection
        }
      };
      setWs(socket);
    };

    connect();

    return () => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close(1000, "Client initiated disconnect");
      }
      setWs(null);
    };
  }, [wsUrl, token]); // Removed onDisconnect from deps to avoid re-connect loop if onDisconnect changes parent state triggering re-render

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = (e: FormEvent) => {
    e.preventDefault();
    if (input.trim() && ws && isConnected) {
      const message: Message = { id: Date.now().toString(), sender: 'user', text: input, timestamp: new Date() };
      setMessages(prev => [...prev, message]);
      ws.send(JSON.stringify({ type: 'command', payload: { text: input } }));
      setInput('');
    }
  };

  const handleToggleMode = () => {
    const newMode = currentMode === 'YOLO' ? 'SAFE' : 'YOLO';
    if (ws && isConnected) {
      ws.send(JSON.stringify({ type: 'set_mode', payload: { mode: newMode } }));
    }
  };

  const handleStreamToggle = () => {
    if (ws && isConnected) {
      const action = isStreamVisible ? "STOP" : "WATCH";
      ws.send(JSON.stringify({ type: 'control_stream', payload: { action: action } }));
      toggleStream(); // Update parent state for VideoCanvas visibility
    }
  }

  return (
    <div className="flex flex-col h-full max-h-screen bg-gray-800 shadow-xl overflow-hidden">
      <header className="bg-gray-700 p-3 shadow-md z-10">
        <div className="flex justify-between items-center">
          <h2 className="text-xl font-semibold text-sky-400">Remote AI Control</h2>
          <div className="flex items-center space-x-3">
            <button 
              onClick={handleToggleMode} 
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all duration-150 flex items-center space-x-1.5 
                ${currentMode === 'YOLO' ? 'bg-red-500 hover:bg-red-600' : 'bg-green-500 hover:bg-green-600'} text-white`}
            >
              {currentMode === 'YOLO' ? <FiAlertTriangle/> : <FiCheckCircle/>}
              <span>Mode: {currentMode}</span>
            </button>
            <button onClick={handleStreamToggle} className="p-2 text-gray-300 hover:text-sky-400 transition-colors duration-150" title={isStreamVisible ? "Hide Stream" : "Watch Stream"}>
              {isStreamVisible ? <FiVideoOff size={20} /> : <FiVideo size={20} />}
            </button>
            <button onClick={onDisconnect} className="p-2 text-gray-300 hover:text-red-500 transition-colors duration-150" title="Disconnect and Re-pair">
              <FiPower size={20} />
            </button>
          </div>
        </div>
        {!isConnected && (
            <div className="text-center text-xs py-1 bg-yellow-500 text-yellow-900 font-semibold">
                {error || 'Attempting to connect...'}
            </div>
        )}
      </header>

      <div className="flex-grow overflow-y-auto p-4 space-y-3 bg-gray-800 scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-700">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div 
              className={`max-w-xl px-4 py-2.5 rounded-xl shadow ${ 
                msg.sender === 'user' ? 'bg-sky-600 text-white rounded-br-none' : 
                msg.sender === 'ai' ? 'bg-gray-600 text-gray-100 rounded-bl-none' : 
                'bg-gray-700 text-xs text-gray-400 italic text-center w-full py-1 rounded-md'
              }`}
            >
              {msg.sender !== 'system' && (
                <p className="whitespace-pre-wrap">{msg.text}</p>
              )}
              {msg.sender === 'system' && <p className='text-center'>{msg.text}</p>}
              {msg.sender !== 'system' && (
                <div className="text-xs mt-1.5 opacity-70 ${msg.sender === 'user' ? 'text-right' : 'text-left'}">
                  {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSend} className="bg-gray-700 p-3 border-t border-gray-600 shadow- ऊपर">
        <div className="flex items-center bg-gray-600 rounded-lg overflow-hidden">
          <input 
            type="text" 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={isConnected ? "Chat with your desktop..." : "Connecting..."}
            className="flex-grow p-3 bg-transparent text-gray-100 placeholder-gray-400 focus:outline-none disabled:opacity-50"
            disabled={!isConnected}
          />
          <button type="submit" disabled={!isConnected || !input.trim()} className="p-3 text-sky-400 hover:text-sky-300 disabled:text-gray-500 transition-colors duration-150">
            <FiSend size={22} />
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChatBox;
