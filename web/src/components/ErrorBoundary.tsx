import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertOctagon, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[React Desktop Shell Error]', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="h-screen w-screen bg-[#0D0E12] text-slate-200 flex items-center justify-center p-6 select-none font-sans">
          <div className="max-w-md bg-[#141620] border border-rose-500/30 rounded-xl p-6 space-y-4 shadow-2xl text-center">
            <div className="w-12 h-12 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400 mx-auto">
              <AlertOctagon className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
                Desktop Shell Runtime Error
              </h2>
              <p className="text-xs text-rose-400 font-mono-code">
                {this.state.error?.message || 'An unhandled exception occurred in the frontend shell.'}
              </p>
            </div>

            <button
              onClick={() => window.location.reload()}
              className="h-9 px-4 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs rounded border border-blue-400/30 flex items-center justify-center space-x-2 mx-auto"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Reload Workstation Shell</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
