import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Zap,
  Key,
  CheckCircle,
  ChevronRight,
  Settings,
  Sparkles,
  Shield,
  Brain,
  ExternalLink,
  AlertCircle,
  Loader2
} from 'lucide-react';

const FIRST_RUN_KEY = 'bael_first_run_completed';
const SETUP_VERSION = '2.1'; // Increment to show wizard again after major updates

interface SetupWizardProps {
  onComplete?: () => void;
}

export function SetupWizard({ onComplete }: SetupWizardProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [step, setStep] = useState(0);
  const [apiKeyStatus, setApiKeyStatus] = useState<'checking' | 'configured' | 'missing'>('checking');
  const [healthStatus, setHealthStatus] = useState<'checking' | 'healthy' | 'error'>('checking');

  // Check if first run
  useEffect(() => {
    const completed = localStorage.getItem(FIRST_RUN_KEY);
    if (completed !== SETUP_VERSION) {
      setIsOpen(true);
      checkSetupStatus();
    }
  }, []);

  const checkSetupStatus = async () => {
    // Check API health
    try {
      const healthRes = await fetch('/api/health');
      setHealthStatus(healthRes.ok ? 'healthy' : 'error');
    } catch {
      setHealthStatus('error');
    }

    // Check if API keys are configured
    try {
      const secretsRes = await fetch('/api/v1/settings/secrets/status');
      if (secretsRes.ok) {
        const data = await secretsRes.json();
        const hasKeys = data.configured && Object.values(data.providers || {}).some(Boolean);
        setApiKeyStatus(hasKeys ? 'configured' : 'missing');
      } else {
        // Check localStorage fallback
        const localSecrets = localStorage.getItem('bael_secrets_status');
        if (localSecrets) {
          const parsed = JSON.parse(localSecrets);
          const hasKeys = Object.values(parsed).some(Boolean);
          setApiKeyStatus(hasKeys ? 'configured' : 'missing');
        } else {
          setApiKeyStatus('missing');
        }
      }
    } catch {
      setApiKeyStatus('missing');
    }
  };

  const handleComplete = () => {
    localStorage.setItem(FIRST_RUN_KEY, SETUP_VERSION);
    setIsOpen(false);
    onComplete?.();
  };

  const handleSkip = () => {
    localStorage.setItem(FIRST_RUN_KEY, SETUP_VERSION);
    setIsOpen(false);
  };

  const steps = [
    {
      title: 'Welcome to BAEL',
      subtitle: 'The Lord of All AI Agents',
      icon: Sparkles,
      content: (
        <div className="space-y-4">
          <p className="text-bael-muted">
            BAEL is your autonomous AI agent system with multi-agent orchestration,
            workflow automation, and advanced reasoning capabilities.
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-purple-500/10 border border-purple-500/30 rounded-lg">
              <Brain className="w-5 h-5 text-purple-400 mb-2" />
              <p className="text-sm font-medium text-white">25+ Reasoning Engines</p>
              <p className="text-xs text-bael-muted">Causal, temporal, game theory, and more</p>
            </div>
            <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
              <Zap className="w-5 h-5 text-blue-400 mb-2" />
              <p className="text-sm font-medium text-white">200+ Capabilities</p>
              <p className="text-xs text-bael-muted">Memory, agents, evolution, perception</p>
            </div>
          </div>
        </div>
      )
    },
    {
      title: 'System Status',
      subtitle: 'Checking your setup',
      icon: Shield,
      content: (
        <div className="space-y-4">
          <div className="space-y-3">
            {/* API Health */}
            <div className="flex items-center justify-between p-3 bg-bael-bg rounded-lg">
              <div className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  healthStatus === 'healthy' ? 'bg-green-500/20' :
                  healthStatus === 'error' ? 'bg-red-500/20' : 'bg-blue-500/20'
                }`}>
                  {healthStatus === 'checking' ? (
                    <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                  ) : healthStatus === 'healthy' ? (
                    <CheckCircle className="w-4 h-4 text-green-400" />
                  ) : (
                    <AlertCircle className="w-4 h-4 text-red-400" />
                  )}
                </div>
                <div>
                  <p className="text-sm font-medium text-white">API Server</p>
                  <p className="text-xs text-bael-muted">
                    {healthStatus === 'checking' ? 'Checking...' :
                     healthStatus === 'healthy' ? 'Connected and running' :
                     'Not reachable'}
                  </p>
                </div>
              </div>
            </div>

            {/* API Keys */}
            <div className="flex items-center justify-between p-3 bg-bael-bg rounded-lg">
              <div className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  apiKeyStatus === 'configured' ? 'bg-green-500/20' :
                  apiKeyStatus === 'missing' ? 'bg-yellow-500/20' : 'bg-blue-500/20'
                }`}>
                  {apiKeyStatus === 'checking' ? (
                    <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                  ) : apiKeyStatus === 'configured' ? (
                    <CheckCircle className="w-4 h-4 text-green-400" />
                  ) : (
                    <Key className="w-4 h-4 text-yellow-400" />
                  )}
                </div>
                <div>
                  <p className="text-sm font-medium text-white">API Keys</p>
                  <p className="text-xs text-bael-muted">
                    {apiKeyStatus === 'checking' ? 'Checking...' :
                     apiKeyStatus === 'configured' ? 'At least one provider configured' :
                     'No API keys found'}
                  </p>
                </div>
              </div>
              {apiKeyStatus === 'missing' && (
                <a
                  href="/settings"
                  className="text-xs px-3 py-1.5 bg-yellow-500/20 text-yellow-400 rounded-lg hover:bg-yellow-500/30 transition-colors"
                >
                  Configure
                </a>
              )}
            </div>
          </div>

          {apiKeyStatus === 'missing' && (
            <div className="p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
              <p className="text-sm text-yellow-400">
                ⚠️ To use BAEL's AI features, you'll need to configure at least one LLM provider API key in Settings.
              </p>
            </div>
          )}
        </div>
      )
    },
    {
      title: 'Quick Start',
      subtitle: 'You\'re ready to go!',
      icon: Zap,
      content: (
        <div className="space-y-4">
          <p className="text-bael-muted">
            Here are some ways to get started:
          </p>
          <div className="space-y-2">
            <a href="/chat" className="flex items-center gap-3 p-3 bg-bael-bg hover:bg-bael-border rounded-lg transition-colors group">
              <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-purple-400" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-white">Start a Chat</p>
                <p className="text-xs text-bael-muted">Begin a conversation with BAEL</p>
              </div>
              <ChevronRight className="w-4 h-4 text-bael-muted group-hover:text-white transition-colors" />
            </a>

            <a href="/council" className="flex items-center gap-3 p-3 bg-bael-bg hover:bg-bael-border rounded-lg transition-colors group">
              <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <Brain className="w-5 h-5 text-blue-400" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-white">Council Deliberation</p>
                <p className="text-xs text-bael-muted">Multi-perspective AI discussion</p>
              </div>
              <ChevronRight className="w-4 h-4 text-bael-muted group-hover:text-white transition-colors" />
            </a>

            <a href="/settings" className="flex items-center gap-3 p-3 bg-bael-bg hover:bg-bael-border rounded-lg transition-colors group">
              <div className="w-10 h-10 rounded-lg bg-gray-500/20 flex items-center justify-center">
                <Settings className="w-5 h-5 text-gray-400" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-white">Configure Settings</p>
                <p className="text-xs text-bael-muted">API keys, preferences, and more</p>
              </div>
              <ChevronRight className="w-4 h-4 text-bael-muted group-hover:text-white transition-colors" />
            </a>
          </div>

          <div className="text-center pt-2">
            <p className="text-xs text-bael-muted">
              Press <kbd className="px-1.5 py-0.5 bg-bael-bg rounded text-bael-text">⌘</kbd> + <kbd className="px-1.5 py-0.5 bg-bael-bg rounded text-bael-text">K</kbd> anytime to open the command palette
            </p>
          </div>
        </div>
      )
    }
  ];

  const currentStep = steps[step];
  const StepIcon = currentStep.icon;

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          className="w-full max-w-lg bg-bael-surface border border-bael-border rounded-2xl overflow-hidden"
        >
          {/* Header */}
          <div className="p-6 border-b border-bael-border">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-purple-600/20 flex items-center justify-center">
                <StepIcon className="w-6 h-6 text-purple-400" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">{currentStep.title}</h2>
                <p className="text-sm text-bael-muted">{currentStep.subtitle}</p>
              </div>
            </div>

            {/* Progress dots */}
            <div className="flex items-center justify-center gap-2 mt-4">
              {steps.map((_, idx) => (
                <div
                  key={idx}
                  className={`w-2 h-2 rounded-full transition-colors ${
                    idx === step ? 'bg-purple-500' :
                    idx < step ? 'bg-purple-500/50' : 'bg-bael-border'
                  }`}
                />
              ))}
            </div>
          </div>

          {/* Content */}
          <div className="p-6">
            {currentStep.content}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between px-6 py-4 border-t border-bael-border bg-bael-bg/50">
            <button
              onClick={handleSkip}
              className="text-sm text-bael-muted hover:text-white transition-colors"
            >
              Skip setup
            </button>
            <div className="flex items-center gap-3">
              {step > 0 && (
                <button
                  onClick={() => setStep(step - 1)}
                  className="px-4 py-2 text-sm text-bael-muted hover:text-white transition-colors"
                >
                  Back
                </button>
              )}
              {step < steps.length - 1 ? (
                <button
                  onClick={() => setStep(step + 1)}
                  className="flex items-center gap-2 px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-500 transition-colors"
                >
                  Next
                  <ChevronRight className="w-4 h-4" />
                </button>
              ) : (
                <button
                  onClick={handleComplete}
                  className="flex items-center gap-2 px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-500 transition-colors"
                >
                  Get Started
                  <Zap className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

export default SetupWizard;
