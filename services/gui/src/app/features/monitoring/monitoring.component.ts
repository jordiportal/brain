import { Component, OnInit, OnDestroy, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatTabsModule } from '@angular/material/tabs';
import { MatBadgeModule } from '@angular/material/badge';
import { MatDividerModule } from '@angular/material/divider';
import { environment } from '../../../environments/environment';

interface DashboardStats {
  requests_per_minute: number;
  avg_latency_ms: number;
  error_rate: number;
  active_executions: number;
  total_requests: number;
  total_errors: number;
  total_tokens: number;
  total_cost_usd: number;
  hourly_requests: { hour: string; count: number }[];
  hourly_latency: { hour: string; latency: number }[];
  top_endpoints: { endpoint: string; request_count: number; avg_latency_ms: number; error_count: number }[];
  chain_stats: { chain_id: string; execution_count: number; avg_duration_ms: number; total_cost_usd: number; error_count: number }[];
  active_alerts: number;
  critical_alerts: number;
}

interface Alert {
  id: number;
  timestamp: string;
  alert_type: string;
  severity: string;
  message: string;
  acknowledged: boolean;
}

interface Execution {
  execution_id: string;
  chain_id: string;
  timestamp: string;
  duration_ms: number;
  success: boolean;
  error_message?: string;
}

