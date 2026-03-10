import {
  Component,
  Input,
  OnChanges,
  SimpleChanges,
  signal,
  inject,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTabsModule } from '@angular/material/tabs';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ConversationService, MemoryContextResponse } from '../../../core/services/conversation.service';
import { MemoryFact, MemoryEpisode } from '../../../core/models';

@Component({
  selector: 'app-memory-panel',
  standalone: true,
  imports: [
    CommonModule,
    MatTabsModule,
    MatIconModule,
    MatChipsModule,
    MatTooltipModule,
    MatProgressSpinnerModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="memory-panel">
      <div class="memory-header">
        <mat-icon>psychology</mat-icon>
        <span>Memoria</span>
        @if (factsCount() > 0) {
          <span class="memory-badge">{{ factsCount() }} hechos</span>
        }
      </div>

      @if (loading()) {
        <div class="memory-loading">
          <mat-spinner diameter="24"></mat-spinner>
        </div>
      } @else {
        <mat-tab-group class="memory-tabs" animationDuration="0ms">
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon>lightbulb</mat-icon>
              <span>Hechos ({{ facts().length }})</span>
            </ng-template>
            <div class="tab-content">
              @if (facts().length === 0) {
                <div class="empty-tab">
                  <mat-icon>lightbulb_outline</mat-icon>
                  <span>Brain aún no ha aprendido hechos sobre ti.</span>
                  <span class="hint">Los hechos se extraen automáticamente de las conversaciones.</span>
                </div>
              } @else {
                @for (fact of facts(); track fact.id) {
                  <div class="fact-item">
                    <mat-icon class="fact-type-icon" [matTooltip]="fact.type">
                      {{ getFactIcon(fact.type) }}
                    </mat-icon>
                    <div class="fact-content">
                      <span class="fact-text">{{ fact.content }}</span>
                      <span class="fact-meta">
                        <mat-chip class="fact-chip">{{ fact.type }}</mat-chip>
                        {{ formatDate(fact.created_at) }}
                      </span>
                    </div>
                  </div>
                }
              }
            </div>
          </mat-tab>

          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon>history</mat-icon>
              <span>Episodios ({{ episodes().length }})</span>
            </ng-template>
            <div class="tab-content">
              @if (episodes().length === 0) {
                <div class="empty-tab">
                  <mat-icon>history_toggle_off</mat-icon>
                  <span>Sin resúmenes episódicos aún.</span>
                  <span class="hint">Los episodios se generan automáticamente al completar conversaciones.</span>
                </div>
              } @else {
                @for (episode of episodes(); track episode.id) {
                  <div class="episode-item">
                    <div class="episode-summary">{{ episode.summary }}</div>
                    @if (episode.key_points.length > 0) {
                      <div class="episode-points">
                        @for (point of episode.key_points; track $index) {
                          <span class="episode-point">{{ point }}</span>
                        }
                      </div>
                    }
                    <div class="episode-meta">
                      <span>{{ episode.message_count }} mensajes</span>
                      <span>{{ formatDate(episode.created_at) }}</span>
                    </div>
                  </div>
                }
              }
            </div>
          </mat-tab>
        </mat-tab-group>
      }
    </div>
  `,
  styles: [`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
    }

    .memory-panel {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: white;
    }

    .memory-header {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 14px 16px;
      font-size: 14px;
      font-weight: 600;
      color: #1e293b;
      border-bottom: 1px solid #e2e8f0;
    }

    .memory-header mat-icon {
      font-size: 20px;
      width: 20px;
      height: 20px;
      color: #667eea;
    }

    .memory-badge {
      margin-left: auto;
      font-size: 11px;
      font-weight: 500;
      padding: 2px 8px;
      border-radius: 10px;
      background: rgba(102, 126, 234, 0.1);
      color: #667eea;
    }

    .memory-loading {
      display: flex;
      justify-content: center;
      padding: 40px;
    }

    .memory-tabs {
      flex: 1;
      overflow: hidden;
    }

    :host ::ng-deep .memory-tabs .mat-mdc-tab-labels {
      padding: 0 8px;
    }

    :host ::ng-deep .memory-tabs .mat-mdc-tab {
      min-width: 0;
      padding: 0 12px;
      height: 40px;
    }

    :host ::ng-deep .memory-tabs .mdc-tab__text-label {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
    }

    :host ::ng-deep .memory-tabs .mdc-tab__text-label mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
    }

    .tab-content {
      padding: 8px;
      overflow-y: auto;
      max-height: calc(100vh - 180px);
    }

    .empty-tab {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      padding: 32px 16px;
      text-align: center;
      color: #94a3b8;
      font-size: 13px;
    }

    .empty-tab mat-icon {
      font-size: 32px;
      width: 32px;
      height: 32px;
      color: #cbd5e1;
    }

    .hint {
      font-size: 11px;
      color: #b0bec5;
    }

    /* Facts */
    .fact-item {
      display: flex;
      gap: 10px;
      padding: 10px;
      border-radius: 8px;
      transition: background 0.15s ease;
    }

    .fact-item:hover {
      background: #f8fafc;
    }

    .fact-type-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
      color: #667eea;
      flex-shrink: 0;
      margin-top: 2px;
    }

    .fact-content {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .fact-text {
      font-size: 13px;
      color: #334155;
      line-height: 1.4;
    }

    .fact-meta {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      color: #94a3b8;
    }

    .fact-chip {
      height: 18px !important;
      font-size: 10px !important;
      padding: 0 6px !important;
      min-height: unset !important;
    }

    /* Episodes */
    .episode-item {
      padding: 10px;
      border-radius: 8px;
      border: 1px solid #e2e8f0;
      margin-bottom: 8px;
    }

    .episode-item:hover {
      background: #f8fafc;
    }

    .episode-summary {
      font-size: 13px;
      color: #334155;
      line-height: 1.4;
      margin-bottom: 6px;
    }

    .episode-points {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      margin-bottom: 6px;
    }

    .episode-point {
      font-size: 11px;
      padding: 2px 6px;
      border-radius: 4px;
      background: #f1f5f9;
      color: #64748b;
    }

    .episode-meta {
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      color: #94a3b8;
    }
  `],
})
export class MemoryPanelComponent implements OnChanges {
  @Input() userId: string | null = null;
  @Input() agentId: string | null = null;

  private convService = inject(ConversationService);

  facts = signal<MemoryFact[]>([]);
  episodes = signal<MemoryEpisode[]>([]);
  factsCount = signal(0);
  loading = signal(false);

  ngOnChanges(changes: SimpleChanges) {
    if (changes['userId'] || changes['agentId']) {
      this.loadMemory();
    }
  }

  loadMemory() {
    if (!this.userId) return;
    this.loading.set(true);
    this.convService.getMemoryContext(this.userId, this.agentId || undefined).subscribe({
      next: (res) => {
        this.facts.set(res.facts as any[]);
        this.episodes.set(res.episodes as any[]);
        this.factsCount.set(res.facts_count ?? res.facts.length);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  getFactIcon(type: string): string {
    switch (type) {
      case 'preference': return 'favorite';
      case 'correction': return 'edit';
      case 'knowledge': return 'school';
      default: return 'lightbulb';
    }
  }

  formatDate(dateStr: string): string {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString('es-ES', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  }
}
