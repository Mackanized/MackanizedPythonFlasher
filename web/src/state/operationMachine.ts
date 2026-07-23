/**
 * Operation State Machine for Mackanized flasher Workflows
 * 
 * Replaces scattered boolean flags with explicit state transitions.
 */

export type OperationState =
  | 'idle'
  | 'connecting'
  | 'connectionFailed'
  | 'connected'
  | 'identifying'
  | 'ecuIdentified'
  | 'fileValidating'
  | 'readyToFlash'
  | 'flashPreparing'
  | 'flashErasing'
  | 'flashProgramming'
  | 'flashVerifying'
  | 'flashSuccess'
  | 'flashFailed'
  | 'recoveryRequired';

export interface OperationContext {
  adapterId: string | null;
  ecuName: string | null;
  selectedFilePath: string | null;
  selectedRegion: string;
  currentPhaseText: string;
  progressPercent: number;
  errorMessage: string | null;
}

export class OperationMachine {
  private state: OperationState = 'idle';
  private context: OperationContext = {
    adapterId: null,
    ecuName: null,
    selectedFilePath: null,
    selectedRegion: 'full',
    currentPhaseText: 'Idle',
    progressPercent: 0,
    errorMessage: null,
  };
  private listeners: Set<(state: OperationState, ctx: OperationContext) => void> = new Set();

  getState(): OperationState {
    return this.state;
  }

  getContext(): OperationContext {
    return { ...this.context };
  }

  subscribe(callback: (state: OperationState, ctx: OperationContext) => void): () => void {
    this.listeners.add(callback);
    callback(this.state, this.context);
    return () => this.listeners.delete(callback);
  }

  private transition(nextState: OperationState, updateCtx?: Partial<OperationContext>): void {
    this.state = nextState;
    if (updateCtx) {
      this.context = { ...this.context, ...updateCtx };
    }
    console.log(`[Operation FSM] Transition ➔ ${nextState}`, this.context);
    this.listeners.forEach((fn) => fn(this.state, this.context));
  }

  selectFile(filePath: string): void {
    // File selection is UI state only. Validation and all operation progress
    // come from the Python backend (or the explicit browser simulator).
    this.transition('readyToFlash', {
      selectedFilePath: filePath,
      currentPhaseText: 'Firmware selected; backend validation pending.',
    });
  }

  selectRegion(region: string): void {
    this.transition(this.state, { selectedRegion: region });
  }

  abort(): void {
    this.transition('recoveryRequired', { errorMessage: 'Emergency Abort Triggered. ECU Reset Required.', currentPhaseText: 'Safety Recovery Required' });
  }

  reset(): void {
    this.transition('idle', {
      adapterId: null,
      ecuName: null,
      selectedFilePath: null,
      progressPercent: 0,
      errorMessage: null,
      currentPhaseText: 'Idle',
    });
  }
}

export const globalOperationMachine = new OperationMachine();
