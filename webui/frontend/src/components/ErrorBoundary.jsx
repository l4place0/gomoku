import { Component } from 'react';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="card" style={{ borderColor: 'var(--red)', margin: 24 }}>
          <h2 style={{ color: 'var(--red)' }}>Something went wrong</h2>
          <p style={{ color: 'var(--text-dim)', marginTop: 8 }}>{this.state.error?.message}</p>
          <button className="btn" onClick={() => this.setState({ hasError: false, error: null })} style={{ marginTop: 12 }}>
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
