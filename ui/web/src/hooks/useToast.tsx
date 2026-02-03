import toast, { Toaster as HotToaster } from 'react-hot-toast';
import { CheckCircle, XCircle, AlertTriangle, Info, Loader2 } from 'lucide-react';
import React from 'react';

// Toast styling configuration
export const toastConfig = {
  duration: 4000,
  position: 'bottom-right' as const,
  style: {
    background: '#1a1a2e',
    color: '#e2e8f0',
    border: '1px solid #2d2d44',
    borderRadius: '12px',
    padding: '12px 16px',
    fontSize: '14px',
    maxWidth: '400px',
  },
};

// Custom toast functions with icons
export const showToast = {
  success: (message: string) => {
    toast.success(message, {
      icon: <CheckCircle className="w-5 h-5 text-green-400" />,
      ...toastConfig,
    });
  },

  error: (message: string) => {
    toast.error(message, {
      icon: <XCircle className="w-5 h-5 text-red-400" />,
      duration: 6000,
      ...toastConfig,
    });
  },

  warning: (message: string) => {
    toast(message, {
      icon: <AlertTriangle className="w-5 h-5 text-yellow-400" />,
      ...toastConfig,
    });
  },

  info: (message: string) => {
    toast(message, {
      icon: <Info className="w-5 h-5 text-blue-400" />,
      ...toastConfig,
    });
  },

  loading: (message: string) => {
    return toast.loading(message, {
      icon: <Loader2 className="w-5 h-5 text-purple-400 animate-spin" />,
      ...toastConfig,
    });
  },

  promise: <T,>(
    promise: Promise<T>,
    messages: { loading: string; success: string; error: string }
  ) => {
    return toast.promise(promise, messages, toastConfig);
  },

  dismiss: (toastId?: string) => {
    if (toastId) {
      toast.dismiss(toastId);
    } else {
      toast.dismiss();
    }
  },
};

// Toaster component to be added to App
export function Toaster() {
  return (
    <HotToaster
      position="bottom-right"
      reverseOrder={false}
      gutter={8}
      toastOptions={{
        ...toastConfig,
        success: {
          style: {
            ...toastConfig.style,
            borderColor: '#22c55e33',
          },
        },
        error: {
          style: {
            ...toastConfig.style,
            borderColor: '#ef444433',
          },
        },
      }}
    />
  );
}

// Hook for easy access
export function useToast() {
  return showToast;
}

export default showToast;
