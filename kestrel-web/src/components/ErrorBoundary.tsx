"use client";

import { Component, type ReactNode } from "react";
import { logError } from "@/lib/log";

interface Props {
  children: ReactNode;
  /** Rendered when a child throws. Defaults to a compact inline message. */
  fallback?: ReactNode;
  /** Label for the logged error (e.g. "ChatWindow"). */
  label?: string;
}

interface State {
  hasError: boolean;
}

/** Catches render/runtime errors in a subtree so one broken panel doesn't blank
 *  the whole page. Use around independently-failing sections (chat stream, a
 *  stock-detail tab). For data-fetch errors prefer React Query's error state;
 *  this is the backstop for unexpected throws. */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: unknown): void {
    logError(`ErrorBoundary${this.props.label ? `:${this.props.label}` : ""}`, error);
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="p-6 text-center text-sm text-muted">
            <p>Something went wrong loading this section.</p>
          </div>
        )
      );
    }
    return this.props.children;
  }
}
