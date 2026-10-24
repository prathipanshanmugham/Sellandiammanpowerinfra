import { Component } from "react";

// Keeps one broken screen from blanking the whole app; the menu stays usable.
export default class ErrorBoundary extends Component {
  constructor(p) { super(p); this.state = { err: null }; }
  static getDerivedStateFromError(err) { return { err }; }
  componentDidUpdate(prev) { if (prev.resetKey !== this.props.resetKey && this.state.err) this.setState({ err: null }); }
  componentDidCatch(err, info) { console.error("Screen error", err, info?.componentStack?.slice(0, 400)); }
  render() {
    if (!this.state.err) return this.props.children;
    return (
      <div className="mx-auto max-w-lg py-20 text-center">
        <p className="font-display text-xl font-bold">This screen hit a problem</p>
        <p className="mt-2 text-sm text-muted">The rest of the app still works. Reload the page, or go back and try again. If it keeps happening, tell your administrator what you were doing.</p>
        <p className="mt-3 break-words font-mono text-xs text-muted">{String(this.state.err?.message || this.state.err).slice(0, 200)}</p>
        <button type="button" onClick={() => window.location.reload()} className="mt-5 rounded-md bg-ink px-4 py-2 text-sm font-semibold text-white">Reload</button>
      </div>
    );
  }
}
