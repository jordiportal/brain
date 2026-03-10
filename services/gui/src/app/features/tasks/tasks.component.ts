import { Component, OnInit, OnDestroy, signal, computed, inject } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatCardModule } from '@angular/material/card';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { TaskService, TaskListParams } from '../../core/services/task.service';
import { EngineTask, EngineTaskState } from '../../core/models';
import { TaskDetailComponent } from './task-detail.component';

@Component({
  selector: 'app-tasks',
  standalone: true,
  imports: [
    CommonModule, FormsModule, DatePipe,
    MatTableModule, MatButtonModule, MatIconModule, MatChipsModule,
    MatSelectModule, MatFormFieldModule, MatPaginatorModule,
    MatProgressSpinnerModule, MatTooltipModule, MatCardModule,
    MatDialogModule, TaskDetailComponent,
  ],
  template: `
    <div class="tasks-container">
      <div class="tasks-header">
        <h2>Tasks Monitor</h2>
        <div class="tasks-filters">
          <mat-form-field appearance="outline" class="filter-field">
            <mat-label>Estado</mat-label>
            <mat-select [(ngModel)]="stateFilter" (selectionChange)="loadTasks()">
              <mat-option [value]="''">Todos</mat-option>
              <mat-option value="submitted">Submitted</mat-option>
              <mat-option value="working">Working</mat-option>
              <mat-option value="input_required">Input Required</mat-option>
              <mat-option value="completed">Completed</mat-option>
              <mat-option value="failed">Failed</mat-option>
              <mat-option value="canceled">Canceled</mat-option>
            </mat-select>
          </mat-form-field>
          <button mat-icon-button (click)="loadTasks()" matTooltip="Refrescar">
            <mat-icon>refresh</mat-icon>
          </button>
        </div>
      </div>

      @if (loading()) {
        <div class="loading-spinner">
          <mat-progress-spinner mode="indeterminate" diameter="40"></mat-progress-spinner>
        </div>
      }

      @if (!loading() && tasks().length === 0) {
        <div class="empty-state">
          <mat-icon>task_alt</mat-icon>
          <p>No hay tareas que mostrar</p>
        </div>
      }

      @if (!loading() && tasks().length > 0) {
        <div class="tasks-grid">
          @for (task of tasks(); track task.id) {
            <mat-card class="task-card" [class]="'state-' + task.state" (click)="selectTask(task)">
              <div class="task-card-header">
                <span class="task-state-badge" [class]="task.state">{{ task.state }}</span>
                <span class="task-id" [matTooltip]="task.id">{{ task.id.substring(0, 8) }}...</span>
              </div>
              <div class="task-card-body">
                <p class="task-input">{{ getInputPreview(task) }}</p>
                @if (task.agent_id) {
                  <span class="task-agent">
                    <mat-icon>smart_toy</mat-icon>
                    {{ task.agent_id }}
                  </span>
                }
              </div>
              <div class="task-card-footer">
                <span class="task-meta">
                  <mat-icon>schedule</mat-icon>
                  {{ task.duration_ms | number:'1.0-0' }}ms
                </span>
                <span class="task-meta">
                  <mat-icon>token</mat-icon>
                  {{ task.tokens_used }}
                </span>
                <span class="task-meta">
                  <mat-icon>loop</mat-icon>
                  {{ task.iterations }}
                </span>
                <span class="task-date">{{ task.created_at | date:'short' }}</span>
              </div>
            </mat-card>
          }
        </div>

        <mat-paginator
          [length]="totalTasks()"
          [pageSize]="pageSize"
          [pageIndex]="pageIndex"
          [pageSizeOptions]="[10, 25, 50]"
          (page)="onPage($event)"
          showFirstLastButtons>
        </mat-paginator>
      }

      @if (selectedTask()) {
        <div class="task-detail-overlay" (click)="closeDetail($event)">
          <div class="task-detail-panel" (click)="$event.stopPropagation()">
            <app-task-detail
              [task]="selectedTask()!"
              (close)="selectedTask.set(null)"
              (taskCanceled)="onTaskCanceledEvent($any($event))"
              (taskResumed)="onTaskResumedEvent($any($event))">
            </app-task-detail>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .tasks-container {
      padding: 24px;
      max-width: 1400px;
      margin: 0 auto;
    }
    .tasks-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 24px;
    }
    .tasks-header h2 {
      margin: 0;
      font-size: 24px;
      font-weight: 600;
    }
    .tasks-filters {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .filter-field {
      width: 180px;
    }
    .loading-spinner {
      display: flex;
      justify-content: center;
      padding: 48px;
    }
    .empty-state {
      text-align: center;
      padding: 64px 24px;
      color: #666;
    }
    .empty-state mat-icon {
      font-size: 64px;
      width: 64px;
      height: 64px;
      color: #ccc;
    }
    .tasks-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .task-card {
      cursor: pointer;
      transition: transform 0.15s, box-shadow 0.15s;
      border-left: 4px solid #ccc;
    }
    .task-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .task-card.state-submitted { border-left-color: #90caf9; }
    .task-card.state-working { border-left-color: #42a5f5; }
    .task-card.state-input_required { border-left-color: #ffb74d; }
    .task-card.state-completed { border-left-color: #66bb6a; }
    .task-card.state-failed { border-left-color: #ef5350; }
    .task-card.state-canceled { border-left-color: #9e9e9e; }
    .task-card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px 0;
    }
    .task-state-badge {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      padding: 3px 8px;
      border-radius: 4px;
      color: white;
    }
    .task-state-badge.submitted { background: #90caf9; color: #1a237e; }
    .task-state-badge.working { background: #42a5f5; }
    .task-state-badge.input_required { background: #ffb74d; color: #4e342e; }
    .task-state-badge.completed { background: #66bb6a; }
    .task-state-badge.failed { background: #ef5350; }
    .task-state-badge.canceled { background: #9e9e9e; }
    .task-id {
      font-size: 12px;
      color: #888;
      font-family: monospace;
    }
    .task-card-body {
      padding: 12px 16px;
    }
    .task-input {
      font-size: 14px;
      line-height: 1.5;
      color: #333;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
      margin: 0 0 8px;
    }
    .task-agent {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
      color: #666;
    }
    .task-agent mat-icon {
      font-size: 14px;
      width: 14px;
      height: 14px;
    }
    .task-card-footer {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 0 16px 12px;
      flex-wrap: wrap;
    }
    .task-meta {
      display: inline-flex;
      align-items: center;
      gap: 2px;
      font-size: 11px;
      color: #888;
    }
    .task-meta mat-icon {
      font-size: 14px;
      width: 14px;
      height: 14px;
    }
    .task-date {
      margin-left: auto;
      font-size: 11px;
      color: #aaa;
    }
    .task-detail-overlay {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0,0,0,0.5);
      z-index: 1000;
      display: flex;
      justify-content: flex-end;
    }
    .task-detail-panel {
      width: 700px;
      max-width: 90vw;
      height: 100vh;
      overflow-y: auto;
      background: white;
      box-shadow: -4px 0 20px rgba(0,0,0,0.2);
    }
  `]
})
export class TasksComponent implements OnInit {
  private taskService = inject(TaskService);

