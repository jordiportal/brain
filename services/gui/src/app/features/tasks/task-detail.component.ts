import { Component, Input, Output, EventEmitter, OnInit, signal, inject } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TaskService } from '../../core/services/task.service';
import { EngineTask, TaskEvent, EngineTaskState } from '../../core/models';

@Component({
  selector: 'app-task-detail',
  standalone: true,
  imports: [
    CommonModule, FormsModule, DatePipe,
    MatButtonModule, MatIconModule, MatChipsModule, MatDividerModule,
    MatExpansionModule, MatInputModule, MatFormFieldModule,
    MatTooltipModule, MatProgressSpinnerModule,
  ],
  template: `
    <div class="task-detail">
      <div class="detail-header">
        <h3>Task Detail</h3>
        <button mat-icon-button (click)="close.emit()">
          <mat-icon>close</mat-icon>
        </button>
      </div>

      <!-- State badge and ID -->
      <div class="detail-summary">
        <span class="state-badge" [class]="task.state">{{ task.state }}</span>
        <code class="task-id">{{ task.id }}</code>
      </div>

      @if (task.state_reason) {
        <p class="state-reason">{{ task.state_reason }}</p>
      }

      <!-- Metrics -->
      <div class="metrics-row">
        <div class="metric">
          <span class="metric-label">Duración</span>
          <span class="metric-value">{{ task.duration_ms | number:'1.0-0' }}ms</span>
        </div>
        <div class="metric">
          <span class="metric-label">Tokens</span>
          <span class="metric-value">{{ task.tokens_used | number }}</span>
        </div>
        <div class="metric">
          <span class="metric-label">Iteraciones</span>
          <span class="metric-value">{{ task.iterations }}</span>
        </div>
        <div class="metric">
          <span class="metric-label">Coste</span>
          <span class="metric-value">\${{ task.cost_usd | number:'1.4-4' }}</span>
        </div>
      </div>

      <mat-divider></mat-divider>

      <!-- State Timeline -->
      <div class="section">
        <h4>Timeline</h4>
        @if (loadingEvents()) {
          <mat-progress-spinner mode="indeterminate" diameter="24"></mat-progress-spinner>
        }
        <div class="timeline">
          @for (event of events(); track event.id) {
            <div class="timeline-item">
              <div class="timeline-dot" [class]="event.state"></div>
              <div class="timeline-content">
                <span class="timeline-state">{{ event.state }}</span>
                @if (event.reason) {
                  <span class="timeline-reason">{{ event.reason }}</span>
                }
                <span class="timeline-time">{{ event.created_at | date:'medium' }}</span>
              </div>
            </div>
          }
        </div>
      </div>

      <mat-divider></mat-divider>

      <!-- Input -->
      <div class="section">
        <h4>Input</h4>
        <div class="message-box user">
          @for (part of task.input?.parts || []; track $index) {
            @if (part.type === 'text') {
              <p>{{ part.text }}</p>
            } @else {
              <span class="part-badge">{{ part.type }}: {{ part.filename || part.url || 'data' }}</span>
            }
          }
        </div>
      </div>

      <!-- Output -->
      @if (task.output) {
        <div class="section">
          <h4>Output</h4>
          <div class="message-box agent">
            @for (part of task.output.parts; track $index) {
              @if (part.type === 'text') {
                <p>{{ part.text }}</p>
              } @else {
                <span class="part-badge">{{ part.type }}: {{ part.filename || part.url || 'data' }}</span>
              }
            }
          </div>
        </div>
      }

      <!-- History -->
      @if (task.history?.length) {
        <mat-expansion-panel>
          <mat-expansion-panel-header>
            <mat-panel-title>History ({{ task.history.length }} messages)</mat-panel-title>
          </mat-expansion-panel-header>
          @for (msg of task.history; track msg.id) {
            <div class="message-box" [class]="msg.role">
              <div class="msg-header">
                <span class="msg-role">{{ msg.role }}</span>
                @if (msg.agent_id) {
                  <span class="msg-agent">{{ msg.agent_id }}</span>
                }
                <span class="msg-time">{{ msg.created_at | date:'shortTime' }}</span>
              </div>
              @for (part of msg.parts; track $index) {
                @if (part.type === 'text') {
                  <p class="msg-text">{{ part.text }}</p>
                }
              }
            </div>
          }
        </mat-expansion-panel>
      }

      <!-- Artifacts -->
      @if (task.artifacts?.length) {
        <mat-expansion-panel>
          <mat-expansion-panel-header>
            <mat-panel-title>Artifacts ({{ task.artifacts.length }})</mat-panel-title>
          </mat-expansion-panel-header>
          @for (art of task.artifacts; track art.id) {
            <div class="artifact-card">
              <mat-icon>attachment</mat-icon>
              <div>
                <strong>{{ art.name }}</strong>
                @if (art.description) {
                  <p>{{ art.description }}</p>
                }
              </div>
            </div>
          }
        </mat-expansion-panel>
      }

      <!-- Child Tasks -->
      @if (childTasks().length) {
        <mat-expansion-panel>
          <mat-expansion-panel-header>
            <mat-panel-title>Delegations ({{ childTasks().length }})</mat-panel-title>
          </mat-expansion-panel-header>
          @for (child of childTasks(); track child.id) {
            <div class="child-task">
              <span class="state-badge small" [class]="child.state">{{ child.state }}</span>
              <span class="child-agent">{{ child.agent_id || 'N/A' }}</span>
              <span class="child-preview">{{ getInputPreview(child) }}</span>
            </div>
          }
        </mat-expansion-panel>
      }

      <mat-divider></mat-divider>

      <!-- Actions -->
      <div class="actions">
        @if (task.state === 'working' || task.state === 'submitted') {
          <button mat-raised-button color="warn" (click)="cancelTask()">
            <mat-icon>cancel</mat-icon> Cancelar
          </button>
        }
        @if (task.state === 'input_required') {
          <mat-form-field appearance="outline" class="resume-input">
            <mat-label>Tu respuesta</mat-label>
            <input matInput [(ngModel)]="resumeMessage" placeholder="Escribe tu respuesta...">
          </mat-form-field>
          <button mat-raised-button color="primary" (click)="resumeTask()" [disabled]="!resumeMessage">
            <mat-icon>play_arrow</mat-icon> Responder
          </button>
        }
        @if (task.state === 'failed') {
          <button mat-raised-button color="primary" (click)="retryTask()">
            <mat-icon>replay</mat-icon> Reintentar
          </button>
        }
      </div>

      <!-- Metadata -->
      <div class="section metadata-section">
        <h4>Metadata</h4>
        <div class="meta-grid">
          <span class="meta-key">Context ID</span>
          <code>{{ task.context_id }}</code>
          @if (task.chain_id) {
            <span class="meta-key">Chain</span>
            <code>{{ task.chain_id }}</code>
          }
          @if (task.agent_id) {
            <span class="meta-key">Agent</span>
            <code>{{ task.agent_id }}</code>
          }
          @if (task.created_by) {
            <span class="meta-key">Created By</span>
            <code>{{ task.created_by }}</code>
          }
          <span class="meta-key">Created</span>
          <span>{{ task.created_at | date:'medium' }}</span>
          <span class="meta-key">Updated</span>
          <span>{{ task.updated_at | date:'medium' }}</span>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .task-detail { padding: 24px; }
    .detail-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }
    .detail-header h3 { margin: 0; font-size: 20px; }
    .detail-summary {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 8px;
    }
    .state-badge {
      font-size: 12px; font-weight: 700; text-transform: uppercase;
      padding: 4px 10px; border-radius: 4px; color: white;
    }
    .state-badge.small { font-size: 10px; padding: 2px 6px; }
    .state-badge.submitted { background: #90caf9; color: #1a237e; }
    .state-badge.working { background: #42a5f5; }
    .state-badge.input_required { background: #ffb74d; color: #4e342e; }
    .state-badge.completed { background: #66bb6a; }
    .state-badge.failed { background: #ef5350; }
    .state-badge.canceled { background: #9e9e9e; }
    .task-id { font-size: 12px; color: #888; }
    .state-reason { font-size: 13px; color: #666; margin: 4px 0 16px; }
    .metrics-row {
      display: flex; gap: 24px; padding: 16px 0; flex-wrap: wrap;
    }
    .metric { display: flex; flex-direction: column; }
    .metric-label { font-size: 11px; color: #999; text-transform: uppercase; }
    .metric-value { font-size: 18px; font-weight: 600; }
    .section { padding: 16px 0; }
    .section h4 { margin: 0 0 12px; font-size: 14px; font-weight: 600; color: #555; }
    .timeline { padding-left: 16px; border-left: 2px solid #e0e0e0; }
    .timeline-item { display: flex; gap: 12px; margin-bottom: 16px; position: relative; }
    .timeline-dot {
      width: 12px; height: 12px; border-radius: 50%;
      background: #ccc; flex-shrink: 0; margin-top: 4px; position: relative; left: -23px;
    }
    .timeline-dot.submitted { background: #90caf9; }
    .timeline-dot.working { background: #42a5f5; }
    .timeline-dot.input_required { background: #ffb74d; }
    .timeline-dot.completed { background: #66bb6a; }
    .timeline-dot.failed { background: #ef5350; }
    .timeline-dot.canceled { background: #9e9e9e; }
    .timeline-content { margin-left: -12px; display: flex; flex-direction: column; gap: 2px; }
    .timeline-state { font-weight: 600; font-size: 13px; text-transform: uppercase; }
    .timeline-reason { font-size: 12px; color: #666; }
    .timeline-time { font-size: 11px; color: #aaa; }
    .message-box {
      background: #f5f5f5; border-radius: 8px; padding: 12px; margin-bottom: 8px;
    }
    .message-box.user { border-left: 3px solid #42a5f5; }
    .message-box.agent { border-left: 3px solid #66bb6a; }
    .message-box.system { border-left: 3px solid #ffb74d; }
    .message-box.tool { border-left: 3px solid #ab47bc; }
    .message-box p { margin: 0; font-size: 14px; line-height: 1.6; white-space: pre-wrap; }
    .msg-header { display: flex; gap: 8px; margin-bottom: 6px; align-items: center; }
    .msg-role { font-size: 11px; font-weight: 700; text-transform: uppercase; color: #555; }
    .msg-agent { font-size: 11px; color: #888; }
    .msg-time { font-size: 10px; color: #aaa; margin-left: auto; }
    .msg-text { margin: 0; font-size: 13px; line-height: 1.5; }
    .part-badge {
      font-size: 11px; background: #e0e0e0; padding: 2px 8px; border-radius: 4px;
    }
    .artifact-card {
      display: flex; gap: 12px; padding: 8px 0; align-items: start;
    }
    .artifact-card mat-icon { color: #888; }
    .child-task {
      display: flex; gap: 8px; align-items: center; padding: 6px 0;
    }
    .child-agent { font-size: 12px; font-weight: 600; }
    .child-preview { font-size: 12px; color: #666; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .actions {
      display: flex; gap: 12px; align-items: center; padding: 16px 0; flex-wrap: wrap;
    }
    .resume-input { flex: 1; min-width: 200px; }
    .metadata-section { opacity: 0.8; }
    .meta-grid {
      display: grid; grid-template-columns: 100px 1fr; gap: 4px 12px; font-size: 12px;
    }
    .meta-key { color: #999; text-transform: uppercase; font-size: 10px; }
    .meta-grid code { font-size: 11px; word-break: break-all; }
  `]
})
export class TaskDetailComponent implements OnInit {
  @Input({ required: true }) task!: EngineTask;
  @Output() close = new EventEmitter<void>();
  @Output() taskCanceled = new EventEmitter<EngineTask>();
  @Output() taskResumed = new EventEmitter<EngineTask>();

