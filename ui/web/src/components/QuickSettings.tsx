import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Settings,
  Moon,
  Sun,
  Volume2,
  VolumeX,
  Bell,
  BellOff,
  Zap,
  ZapOff,
  Eye,
  EyeOff,
  Keyboard,
  X,
  ChevronRight
} from 'lucide-react';

interface QuickSetting {
  id: string;
  label: string;
  description: string;
  iconOn: React.ElementType;
  iconOff: React.ElementType;
  value: boolean;
  onChange: (value: boolean) => void;
}

export function QuickSettingsPanel() {
  const [isOpen, setIsOpen] = useState(false);
  const [settings, setSettings] = useState({
    darkMode: true,
    soundEffects: true,
    notifications: true,
    animations: true,
    compactMode: false,
  });

  // Load settings from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('bael_quick_settings');
    if (saved) {
      try {
        setSettings(JSON.parse(saved));
      } catch (e) {
        console.error('Failed to load quick settings');
      }
    }
  }, []);

  // Save settings to localStorage
  const updateSetting = (key: keyof typeof settings, value: boolean) => {
    const newSettings = { ...settings, [key]: value };
    setSettings(newSettings);
    localStorage.setItem('bael_quick_settings', JSON.stringify(newSettings));

    // Apply settings
    if (key === 'darkMode') {
      document.documentElement.classList.toggle('light', !value);
    }
    if (key === 'animations') {
      document.documentElement.classList.toggle('reduce-motion', !value);
    }
    if (key === 'compactMode') {
      document.documentElement.classList.toggle('compact', value);
    }
  };

  const quickSettings: QuickSetting[] = [
    {
      id: 'darkMode',
      label: 'Dark Mode',
      description: 'Use dark color theme',
      iconOn: Moon,
      iconOff: Sun,
      value: settings.darkMode,
      onChange: (v) => updateSetting('darkMode', v)
    },
    {
      id: 'soundEffects',
      label: 'Sound Effects',
      description: 'Play UI sounds',
      iconOn: Volume2,
      iconOff: VolumeX,
      value: settings.soundEffects,
      onChange: (v) => updateSetting('soundEffects', v)
    },
    {
      id: 'notifications',
      label: 'Notifications',
      description: 'Show desktop notifications',
      iconOn: Bell,
      iconOff: BellOff,
      value: settings.notifications,
      onChange: (v) => updateSetting('notifications', v)
    },
    {
      id: 'animations',
      label: 'Animations',
      description: 'Enable UI animations',
      iconOn: Zap,
      iconOff: ZapOff,
      value: settings.animations,
      onChange: (v) => updateSetting('animations', v)
    },
    {
      id: 'compactMode',
      label: 'Compact Mode',
      description: 'Reduce spacing and padding',
      iconOn: Eye,
      iconOff: EyeOff,
      value: settings.compactMode,
      onChange: (v) => updateSetting('compactMode', v)
    },
  ];

  // Keyboard shortcut to toggle panel
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl/Cmd + Shift + S for quick settings
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 's') {
        e.preventDefault();
        setIsOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 left-6 z-40 w-10 h-10 rounded-full bg-bael-surface border border-bael-border shadow-lg flex items-center justify-center text-bael-muted hover:text-bael-text hover:border-bael-primary/50 transition-all"
        title="Quick Settings (⌘⇧S)"
      >
        <Settings className="w-5 h-5" />
      </button>

      {/* Panel */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/30 z-40"
              onClick={() => setIsOpen(false)}
            />

            {/* Panel */}
            <motion.div
              initial={{ opacity: 0, x: -300 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -300 }}
              className="fixed left-0 top-0 bottom-0 w-80 bg-bael-surface border-r border-bael-border shadow-2xl z-50 flex flex-col"
            >
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-bael-border">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-bael-primary/20 flex items-center justify-center">
                    <Settings className="w-5 h-5 text-bael-primary" />
                  </div>
                  <div>
                    <h2 className="font-semibold text-bael-text">Quick Settings</h2>
                    <p className="text-xs text-bael-muted">⌘⇧S to toggle</p>
                  </div>
                </div>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-2 text-bael-muted hover:text-bael-text hover:bg-bael-border rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Settings List */}
              <div className="flex-1 overflow-y-auto p-4 space-y-2">
                {quickSettings.map(setting => {
                  const IconOn = setting.iconOn;
                  const IconOff = setting.iconOff;
                  const Icon = setting.value ? IconOn : IconOff;

                  return (
                    <button
                      key={setting.id}
                      onClick={() => setting.onChange(!setting.value)}
                      className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all ${
                        setting.value
                          ? 'bg-bael-primary/10 border border-bael-primary/30'
                          : 'bg-bael-bg border border-transparent hover:border-bael-border'
                      }`}
                    >
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                        setting.value ? 'bg-bael-primary/20' : 'bg-bael-border'
                      }`}>
                        <Icon className={`w-5 h-5 ${setting.value ? 'text-bael-primary' : 'text-bael-muted'}`} />
                      </div>
                      <div className="flex-1 text-left">
                        <p className={`text-sm font-medium ${setting.value ? 'text-bael-text' : 'text-bael-muted'}`}>
                          {setting.label}
                        </p>
                        <p className="text-xs text-bael-muted">{setting.description}</p>
                      </div>
                      <div className={`w-10 h-6 rounded-full p-1 transition-colors ${
                        setting.value ? 'bg-bael-primary' : 'bg-bael-border'
                      }`}>
                        <motion.div
                          animate={{ x: setting.value ? 16 : 0 }}
                          className="w-4 h-4 rounded-full bg-white shadow"
                        />
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* Footer */}
              <div className="p-4 border-t border-bael-border">
                <a
                  href="/settings"
                  className="flex items-center justify-between p-3 bg-bael-bg rounded-xl hover:bg-bael-border transition-colors group"
                >
                  <span className="text-sm text-bael-text">All Settings</span>
                  <ChevronRight className="w-4 h-4 text-bael-muted group-hover:text-bael-text transition-colors" />
                </a>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

export default QuickSettingsPanel;