  tasks = signal<EngineTask[]>([]);
  totalTasks = signal(0);
  loading = signal(false);
  selectedTask = signal<EngineTask | null>(null);

  stateFilter = '';
  pageSize = 25;
  pageIndex = 0;

  ngOnInit() {
    this.loadTasks();
  }

  loadTasks() {
    this.loading.set(true);
    const params: TaskListParams = {
      limit: this.pageSize,
      offset: this.pageIndex * this.pageSize,
      order_by: 'created_at',
      order_dir: 'DESC',
    };
    if (this.stateFilter) {
      params.state = this.stateFilter as EngineTaskState;
    }
    this.taskService.listTasks(params).subscribe({
      next: res => {
        this.tasks.set(res.tasks);
        this.totalTasks.set(res.total);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  getInputPreview(task: EngineTask): string {
    if (!task.input?.parts?.length) return '(sin input)';
    const textPart = task.input.parts.find(p => p.type === 'text');
    return textPart?.text?.substring(0, 120) || '(sin texto)';
  }

  selectTask(task: EngineTask) {
    this.selectedTask.set(task);
  }

  closeDetail(event: MouseEvent) {
    this.selectedTask.set(null);
  }

  onPage(event: PageEvent) {
    this.pageSize = event.pageSize;
    this.pageIndex = event.pageIndex;
    this.loadTasks();
  }

  onTaskCanceledEvent(task: EngineTask) {
    this.loadTasks();
    this.selectedTask.set(null);
  }

  onTaskResumedEvent(task: EngineTask) {
    this.loadTasks();
  }
}