@Component({
  selector: 'app-monitoring',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatTabsModule,
    MatBadgeModule,
    MatDividerModule
  ],
  template: `
    <div class="monitoring-page">
      <div class="page-header">
        <div>
          <h1>Monitorizacion</h1>
          <p class="subtitle">Metricas, trazas y alertas del sistema</p>
        </div>
        <div class="header-actions">
          @if (stats()?.critical_alerts) {
            <mat-chip class="alert-chip critical">
              <mat-icon>warning</mat-icon>
              {{ stats()?.critical_alerts }} alertas criticas
            </mat-chip>
          }
          <button mat-raised-button color="primary" (click)="refreshAll()">
            <mat-icon>refresh</mat-icon>
            Actualizar
          </button>
        </div>
      </div>

      @if (loading()) {
        <div class="loading-container">
          <mat-spinner diameter="48"></mat-spinner>
          <p>Cargando metricas...</p>
        </div>
      } @else {
        <!-- Stats Cards -->
        <div class="stats-grid">
          <mat-card class="stat-card">
            <div class="stat-icon requests">
              <mat-icon>trending_up</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ stats()?.requests_per_minute | number:'1.0-0' }}</span>
              <span class="stat-label">Requests/min</span>
            </div>
          </mat-card>
          
          <mat-card class="stat-card">
            <div class="stat-icon latency">
              <mat-icon>speed</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ stats()?.avg_latency_ms | number:'1.0-0' }}ms</span>
              <span class="stat-label">Latencia media</span>
            </div>
          </mat-card>
          
          <mat-card class="stat-card">
            <div class="stat-icon" [class.error-high]="(stats()?.error_rate || 0) > 0.05">
              <mat-icon>error_outline</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value" [class.error-value]="(stats()?.error_rate || 0) > 0.05">
                {{ (stats()?.error_rate || 0) * 100 | number:'1.1-1' }}%
              </span>
              <span class="stat-label">Error rate</span>
            </div>
          </mat-card>
          
          <mat-card class="stat-card">
            <div class="stat-icon cost">
              <mat-icon>payments</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value">\${{ stats()?.total_cost_usd | number:'1.2-2' }}</span>
              <span class="stat-label">Coste LLM (hoy)</span>
            </div>
          </mat-card>
        </div>

        <!-- Secondary Stats -->
        <div class="secondary-stats">
          <mat-card class="mini-stat">
            <mat-icon>api</mat-icon>
            <div>
              <span class="value">{{ stats()?.total_requests | number }}</span>
              <span class="label">Requests totales</span>
            </div>
          </mat-card>
          <mat-card class="mini-stat">
            <mat-icon>token</mat-icon>
            <div>
              <span class="value">{{ formatTokens(stats()?.total_tokens || 0) }}</span>
              <span class="label">Tokens usados</span>
            </div>
          </mat-card>
          <mat-card class="mini-stat">
            <mat-icon>error</mat-icon>
            <div>
              <span class="value">{{ stats()?.total_errors | number }}</span>
              <span class="label">Errores totales</span>
            </div>
          </mat-card>
          <mat-card class="mini-stat" [class.has-alerts]="stats()?.active_alerts">
            <mat-icon>notifications</mat-icon>
            <div>
              <span class="value">{{ stats()?.active_alerts }}</span>
              <span class="label">Alertas activas</span>
            </div>
          </mat-card>
        </div>

        <mat-tab-group>
          <!-- Tab: Endpoints -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon>api</mat-icon>
              Top Endpoints
            </ng-template>
            
            <div class="tab-content">
              <mat-card>
                <mat-card-header>
                  <mat-card-title>Endpoints mas utilizados (24h)</mat-card-title>
                </mat-card-header>
                <mat-card-content>
                  @if (stats()?.top_endpoints?.length) {
                    <table class="data-table">
                      <thead>
                        <tr>
                          <th>Endpoint</th>
                          <th>Requests</th>
                          <th>Latencia media</th>
                          <th>Errores</th>
                        </tr>
                      </thead>
                      <tbody>
                        @for (ep of stats()?.top_endpoints; track ep.endpoint) {
                          <tr>
                            <td><code>{{ ep.endpoint }}</code></td>
                            <td>{{ ep.request_count | number }}</td>
                            <td>{{ ep.avg_latency_ms | number:'1.0-0' }}ms</td>
                            <td [class.error-cell]="ep.error_count > 0">{{ ep.error_count }}</td>
                          </tr>
                        }
                      </tbody>
                    </table>
                  } @else {
                    <div class="empty-state">
                      <mat-icon>inbox</mat-icon>
                      <p>No hay datos de endpoints</p>
                    </div>
                  }
                </mat-card-content>
              </mat-card>
            </div>
          </mat-tab>

          <!-- Tab: Chains -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon>account_tree</mat-icon>
              Chains
            </ng-template>
            
            <div class="tab-content">
              <mat-card>
                <mat-card-header>
                  <mat-card-title>Estadisticas de Chains (7 dias)</mat-card-title>
                </mat-card-header>
                <mat-card-content>
                  @if (stats()?.chain_stats?.length) {
                    <table class="data-table">
                      <thead>
                        <tr>
                          <th>Chain</th>
                          <th>Ejecuciones</th>
                          <th>Duracion media</th>
                          <th>Coste</th>
                          <th>Errores</th>
                        </tr>
                      </thead>
                      <tbody>
                        @for (chain of stats()?.chain_stats; track chain.chain_id) {
                          <tr>
                            <td><strong>{{ chain.chain_id }}</strong></td>
                            <td>{{ chain.execution_count | number }}</td>
                            <td>{{ formatDuration(chain.avg_duration_ms) }}</td>
                            <td>\${{ chain.total_cost_usd | number:'1.4-4' }}</td>
                            <td [class.error-cell]="chain.error_count > 0">{{ chain.error_count }}</td>
                          </tr>
                        }
                      </tbody>
                    </table>
                  } @else {
                    <div class="empty-state">
                      <mat-icon>inbox</mat-icon>
                      <p>No hay datos de chains</p>
                    </div>
                  }
                </mat-card-content>
              </mat-card>
            </div>
          </mat-tab>

          <!-- Tab: Executions -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon>history</mat-icon>
              Ejecuciones
            </ng-template>
            
            <div class="tab-content">
              <mat-card>
                <mat-card-header>
                  <mat-card-title>Ejecuciones recientes</mat-card-title>
                </mat-card-header>
                <mat-card-content>
                  @if (executions().length) {
                    <table class="data-table">
                      <thead>
                        <tr>
                          <th>ID</th>
                          <th>Chain</th>
                          <th>Fecha</th>
                          <th>Duracion</th>
                          <th>Estado</th>
                        </tr>
                      </thead>
                      <tbody>
                        @for (exec of executions(); track exec.execution_id) {
                          <tr>
                            <td><code>{{ exec.execution_id.slice(0, 8) }}...</code></td>
                            <td>{{ exec.chain_id }}</td>
                            <td>{{ formatDate(exec.timestamp) }}</td>
                            <td>{{ formatDuration(exec.duration_ms) }}</td>
                            <td>
                              <mat-chip [class]="exec.success ? 'success' : 'error'">
                                <mat-icon>{{ exec.success ? 'check_circle' : 'error' }}</mat-icon>
                                {{ exec.success ? 'OK' : 'Error' }}
                              </mat-chip>
                            </td>
                          </tr>
                        }
                      </tbody>
                    </table>
                  } @else {
                    <div class="empty-state">
                      <mat-icon>inbox</mat-icon>
                      <p>No hay ejecuciones recientes</p>
                    </div>
                  }
                </mat-card-content>
              </mat-card>
            </div>
          </mat-tab>

          <!-- Tab: Alerts -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon [matBadge]="stats()?.active_alerts" matBadgeColor="warn" 
                        [matBadgeHidden]="!stats()?.active_alerts">notifications</mat-icon>
              Alertas
            </ng-template>
            
            <div class="tab-content">
              <mat-card>
                <mat-card-header>
                  <mat-card-title>Alertas activas</mat-card-title>
                </mat-card-header>
                <mat-card-content>
                  @if (alerts().length) {
                    <div class="alerts-list">
                      @for (alert of alerts(); track alert.id) {
                        <div class="alert-item" [class]="alert.severity">
                          <div class="alert-icon">
                            <mat-icon>{{ getAlertIcon(alert.severity) }}</mat-icon>
                          </div>
                          <div class="alert-content">
                            <span class="alert-type">{{ alert.alert_type }}</span>
                            <span class="alert-message">{{ alert.message }}</span>
                            <span class="alert-time">{{ formatDate(alert.timestamp) }}</span>
                          </div>
                          <button mat-icon-button (click)="acknowledgeAlert(alert.id)" 
                                  matTooltip="Marcar como vista">
                            <mat-icon>check</mat-icon>
                          </button>
                        </div>
                      }
                    </div>
                  } @else {
                    <div class="empty-state success">
                      <mat-icon>check_circle</mat-icon>
                      <p>No hay alertas activas</p>
                    </div>
                  }
                </mat-card-content>
              </mat-card>
            </div>
          </mat-tab>
        </mat-tab-group>
      }
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

    .header-actions {
      display: flex;
      gap: 12px;
      align-items: center;
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

    .loading-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 48px;
      gap: 16px;
      color: #666;
    }

    /* Stats Grid */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      margin-bottom: 16px;
    }

    .stat-card {
      display: flex;
      align-items: center;
      padding: 20px;
      border-radius: 12px;
      gap: 16px;
    }

    .stat-icon {
      width: 56px;
      height: 56px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #f0f4f8;
    }

    .stat-icon mat-icon {
      font-size: 28px;
      width: 28px;
      height: 28px;
    }

    .stat-icon.requests { background: #e3f2fd; color: #1976d2; }
    .stat-icon.latency { background: #f3e5f5; color: #7b1fa2; }
    .stat-icon.error-high { background: #ffebee; color: #c62828; }
    .stat-icon.cost { background: #e8f5e9; color: #388e3c; }

    .stat-info {
      display: flex;
      flex-direction: column;
    }

    .stat-value {
      font-size: 28px;
      font-weight: 700;
      color: #1a1a2e;
    }

    .stat-value.error-value {
      color: #c62828;
    }

    .stat-label {
      font-size: 13px;
      color: #666;
    }

    /* Secondary Stats */
    .secondary-stats {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
      margin-bottom: 24px;
    }

    .mini-stat {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      border-radius: 8px;
    }

    .mini-stat mat-icon {
      color: #666;
    }

    .mini-stat .value {
      display: block;
      font-size: 18px;
      font-weight: 600;
      color: #1a1a2e;
    }

    .mini-stat .label {
      display: block;
      font-size: 11px;
      color: #999;
    }

    .mini-stat.has-alerts {
      background: #fff3e0;
    }

    .mini-stat.has-alerts mat-icon {
      color: #ef6c00;
    }

    /* Alert chip */
    .alert-chip.critical {
      background: #ffebee !important;
      color: #c62828 !important;
    }

    .alert-chip mat-icon {
      font-size: 16px;
      margin-right: 4px;
    }

    /* Tabs */
    mat-tab-group {
      margin-top: 8px;
    }

    .tab-content {
      padding: 16px 0;
    }

    /* Data Table */
    .data-table {
      width: 100%;
      border-collapse: collapse;
    }

    .data-table th,
    .data-table td {
      padding: 12px 16px;
      text-align: left;
      border-bottom: 1px solid #eee;
    }

    .data-table th {
      font-weight: 600;
      color: #666;
      font-size: 12px;
      text-transform: uppercase;
    }

    .data-table code {
      background: #f5f5f5;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 12px;
    }

    .data-table .error-cell {
      color: #c62828;
      font-weight: 600;
    }

    /* Execution chips */
    mat-chip.success {
      background: #e8f5e9 !important;
      color: #388e3c !important;
    }

    mat-chip.error {
      background: #ffebee !important;
      color: #c62828 !important;
    }

    mat-chip mat-icon {
      font-size: 14px;
      width: 14px;
      height: 14px;
      margin-right: 4px;
    }

    /* Alerts List */
    .alerts-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .alert-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      border-radius: 8px;
      background: #fafafa;
    }

    .alert-item.critical {
      background: #ffebee;
      border-left: 4px solid #c62828;
    }

    .alert-item.warning {
      background: #fff3e0;
      border-left: 4px solid #ef6c00;
    }

    .alert-item.info {
      background: #e3f2fd;
      border-left: 4px solid #1976d2;
    }

    .alert-icon {
      width: 40px;
      height: 40px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .alert-item.critical .alert-icon { background: #ffcdd2; color: #c62828; }
    .alert-item.warning .alert-icon { background: #ffe0b2; color: #ef6c00; }
    .alert-item.info .alert-icon { background: #bbdefb; color: #1976d2; }

    .alert-content {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .alert-type {
      font-size: 11px;
      text-transform: uppercase;
      color: #999;
    }

    .alert-message {
      font-size: 14px;
      color: #333;
    }

    .alert-time {
      font-size: 11px;
      color: #999;
    }

    /* Empty State */
    .empty-state {
      text-align: center;
      padding: 48px;
      color: #999;
    }

    .empty-state mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      margin-bottom: 8px;
    }

    .empty-state.success mat-icon {
      color: #4caf50;
    }

    @media (max-width: 1024px) {
      .stats-grid {
        grid-template-columns: repeat(2, 1fr);
      }
      .secondary-stats {
        grid-template-columns: repeat(2, 1fr);
      }
    }

    @media (max-width: 600px) {
      .stats-grid {
        grid-template-columns: 1fr;
      }
      .secondary-stats {
        grid-template-columns: 1fr;
      }
    }
  `]
})
export class MonitoringComponent implements OnInit, OnDestroy {
  private http = inject(HttpClient);
  
