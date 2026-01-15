import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { StrapiService } from '../../core/services/strapi.service';
import { ExecutionLog } from '../../core/models';

@Component({
  selector: 'app-monitoring',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatTableModule,
    MatPaginatorModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatTooltipModule
  ],
  template: `
    <div class="monitoring-page">
      <div class="page-header">
        <div>
          <h1>Monitorización</h1>
          <p class="subtitle">Historial de ejecuciones y métricas del sistema</p>
        </div>
        <button mat-raised-button (click)="loadExecutions()">
          <mat-icon>refresh</mat-icon>
          Actualizar
        </button>
      </div>

      <!-- Stats Summary -->
      <div class="stats-row">
        <mat-card class="stat-mini">
          <span class="stat-value success">{{ statusCounts().completed }}</span>
          <span class="stat-label">Completadas</span>
        </mat-card>
        <mat-card class="stat-mini">
          <span class="stat-value running">{{ statusCounts().running }}</span>
          <span class="stat-label">En ejecución</span>
        </mat-card>
        <mat-card class="stat-mini">
          <span class="stat-value failed">{{ statusCounts().failed }}</span>
          <span class="stat-label">Fallidas</span>
        </mat-card>
        <mat-card class="stat-mini">
          <span class="stat-value pending">{{ statusCounts().pending }}</span>
          <span class="stat-label">Pendientes</span>
        </mat-card>
      </div>

      <!-- Executions Table -->
      <mat-card class="table-card">
        @if (loading()) {
          <div class="loading-container">
            <mat-spinner diameter="40"></mat-spinner>
          </div>
        } @else {
          <table mat-table [dataSource]="executions()" class="executions-table">
            <!-- ID Column -->
            <ng-container matColumnDef="executionId">
              <th mat-header-cell *matHeaderCellDef>ID</th>
              <td mat-cell *matCellDef="let exec">
                <code>{{ exec.executionId?.slice(0, 8) }}...</code>
              </td>
            </ng-container>

            <!-- Chain Column -->
            <ng-container matColumnDef="chain">
              <th mat-header-cell *matHeaderCellDef>Cadena</th>
              <td mat-cell *matCellDef="let exec">
                {{ exec.brainChain?.name || 'N/A' }}
              </td>
            </ng-container>

            <!-- Status Column -->
            <ng-container matColumnDef="status">
              <th mat-header-cell *matHeaderCellDef>Estado</th>
              <td mat-cell *matCellDef="let exec">
                <mat-chip [class]="exec.status">
                  <mat-icon>{{ getStatusIcon(exec.status) }}</mat-icon>
                  {{ getStatusLabel(exec.status) }}
                </mat-chip>
              </td>
            </ng-container>

            <!-- Duration Column -->
            <ng-container matColumnDef="duration">
              <th mat-header-cell *matHeaderCellDef>Duración</th>
              <td mat-cell *matCellDef="let exec">
                {{ formatDuration(exec.durationMs) }}
              </td>
            </ng-container>

            <!-- Tokens Column -->
            <ng-container matColumnDef="tokens">
              <th mat-header-cell *matHeaderCellDef>Tokens</th>
              <td mat-cell *matCellDef="let exec">
                {{ exec.tokensUsed || '-' }}
              </td>
            </ng-container>

            <!-- Date Column -->
            <ng-container matColumnDef="createdAt">
              <th mat-header-cell *matHeaderCellDef>Fecha</th>
              <td mat-cell *matCellDef="let exec">
                {{ formatDate(exec.createdAt) }}
              </td>
            </ng-container>

            <!-- Actions Column -->
            <ng-container matColumnDef="actions">
              <th mat-header-cell *matHeaderCellDef></th>
              <td mat-cell *matCellDef="let exec">
                <button mat-icon-button matTooltip="Ver detalles">
                  <mat-icon>visibility</mat-icon>
                </button>
                <button mat-icon-button matTooltip="Ver trace">
                  <mat-icon>timeline</mat-icon>
                </button>
              </td>
            </ng-container>

            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
          </table>

          @if (executions().length === 0) {
            <div class="empty-table">
              <mat-icon>history</mat-icon>
              <p>No hay ejecuciones registradas</p>
            </div>
          }

          <mat-paginator
            [length]="totalExecutions()"
            [pageSize]="pageSize"
            [pageSizeOptions]="[10, 25, 50]"
            (page)="onPageChange($event)">
          </mat-paginator>
        }
      </mat-card>
    </div>
  `,
  styles: [`
    .monitoring-page {
      max-width: 1400px;
      margin: 0 auto;
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 24px;
    }

    h1 {
      margin: 0;
      font-size: 28px;
      font-weight: 600;
      color: #1a1a2e;
    }

    .subtitle {
      color: #666;
      margin: 4px 0 0;
    }

    .stats-row {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      margin-bottom: 24px;
    }

    .stat-mini {
      padding: 16px 20px;
      text-align: center;
      border-radius: 12px;
    }

    .stat-value {
      display: block;
      font-size: 32px;
      font-weight: 700;
      margin-bottom: 4px;
    }

    .stat-value.success { color: #4caf50; }
    .stat-value.running { color: #2196f3; }
    .stat-value.failed { color: #f44336; }
    .stat-value.pending { color: #ff9800; }

    .stat-label {
      font-size: 13px;
      color: #666;
    }

    .table-card {
      border-radius: 12px;
      overflow: hidden;
    }

    .loading-container {
      display: flex;
      justify-content: center;
      padding: 48px;
    }

    .executions-table {
      width: 100%;
    }

    code {
      background: #f5f5f5;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 12px;
    }

    mat-chip {
      font-size: 12px;
    }

    mat-chip.completed {
      background: #e8f5e9 !important;
      color: #388e3c !important;
    }

    mat-chip.running {
      background: #e3f2fd !important;
      color: #1976d2 !important;
    }

    mat-chip.failed {
      background: #ffebee !important;
      color: #c62828 !important;
    }

    mat-chip.pending {
      background: #fff3e0 !important;
      color: #ef6c00 !important;
    }

    mat-chip.cancelled {
      background: #fafafa !important;
      color: #757575 !important;
    }

    mat-chip mat-icon {
      font-size: 14px;
      width: 14px;
      height: 14px;
      margin-right: 4px;
    }

    .empty-table {
      text-align: center;
      padding: 48px;
      color: #666;
    }

    .empty-table mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      color: #ccc;
      margin-bottom: 8px;
    }

    @media (max-width: 768px) {
      .stats-row {
        grid-template-columns: repeat(2, 1fr);
      }
    }
  `]
})
export class MonitoringComponent implements OnInit {
  executions = signal<ExecutionLog[]>([]);
  totalExecutions = signal(0);
  loading = signal(true);
  pageSize = 10;
  currentPage = 1;

