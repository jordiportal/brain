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
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatTabsModule } from '@angular/material/tabs';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ConversationService, MemoryContextResponse } from '../../../core/services/conversation.service';
import { MemoryFact, MemoryEpisode } from '../../../core/models';
import { environment } from '../../../../environments/environment';

@Component({
  selector: 'app-memory-panel',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatTabsModule,
    MatIconModule,
    MatChipsModule,
    MatTooltipModule,
    MatProgressSpinnerModule,
    MatButtonModule,
    MatInputModule,
    MatFormFieldModule,
    MatSelectModule,
    MatSnackBarModule,
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
              <div class="tab-actions">
                <button mat-stroked-button (click)="startAddFact()">
                  <mat-icon>add</mat-icon> Añadir hecho
                </button>
              </div>

              @if (addingFact()) {
                <div class="edit-card">
                  <mat-form-field appearance="outline" class="full-width">
                    <mat-label>Contenido del hecho</mat-label>
                    <input matInput [(ngModel)]="newFactContent" placeholder="Ej: Prefiere respuestas en español">
                  </mat-form-field>
                  <div class="edit-row">
                    <mat-form-field appearance="outline">
                      <mat-label>Tipo</mat-label>
                      <mat-select [(ngModel)]="newFactType">
                        <mat-option value="fact">Hecho</mat-option>
                        <mat-option value="preference">Preferencia</mat-option>
                        <mat-option value="knowledge">Conocimiento</mat-option>
                        <mat-option value="correction">Corrección</mat-option>
                      </mat-select>
                    </mat-form-field>
                    <div class="edit-actions">
                      <button mat-button (click)="cancelAddFact()">Cancelar</button>
                      <button mat-raised-button color="primary"
                              [disabled]="!newFactContent.trim() || saving()"
                              (click)="saveFact()">
                        @if (saving()) { <mat-spinner diameter="16"></mat-spinner> }
                        Guardar
                      </button>
                    </div>
                  </div>
                </div>
              }

              @if (facts().length === 0 && !addingFact()) {
                <div class="empty-tab">
                  <mat-icon>lightbulb_outline</mat-icon>
                  <span>Brain aún no ha aprendido hechos sobre ti.</span>
                  <span class="hint">Los hechos se extraen automáticamente de las conversaciones, o puedes añadirlos manualmente.</span>
                </div>
              } @else {
                @for (fact of facts(); track fact.id) {
                  <div class="fact-item" [class.editing]="editingFactId() === fact.id">
                    @if (editingFactId() === fact.id) {
                      <div class="edit-inline">
                        <mat-form-field appearance="outline" class="full-width">
                          <input matInput [(ngModel)]="editFactContent">
                        </mat-form-field>
                        <div class="edit-row">
                          <mat-form-field appearance="outline">
                            <mat-select [(ngModel)]="editFactType">
                              <mat-option value="fact">Hecho</mat-option>
                              <mat-option value="preference">Preferencia</mat-option>
                              <mat-option value="knowledge">Conocimiento</mat-option>
                              <mat-option value="correction">Corrección</mat-option>
                            </mat-select>
                          </mat-form-field>
                          <div class="edit-actions">
                            <button mat-button (click)="cancelEditFact()">Cancelar</button>
                            <button mat-raised-button color="primary"
                                    [disabled]="!editFactContent.trim() || saving()"
                                    (click)="updateFact(fact.id)">
                              @if (saving()) { <mat-spinner diameter="16"></mat-spinner> }
                              Guardar
                            </button>
                          </div>
                        </div>
                      </div>
                    } @else {
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
                      <div class="item-actions">
                        <button mat-icon-button matTooltip="Editar" (click)="startEditFact(fact)">
                          <mat-icon>edit</mat-icon>
                        </button>
                        <button mat-icon-button matTooltip="Eliminar" (click)="deleteFact(fact.id)">
                          <mat-icon>delete</mat-icon>
                        </button>
                      </div>
                    }
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
                  <span class="hint">Los episodios se generan automáticamente al completar conversaciones largas.</span>
                </div>
              } @else {
                @for (episode of episodes(); track episode.id) {
                  <div class="episode-item" [class.editing]="editingEpisodeId() === episode.id">
                    @if (editingEpisodeId() === episode.id) {
                      <div class="edit-inline">
                        <mat-form-field appearance="outline" class="full-width">
                          <mat-label>Resumen</mat-label>
                          <textarea matInput [(ngModel)]="editEpisodeSummary" rows="3"></textarea>
                        </mat-form-field>
                        <div class="edit-actions">
                          <button mat-button (click)="cancelEditEpisode()">Cancelar</button>
                          <button mat-raised-button color="primary"
                                  [disabled]="!editEpisodeSummary.trim() || saving()"
                                  (click)="updateEpisode(episode.id)">
                            @if (saving()) { <mat-spinner diameter="16"></mat-spinner> }
                            Guardar
                          </button>
                        </div>
                      </div>
                    } @else {
                      <div class="episode-main">
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
                      <div class="item-actions">
                        <button mat-icon-button matTooltip="Editar" (click)="startEditEpisode(episode)">
                          <mat-icon>edit</mat-icon>
                        </button>
                        <button mat-icon-button matTooltip="Eliminar" (click)="deleteEpisode(episode.id)">
                          <mat-icon>delete</mat-icon>
                        </button>
                      </div>
                    }
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
    :host { display: flex; flex-direction: column; height: 100%; }
    .memory-panel { display: flex; flex-direction: column; height: 100%; background: white; }

    .memory-header { display: flex; align-items: center; gap: 8px; padding: 14px 16px; font-size: 14px; font-weight: 600; color: #1e293b; border-bottom: 1px solid #e2e8f0; }
    .memory-header mat-icon { font-size: 20px; width: 20px; height: 20px; color: #667eea; }
    .memory-badge { margin-left: auto; font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: 10px; background: rgba(102, 126, 234, 0.1); color: #667eea; }

    .memory-loading { display: flex; justify-content: center; padding: 40px; }
    .memory-tabs { flex: 1; overflow: hidden; }

    :host ::ng-deep .memory-tabs .mat-mdc-tab-labels { padding: 0 8px; }
    :host ::ng-deep .memory-tabs .mat-mdc-tab { min-width: 0; padding: 0 12px; height: 40px; }
    :host ::ng-deep .memory-tabs .mdc-tab__text-label { display: flex; align-items: center; gap: 4px; font-size: 12px; }
    :host ::ng-deep .memory-tabs .mdc-tab__text-label mat-icon { font-size: 16px; width: 16px; height: 16px; }

    .tab-content { padding: 8px; overflow-y: auto; max-height: calc(100vh - 180px); }

    .tab-actions { display: flex; justify-content: flex-end; margin-bottom: 8px; }
    .tab-actions button { font-size: 12px; height: 32px; }
    .tab-actions button mat-icon { font-size: 16px; width: 16px; height: 16px; margin-right: 4px; }

    .empty-tab { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 32px 16px; text-align: center; color: #94a3b8; font-size: 13px; }
    .empty-tab mat-icon { font-size: 32px; width: 32px; height: 32px; color: #cbd5e1; }
    .hint { font-size: 11px; color: #b0bec5; }

    /* Edit card (new fact) */
    .edit-card { padding: 12px; margin-bottom: 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; }
    .edit-inline { width: 100%; }
    .edit-row { display: flex; align-items: center; gap: 8px; }
    .edit-row mat-form-field { min-width: 140px; }
    .edit-actions { display: flex; gap: 4px; margin-left: auto; }
    .full-width { width: 100%; }

    /* Facts */
    .fact-item { display: flex; gap: 10px; padding: 10px; border-radius: 8px; transition: background 0.15s ease; align-items: flex-start; }
    .fact-item:hover { background: #f8fafc; }
    .fact-item.editing { background: #f1f5f9; padding: 12px; }
    .fact-item:hover .item-actions { opacity: 1; }

    .fact-type-icon { font-size: 18px; width: 18px; height: 18px; color: #667eea; flex-shrink: 0; margin-top: 2px; }
    .fact-content { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
    .fact-text { font-size: 13px; color: #334155; line-height: 1.4; }
    .fact-meta { display: flex; align-items: center; gap: 6px; font-size: 11px; color: #94a3b8; }
    .fact-chip { height: 18px !important; font-size: 10px !important; padding: 0 6px !important; min-height: unset !important; }

    /* Item actions (edit/delete buttons) */
    .item-actions { display: flex; gap: 0; opacity: 0; transition: opacity 0.15s; flex-shrink: 0; }
    .item-actions button { width: 28px; height: 28px; }
    .item-actions mat-icon { font-size: 16px; width: 16px; height: 16px; color: #94a3b8; }
    .item-actions button:hover mat-icon { color: #667eea; }
    .item-actions button:last-child:hover mat-icon { color: #ef4444; }

    /* Episodes */
    .episode-item { display: flex; gap: 10px; padding: 10px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 8px; align-items: flex-start; }
    .episode-item:hover { background: #f8fafc; }
    .episode-item:hover .item-actions { opacity: 1; }
    .episode-item.editing { background: #f1f5f9; padding: 12px; }
    .episode-main { flex: 1; min-width: 0; }

    .episode-summary { font-size: 13px; color: #334155; line-height: 1.4; margin-bottom: 6px; }
    .episode-points { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 6px; }
    .episode-point { font-size: 11px; padding: 2px 6px; border-radius: 4px; background: #f1f5f9; color: #64748b; }
    .episode-meta { display: flex; justify-content: space-between; font-size: 11px; color: #94a3b8; }
  `],
})
export class MemoryPanelComponent implements OnChanges {
  @Input() userId: string | null = null;
  @Input() agentId: string | null = null;

  private convService = inject(ConversationService);
  private http = inject(HttpClient);
  private snackBar = inject(MatSnackBar);

  facts = signal<MemoryFact[]>([]);
  episodes = signal<MemoryEpisode[]>([]);
  factsCount = signal(0);
  loading = signal(false);
  saving = signal(false);

  // Add fact state
  addingFact = signal(false);
  newFactContent = '';
  newFactType = 'fact';

  // Edit fact state
  editingFactId = signal<number | null>(null);
  editFactContent = '';
  editFactType = 'fact';

  // Edit episode state
  editingEpisodeId = signal<number | null>(null);
  editEpisodeSummary = '';

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

  // ---- Add fact ----

  startAddFact() {
    this.addingFact.set(true);
    this.newFactContent = '';
    this.newFactType = 'fact';
  }

  cancelAddFact() {
    this.addingFact.set(false);
  }

  saveFact() {
    if (!this.newFactContent.trim()) return;
    this.saving.set(true);
    this.http.post(`${environment.apiUrl}/memory/facts`, {
      content: this.newFactContent.trim(),
      type: this.newFactType,
      user_id: this.userId,
      agent_id: this.agentId,
    }).subscribe({
      next: () => {
        this.saving.set(false);
        this.addingFact.set(false);
        this.snackBar.open('Hecho añadido', 'Cerrar', { duration: 2000 });
        this.loadMemory();
      },
      error: () => {
        this.saving.set(false);
        this.snackBar.open('Error al añadir hecho', 'Cerrar', { duration: 3000 });
      },
    });
  }

  // ---- Edit fact ----

  startEditFact(fact: any) {
    this.editingFactId.set(fact.id);
    this.editFactContent = fact.content;
    this.editFactType = fact.type;
  }

  cancelEditFact() {
    this.editingFactId.set(null);
  }

  updateFact(factId: number) {
    if (!this.editFactContent.trim()) return;
    this.saving.set(true);
    this.http.put(`${environment.apiUrl}/memory/facts/${factId}`, {
      content: this.editFactContent.trim(),
      type: this.editFactType,
    }).subscribe({
      next: () => {
        this.saving.set(false);
        this.editingFactId.set(null);
        this.snackBar.open('Hecho actualizado', 'Cerrar', { duration: 2000 });
        this.loadMemory();
      },
      error: () => {
        this.saving.set(false);
        this.snackBar.open('Error al actualizar', 'Cerrar', { duration: 3000 });
      },
    });
  }

  // ---- Delete fact ----

  deleteFact(factId: number) {
    if (!confirm('¿Eliminar este hecho?')) return;
    this.http.delete(`${environment.apiUrl}/memory/facts/${factId}`).subscribe({
      next: () => {
        this.snackBar.open('Hecho eliminado', 'Cerrar', { duration: 2000 });
        this.loadMemory();
      },
      error: () => this.snackBar.open('Error al eliminar', 'Cerrar', { duration: 3000 }),
    });
  }

  // ---- Edit episode ----

  startEditEpisode(episode: any) {
    this.editingEpisodeId.set(episode.id);
    this.editEpisodeSummary = episode.summary;
  }

  cancelEditEpisode() {
    this.editingEpisodeId.set(null);
  }

  updateEpisode(episodeId: number) {
    if (!this.editEpisodeSummary.trim()) return;
    this.saving.set(true);
    this.http.put(`${environment.apiUrl}/memory/episodes/${episodeId}`, {
      summary: this.editEpisodeSummary.trim(),
    }).subscribe({
      next: () => {
        this.saving.set(false);
        this.editingEpisodeId.set(null);
        this.snackBar.open('Episodio actualizado', 'Cerrar', { duration: 2000 });
        this.loadMemory();
      },
      error: () => {
        this.saving.set(false);
        this.snackBar.open('Error al actualizar', 'Cerrar', { duration: 3000 });
      },
    });
  }

  // ---- Delete episode ----

  deleteEpisode(episodeId: number) {
    if (!confirm('¿Eliminar este episodio?')) return;
    this.http.delete(`${environment.apiUrl}/memory/episodes/${episodeId}`).subscribe({
      next: () => {
        this.snackBar.open('Episodio eliminado', 'Cerrar', { duration: 2000 });
        this.loadMemory();
      },
      error: () => this.snackBar.open('Error al eliminar', 'Cerrar', { duration: 3000 }),
    });
  }

  // ---- Helpers ----

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
