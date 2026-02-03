import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home, Bug } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('🔥 BAEL Error Boundary caught an error:', error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleReload = () => {
    window.location.reload();
  };

  private handleGoHome = () => {
    window.location.href = '/';
  };

  private handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen bg-bael-bg flex items-center justify-center p-6">
          <div className="max-w-lg w-full bg-bael-surface border border-bael-border rounded-2xl p-8 text-center">
            {/* Icon */}
            <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-red-500/20 flex items-center justify-center">
              <AlertTriangle className="w-10 h-10 text-red-400" />
            </div>

            {/* Title */}
            <h1 className="text-2xl font-bold text-white mb-2">
              Something went wrong
            </h1>
            <p className="text-bael-muted mb-6">
              BAEL encountered an unexpected error. Don't worry, your data is safe.
            </p>

            {/* Error Details (collapsed) */}
            <details className="text-left mb-6 bg-bael-bg rounded-lg p-4">
              <summary className="cursor-pointer text-bael-muted text-sm flex items-center gap-2">
                <Bug className="w-4 h-4" />
                Technical Details
              </summary>
              <div className="mt-3 space-y-2">
                <p className="text-red-400 text-sm font-mono">
                  {this.state.error?.message || 'Unknown error'}
                </p>
                {this.state.error?.stack && (
                  <pre className="text-xs text-bael-muted overflow-x-auto max-h-40 overflow-y-auto p-2 bg-black/30 rounded">
                    {this.state.error.stack}
                  </pre>
                )}
              </div>
            </details>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <button
                onClick={this.handleReset}
                className="flex items-center justify-center gap-2 px-6 py-3 bg-bael-primary text-white rounded-lg hover:bg-bael-primary/80 transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Try Again
              </button>
              <button
                onClick={this.handleGoHome}
                className="flex items-center justify-center gap-2 px-6 py-3 bg-bael-border text-bael-text rounded-lg hover:bg-bael-border/80 transition-colors"
              >
                <Home className="w-4 h-4" />
                Go Home
              </button>
            </div>

            {/* Help text */}
            <p className="text-xs text-bael-muted mt-6">
              If this keeps happening, try refreshing the page or{' '}
              <button
                onClick={this.handleReload}
                className="text-bael-primary hover:underline"
              >
                hard reload
              </button>.
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
