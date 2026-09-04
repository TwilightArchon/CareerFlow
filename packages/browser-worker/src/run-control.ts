export type BrowserRunControl = 'pause' | 'resume' | 'cancel';

export class RunControlGate {
  private readonly pausedRuns = new Set<string>();
  private readonly cancelledRuns = new Set<string>();

  apply(runId: string, control: BrowserRunControl): void {
    if (control === 'pause') {
      if (!this.cancelledRuns.has(runId)) this.pausedRuns.add(runId);
      return;
    }
    if (control === 'resume') {
      if (this.cancelledRuns.has(runId)) {
        throw new Error('A cancelled run cannot be resumed');
      }
      this.pausedRuns.delete(runId);
      return;
    }
    this.pausedRuns.delete(runId);
    this.cancelledRuns.add(runId);
  }

  assertActionAllowed(runId: string): void {
    if (this.cancelledRuns.has(runId)) {
      throw new Error('This run was cancelled; browser actions are blocked');
    }
    if (this.pausedRuns.has(runId)) {
      throw new Error('This run is paused; browser actions are blocked');
    }
  }
}