  stats = signal<DashboardStats | null>(null);
  alerts = signal<Alert[]>([]);
  executions = signal<Execution[]>([]);
  loading = signal(true);
  
  private refreshInterval: any;

  ngOnInit(): void {
    this.refreshAll();
    // Auto-refresh cada 30 segundos
    this.refreshInterval = setInterval(() => this.refreshAll(), 30000);
  }

  ngOnDestroy(): void {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
  }

  refreshAll(): void {
    this.loading.set(true);
    
    // Cargar dashboard stats
    this.http.get<DashboardStats>(`${environment.apiUrl}/monitoring/dashboard`)
      .subscribe({
        next: (data) => {
          this.stats.set(data);
          this.loading.set(false);
        },
        error: (err) => {
          console.error('Error loading dashboard:', err);
          this.loading.set(false);
        }
      });
    
    // Cargar alertas activas
    this.http.get<{ alerts: Alert[] }>(`${environment.apiUrl}/monitoring/alerts?acknowledged=false&limit=10`)
      .subscribe({
        next: (data) => this.alerts.set(data.alerts),
        error: (err) => console.error('Error loading alerts:', err)
      });
    
    // Cargar ejecuciones recientes
    this.http.get<{ executions: Execution[] }>(`${environment.apiUrl}/monitoring/traces/recent/executions?limit=20`)
      .subscribe({
        next: (data) => this.executions.set(data.executions),
        error: (err) => console.error('Error loading executions:', err)
      });
  }

  acknowledgeAlert(alertId: number): void {
    this.http.put(`${environment.apiUrl}/monitoring/alerts/${alertId}/acknowledge`, {
      acknowledged_by: 'admin'
    }).subscribe({
      next: () => {
        // Remover de la lista local
        this.alerts.update(alerts => alerts.filter(a => a.id !== alertId));
        // Actualizar contador
        if (this.stats()) {
          this.stats.update(s => s ? { ...s, active_alerts: s.active_alerts - 1 } : null);
        }
      },
      error: (err) => console.error('Error acknowledging alert:', err)
    });
  }

  formatDuration(ms: number | undefined): string {
    if (!ms) return '-';
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  }

  formatDate(date: string): string {
    if (!date) return '-';
    return new Date(date).toLocaleString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  formatTokens(tokens: number): string {
    if (tokens < 1000) return tokens.toString();
    if (tokens < 1000000) return `${(tokens / 1000).toFixed(1)}K`;
    return `${(tokens / 1000000).toFixed(1)}M`;
  }

  getAlertIcon(severity: string): string {
    const icons: Record<string, string> = {
      critical: 'error',
      warning: 'warning',
      info: 'info'
    };
    return icons[severity] || 'notification_important';
  }
}
