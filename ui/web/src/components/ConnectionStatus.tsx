import React, { useEffect, useState } from 'react';
import { Wifi, WifiOff, RefreshCw, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface ConnectionStatusProps {
  className?: string;
}

export function ConnectionStatus({ className }: ConnectionStatusProps) {
  const [isConnected, setIsConnected] = useState(true);
  const [isChecking, setIsChecking] = useState(false);
  const [lastCheck, setLastCheck] = useState<Date | null>(null);
  const [showBanner, setShowBanner] = useState(false);

  const checkConnection = async () => {
    setIsChecking(true);
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      const response = await fetch('/api/health', {
        signal: controller.signal,
        cache: 'no-store'
      });

      clearTimeout(timeoutId);

      const wasConnected = isConnected;
      const nowConnected = response.ok;

      setIsConnected(nowConnected);
      setLastCheck(new Date());

      // Show banner on status change
      if (wasConnected !== nowConnected) {
        setShowBanner(true);
        // Auto-hide after 5 seconds if reconnected
        if (nowConnected) {
          setTimeout(() => setShowBanner(false), 5000);
        }
      }
    } catch (error) {
      const wasConnected = isConnected;
      setIsConnected(false);
      setLastCheck(new Date());

      if (wasConnected) {
        setShowBanner(true);
      }
    } finally {
      setIsChecking(false);
    }
  };

  // Check connection on mount and every 30 seconds
  useEffect(() => {
    checkConnection();
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, []);

  // Also check on window focus
  useEffect(() => {
    const handleFocus = () => {
      checkConnection();
    };
    window.addEventListener('focus', handleFocus);
    return () => window.removeEventListener('focus', handleFocus);
  }, []);

  return (
    <>
      {/* Floating banner for connection status changes */}
      <AnimatePresence>
        {showBanner && (
          <motion.div
            initial={{ opacity: 0, y: -50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -50 }}
            className={`fixed top-0 left-0 right-0 z-50 ${className || ''}`}
          >
            <div className={`flex items-center justify-center gap-3 px-4 py-3 text-sm font-medium ${
              isConnected
                ? 'bg-green-500/20 text-green-400 border-b border-green-500/30'
                : 'bg-red-500/20 text-red-400 border-b border-red-500/30'
            }`}>
              {isConnected ? (
                <>
                  <Wifi className="w-4 h-4" />
                  <span>Connection restored! BAEL is back online.</span>
                  <button
                    onClick={() => setShowBanner(false)}
                    className="ml-4 px-2 py-1 bg-green-500/20 hover:bg-green-500/30 rounded transition-colors"
                  >
                    Dismiss
                  </button>
                </>
              ) : (
                <>
                  <WifiOff className="w-4 h-4" />
                  <span>Connection lost. Trying to reconnect...</span>
                  <button
                    onClick={checkConnection}
                    disabled={isChecking}
                    className="ml-4 px-2 py-1 bg-red-500/20 hover:bg-red-500/30 rounded transition-colors flex items-center gap-1"
                  >
                    {isChecking ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <RefreshCw className="w-3 h-3" />
                    )}
                    Retry
                  </button>
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Persistent offline indicator in corner */}
      <AnimatePresence>
        {!isConnected && !showBanner && (
          <motion.button
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            onClick={() => setShowBanner(true)}
            className="fixed bottom-4 right-4 z-40 flex items-center gap-2 px-3 py-2 bg-red-500/20 text-red-400 border border-red-500/30 rounded-full hover:bg-red-500/30 transition-colors"
          >
            <WifiOff className="w-4 h-4" />
            <span className="text-xs font-medium">Offline</span>
          </motion.button>
        )}
      </AnimatePresence>
    </>
  );
}

export default ConnectionStatus;
