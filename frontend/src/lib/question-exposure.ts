export class QuestionExposure {
  private totals = new Map<number, number>();
  private current: number | null = null;
  private since: number | null = null;
  private visible = false;
  private stopped = false;

  constructor(private readonly now: () => number, previous: Record<number, number> = {}) {
    this.totals = new Map(Object.entries(previous).map(([id, value]) => [Number(id), value]));
  }

  private close() {
    if (this.current !== null && this.since !== null) {
      this.totals.set(this.current, (this.totals.get(this.current) ?? 0) + Math.max(0, this.now() - this.since));
      this.since = null;
    }
  }

  show(questionId: number, visible: boolean) {
    if (this.stopped) return;
    if (this.current === questionId && this.visible === visible) return;
    this.close();
    this.current = questionId;
    this.visible = visible;
    if (visible) this.since = this.now();
  }

  setVisible(visible: boolean) {
    if (this.stopped || this.visible === visible) return;
    this.close();
    this.visible = visible;
    if (visible && this.current !== null) this.since = this.now();
  }

  stop() {
    if (this.stopped) return;
    this.close();
    this.stopped = true;
  }

  resume(visible: boolean) {
    if (!this.stopped) return;
    this.stopped = false;
    this.visible = visible;
    if (visible && this.current !== null) this.since = this.now();
  }

  milliseconds(questionId: number) {
    const live = this.current === questionId && this.since !== null ? Math.max(0, this.now() - this.since) : 0;
    return Math.min(2147483647, Math.floor((this.totals.get(questionId) ?? 0) + live));
  }
}