  private taskService = inject(TaskService);

  events = signal<TaskEvent[]>([]);
  childTasks = signal<EngineTask[]>([]);
  loadingEvents = signal(false);
  resumeMessage = '';

  ngOnInit() {
    this.loadEvents();
    this.loadChildren();
  }

  loadEvents() {
    this.loadingEvents.set(true);
    this.taskService.getTaskEvents(this.task.id).subscribe({
      next: res => {
        this.events.set(res.events);
        this.loadingEvents.set(false);
      },
      error: () => this.loadingEvents.set(false),
    });
  }

  loadChildren() {
    this.taskService.getChildTasks(this.task.id).subscribe({
      next: children => this.childTasks.set(children),
      error: () => {},
    });
  }

  cancelTask() {
    this.taskService.cancelTask(this.task.id).subscribe({
      next: updated => this.taskCanceled.emit(updated),
    });
  }

  resumeTask() {
    if (!this.resumeMessage) return;
    this.taskService.resumeTask(this.task.id, this.resumeMessage).subscribe({
      next: updated => {
        this.taskResumed.emit(updated);
        this.resumeMessage = '';
      },
    });
  }

  retryTask() {
    this.taskService.resumeTask(this.task.id, 'retry').subscribe({
      next: updated => this.taskResumed.emit(updated),
    });
  }

  getInputPreview(task: EngineTask): string {
    const textPart = task.input?.parts?.find(p => p.type === 'text');
    return textPart?.text?.substring(0, 80) || '...';
  }
}