  displayedColumns = ['executionId', 'chain', 'status', 'duration', 'tokens', 'createdAt', 'actions'];

  statusCounts = signal({ completed: 0, running: 0, failed: 0, pending: 0 });

  constructor(private strapiService: StrapiService) {}

  ngOnInit(): void {
    this.loadExecutions();
  }

  loadExecutions(): void {
    this.loading.set(true);
    this.strapiService.getExecutionLogs({ page: this.currentPage, pageSize: this.pageSize }).subscribe({
      next: (response) => {
        this.executions.set(response.data);
        this.totalExecutions.set(response.meta.pagination.total);
        this.calculateStatusCounts(response.data);
        this.loading.set(false);
      },
      error: () => this.loading.set(false)
    });
  }

  onPageChange(event: PageEvent): void {
    this.currentPage = event.pageIndex + 1;
    this.pageSize = event.pageSize;
    this.loadExecutions();
  }

  calculateStatusCounts(executions: ExecutionLog[]): void {
    const counts = { completed: 0, running: 0, failed: 0, pending: 0 };
    executions.forEach(e => {
      if (e.status in counts) {
        counts[e.status as keyof typeof counts]++;
      }
    });
    this.statusCounts.set(counts);
  }

  getStatusIcon(status: string): string {
    const icons: Record<string, string> = {
      completed: 'check_circle',
      running: 'sync',
      failed: 'error',
      pending: 'schedule',
      cancelled: 'cancel'
    };
    return icons[status] || 'help';
  }

  getStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      completed: 'Completado',
      running: 'En ejecución',
      failed: 'Fallido',
      pending: 'Pendiente',
      cancelled: 'Cancelado'
    };
    return labels[status] || status;
  }

  formatDuration(ms: number | undefined): string {
    if (!ms) return '-';
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  }

  formatDate(date: string): string {
    return new Date(date).toLocaleString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}
