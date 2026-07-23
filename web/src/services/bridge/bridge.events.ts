/**
 * PyWebView Event Listener Manager
 * Receives asynchronous events pushed from Python backend to Javascript.
 */

type EventCallback<T = any> = (data: T) => void;

class BridgeEventManager {
  private listeners: Map<string, Set<EventCallback>> = new Map();

  constructor() {
    // Expose global callback interface for PyWebView window calls
    if (typeof window !== 'undefined') {
      (window as any).__pywebview_event_listener__ = (eventName: string, payload: any) => {
        this.emit(eventName, payload);
      };
    }
  }

  public subscribe<T = any>(eventName: string, callback: EventCallback<T>): () => void {
    if (!this.listeners.has(eventName)) {
      this.listeners.set(eventName, new Set());
    }
    this.listeners.get(eventName)!.add(callback);

    // Return unsubscribe handler
    return () => {
      const set = this.listeners.get(eventName);
      if (set) {
        set.delete(callback);
      }
    };
  }

  public emit<T = any>(eventName: string, payload: T): void {
    const set = this.listeners.get(eventName);
    if (set) {
      set.forEach((cb) => {
        try {
          cb(payload);
        } catch (err) {
          console.error(`Error in event listener for ${eventName}:`, err);
        }
      });
    }
  }
}

export const bridgeEvents = new BridgeEventManager();
