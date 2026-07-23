/**
 * Mackanized flasher Centralized Desktop Command Registry
 * 
 * Maps application operations to keyboard shortcuts, command palettes, and UI buttons.
 */

export interface DesktopCommand {
  id: string;
  title: string;
  description: string;
  category: 'File' | 'ECU' | 'Diagnostics' | 'View' | 'Settings';
  shortcut?: string;
  safetyLevel: 'safe' | 'dangerous' | 'critical';
  action: () => void;
}

class CommandRegistry {
  private commands: Map<string, DesktopCommand> = new Map();
  private listeners: Set<() => void> = new Set();

  register(command: DesktopCommand): void {
    this.commands.set(command.id, command);
    this.notify();
  }

  get(id: string): DesktopCommand | undefined {
    return this.commands.get(id);
  }

  getAll(): DesktopCommand[] {
    return Array.from(this.commands.values());
  }

  subscribe(callback: () => void): () => void {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  private notify(): void {
    this.listeners.forEach((fn) => fn());
  }

  execute(id: string): void {
    const cmd = this.commands.get(id);
    if (cmd) {
      console.log(`[Command Registry] Executing command: ${id}`);
      cmd.action();
    }
  }
}

export const globalCommandRegistry = new CommandRegistry();
