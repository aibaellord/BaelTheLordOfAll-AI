import { useState, useEffect } from 'react';
import { AlertTriangle, Key, X, ExternalLink } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

export function APIKeyWarning() {
  const [hasKeys, setHasKeys] = useState<boolean | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    // Check if any API keys are configured
    const checkKeys = async () => {
      try {
        const response = await fetch('/api/v1/settings/keys');
        if (response.ok) {
          const data = await response.json();
          // Check if any provider has a key configured (data.keys is an array)
          const configured = Array.isArray(data.keys) && data.keys.some(
            (provider: any) => provider.configured === true
          );
          setHasKeys(configured);
        } else {
          setHasKeys(false);
        }
      } catch (error) {
        // If API fails, assume no keys (for first-time setup)
        setHasKeys(false);
      }
    };

    checkKeys();

    // Check if user previously dismissed this session
    const dismissedSession = sessionStorage.getItem('api-key-warning-dismissed');
    if (dismissedSession === 'true') {
      setDismissed(true);
    }
  }, []);

  const handleDismiss = () => {
    setDismissed(true);
    sessionStorage.setItem('api-key-warning-dismissed', 'true');
  };

  const handleSetupClick = () => {
    navigate('/settings');
    // Scroll to secrets tab
    setTimeout(() => {
      const secretsTab = document.querySelector('[data-tab="secrets"]');
      if (secretsTab) {
        (secretsTab as HTMLElement).click();
      }
    }, 100);
  };

  // Don't show if keys are configured, still loading, or dismissed
  if (hasKeys !== false || dismissed) {
    return null;
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -50 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -50 }}
        className="fixed top-0 left-0 right-0 z-50 bg-amber-500/10 border-b border-amber-500/30 backdrop-blur-sm"
      >
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-amber-500/20">
              <AlertTriangle className="w-5 h-5 text-amber-500" />
            </div>
            <div>
              <p className="text-amber-200 font-medium">
                No API keys configured
              </p>
              <p className="text-amber-300/70 text-sm">
                Ba'el needs at least one LLM API key to function. Add your Anthropic, OpenAI, or other provider key.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleSetupClick}
              className="flex items-center gap-2 px-4 py-2 bg-amber-500 text-black font-medium rounded-lg hover:bg-amber-400 transition-colors"
            >
              <Key className="w-4 h-4" />
              Setup API Keys
            </button>
            <button
              onClick={handleDismiss}
              className="p-2 text-amber-300/70 hover:text-amber-200 transition-colors"
              title="Dismiss for this session"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

export default APIKeyWarning;
