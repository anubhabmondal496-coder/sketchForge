import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Home } from './pages/Home';

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

class GlobalErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('SketchForge GlobalErrorBoundary caught an unhandled error:', error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '100vh',
            backgroundColor: '#0f1115',
            color: '#f1f3f7',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            padding: '24px',
            textAlign: 'center',
          }}
        >
          <div
            style={{
              width: '48px',
              height: '48px',
              borderRadius: '8px',
              background: '#ea580c',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 800,
              fontSize: '20px',
              marginBottom: '16px',
            }}
          >
            SF
          </div>
          <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '8px' }}>
            SketchForge Recovered from an Unexpected Event
          </h2>
          <p style={{ color: '#8b95a5', fontSize: '13px', maxWidth: '420px', marginBottom: '20px' }}>
            {this.state.error?.message || 'An unexpected rendering issue occurred. Your workspace state has been protected.'}
          </p>
          <button
            type="button"
            onClick={this.handleReset}
            style={{
              background: '#ea580c',
              border: 'none',
              color: '#fff',
              padding: '10px 20px',
              borderRadius: '4px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Reload Workspace
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export const App: React.FC = () => {
  return (
    <GlobalErrorBoundary>
      <Home />
    </GlobalErrorBoundary>
  );
};

export default App;
