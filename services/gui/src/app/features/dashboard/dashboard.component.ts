import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { StrapiService } from '../../core/services/config.service';
import { forkJoin } from 'rxjs';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    RouterModule
  ],
  template: `
    <div class="admin-page">
      <div class="page-header">
        <div class="header-title">
          <mat-icon>dashboard</mat-icon>
          <div>
            <h1>Dashboard</h1>
            <p class="subtitle">Resumen del sistema Brain</p>
          </div>
        </div>
      </div>

      <!-- Row 1: Stats principales -->
      <div class="dash-stats-grid">
        <mat-card class="dash-stat-card">
          <mat-card-content>
            <div class="dash-stat-icon chains">
              <mat-icon>account_tree</mat-icon>
            </div>
            <div class="dash-stat-info">
              <span class="dash-stat-value">{{ stats().chains }}</span>
              <span class="dash-stat-label">Asistentes Activos</span>
            </div>
          </mat-card-content>
        </mat-card>

        <mat-card class="dash-stat-card">
          <mat-card-content>
            <div class="dash-stat-icon providers">
              <mat-icon>smart_toy</mat-icon>
            </div>
            <div class="dash-stat-info">
              <span class="dash-stat-value">{{ stats().llmProviders }}</span>
              <span class="dash-stat-label">Proveedores LLM</span>
            </div>
          </mat-card-content>
        </mat-card>

        <mat-card class="dash-stat-card">
          <mat-card-content>
            <div class="dash-stat-icon tools">
              <mat-icon>build</mat-icon>
            </div>
            <div class="dash-stat-info">
              <span class="dash-stat-value">{{ readiness().tools_total }}</span>
              <span class="dash-stat-label">Herramientas</span>
            </div>
          </mat-card-content>
        </mat-card>

        <mat-card class="dash-stat-card">
          <mat-card-content>
            <div class="dash-stat-icon mcp">
              <mat-icon>extension</mat-icon>
            </div>
            <div class="dash-stat-info">
              <span class="dash-stat-value">{{ stats().mcpConnections }}</span>
              <span class="dash-stat-label">Conexiones MCP</span>
            </div>
          </mat-card-content>
        </mat-card>
      </div>

      <!-- Row 2: Métricas operativas -->
      <div class="section">
        <h2>Métricas del Día</h2>
        <div class="metrics-grid">
          <mat-card class="metric-card">
            <mat-card-content>
              <div class="metric-value">{{ metrics().total_requests | number }}</div>
              <div class="metric-label">Requests hoy</div>
            </mat-card-content>
          </mat-card>
          <mat-card class="metric-card">
            <mat-card-content>
              <div class="metric-value">{{ formatLatency(metrics().avg_latency_ms) }}</div>
              <div class="metric-label">Latencia media</div>
            </mat-card-content>
          </mat-card>
          <mat-card class="metric-card">
            <mat-card-content>
              <div class="metric-value">{{ formatTokens(metrics().total_tokens) }}</div>
              <div class="metric-label">Tokens consumidos</div>
            </mat-card-content>
          </mat-card>
          <mat-card class="metric-card">
            <mat-card-content>
              <div class="metric-value">\${{ metrics().total_cost_usd | number:'1.2-2' }}</div>
              <div class="metric-label">Coste estimado</div>
            </mat-card-content>
          </mat-card>
          <mat-card class="metric-card">
            <mat-card-content>
              <div class="metric-value" [class.metric-danger]="metrics().error_rate > 0.05">
                {{ (metrics().error_rate * 100) | number:'1.1-1' }}%
              </div>
              <div class="metric-label">Tasa de error</div>
            </mat-card-content>
          </mat-card>
          <mat-card class="metric-card">
            <mat-card-content>
              <div class="metric-value" [class.metric-warning]="metrics().active_alerts > 0">
                {{ metrics().active_alerts }}
                <mat-icon *ngIf="metrics().critical_alerts > 0" class="alert-badge">warning</mat-icon>
              </div>
              <div class="metric-label">Alertas activas</div>
            </mat-card-content>
          </mat-card>
        </div>
      </div>

      <!-- Row 3: Actividad de Usuarios -->
      <div class="section">
        <h2>Actividad de Usuarios</h2>
        <div class="user-activity-grid">
          <div class="user-activity-cards">
            <mat-card class="activity-card">
              <mat-card-content>
                <div class="activity-value activity-today">{{ userActivity().active_users_today }}</div>
                <div class="activity-label">Hoy</div>
              </mat-card-content>
            </mat-card>
            <mat-card class="activity-card">
              <mat-card-content>
                <div class="activity-value activity-7d">{{ userActivity().active_users_7d }}</div>
                <div class="activity-label">Últimos 7 días</div>
              </mat-card-content>
            </mat-card>
            <mat-card class="activity-card">
              <mat-card-content>
                <div class="activity-value activity-30d">{{ userActivity().active_users_30d }}</div>
                <div class="activity-label">Último mes</div>
              </mat-card-content>
            </mat-card>
            <mat-card class="activity-card">
              <mat-card-content>
                <div class="activity-value activity-total">{{ userActivity().total_registered_users }}</div>
                <div class="activity-label">Registrados</div>
              </mat-card-content>
            </mat-card>
          </div>

          <mat-card class="top-users-card" *ngIf="userActivity().top_users.length > 0">
            <mat-card-content>
              <h3>Top Usuarios (24h)</h3>
              <div class="top-users-list">
                <div class="top-user-row" *ngFor="let user of userActivity().top_users.slice(0, 5); let i = index">
                  <span class="top-user-rank">#{{ i + 1 }}</span>
                  <span class="top-user-email">{{ user.user_id }}</span>
                  <span class="top-user-count">{{ user.request_count }} req</span>
                </div>
              </div>
            </mat-card-content>
          </mat-card>
        </div>
      </div>

      <!-- Row 4: Acciones Rápidas -->
      <div class="section">
        <h2>Acciones Rápidas</h2>
        <div class="actions-grid">
          <mat-card class="action-card" routerLink="/chains">
            <mat-icon>add_circle</mat-icon>
            <span>Nuevo Asistente</span>
          </mat-card>
          <mat-card class="action-card" routerLink="/settings">
            <mat-icon>settings</mat-icon>
            <span>Configurar LLM</span>
          </mat-card>
          <mat-card class="action-card" routerLink="/monitoring">
            <mat-icon>monitoring</mat-icon>
            <span>Ver Ejecuciones</span>
          </mat-card>
          <mat-card class="action-card" routerLink="/rag">
            <mat-icon>upload_file</mat-icon>
            <span>Subir Documentos</span>
          </mat-card>
        </div>
      </div>

      <!-- Row 5: Estado del Sistema -->
      <div class="section">
        <h2>Estado del Sistema</h2>
        <div class="status-grid">
          <mat-card class="status-card">
            <mat-card-header>
              <mat-icon mat-card-avatar [class]="apiStatus().class">{{ apiStatus().icon }}</mat-icon>
              <mat-card-title>API Python</mat-card-title>
              <mat-card-subtitle>{{ apiStatus().message }}</mat-card-subtitle>
            </mat-card-header>
          </mat-card>

          <mat-card class="status-card">
            <mat-card-header>
              <mat-icon mat-card-avatar [class]="dbStatus().class">{{ dbStatus().icon }}</mat-icon>
              <mat-card-title>Base de Datos</mat-card-title>
              <mat-card-subtitle>{{ dbStatus().message }}</mat-card-subtitle>
            </mat-card-header>
          </mat-card>

          <mat-card class="status-card">
            <mat-card-header>
              <mat-icon mat-card-avatar [class]="redisStatus().class">{{ redisStatus().icon }}</mat-icon>
              <mat-card-title>Redis</mat-card-title>
              <mat-card-subtitle>{{ redisStatus().message }}</mat-card-subtitle>
            </mat-card-header>
          </mat-card>

          <mat-card class="status-card">
            <mat-card-header>
              <mat-icon mat-card-avatar [class]="mcpStatus().class">{{ mcpStatus().icon }}</mat-icon>
              <mat-card-title>MCP</mat-card-title>
              <mat-card-subtitle>{{ mcpStatus().message }}</mat-card-subtitle>
            </mat-card-header>
          </mat-card>
        </div>
      </div>
    </div>
  `,
  styles: [`
    h2 {
      font-size: 18px;
      font-weight: 600;
      color: #1e293b;
      margin-bottom: 16px;
    }

    h3 {
      font-size: 15px;
      font-weight: 600;
      color: #1e293b;
      margin: 0 0 12px;
    }

    .section {
      margin-top: 32px;
    }

    /* Row 1: Stat cards with gradient icons */
    .dash-stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 20px;
    }

    .dash-stat-card mat-card-content {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 20px;
    }

    .dash-stat-icon {
      width: 56px;
      height: 56px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .dash-stat-icon mat-icon {
      font-size: 28px;
      width: 28px;
      height: 28px;
      color: white;
    }

    .dash-stat-icon.chains { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .dash-stat-icon.providers { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
    .dash-stat-icon.tools { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
    .dash-stat-icon.mcp { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }

    .dash-stat-info {
      display: flex;
      flex-direction: column;
    }

    .dash-stat-value {
      font-size: 32px;
      font-weight: 700;
      color: #1e293b;
    }

    .dash-stat-label {
      font-size: 14px;
      color: #64748b;
    }

    /* Row 2: Metric cards */
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 16px;
    }

    .metric-card {
      text-align: center;
    }

    .metric-card mat-card-content {
      padding: 20px 16px;
    }

    .metric-value {
      font-size: 24px;
      font-weight: 700;
      color: #3b82f6;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
    }

    .metric-value.metric-danger {
      color: #ef4444;
    }

    .metric-value.metric-warning {
      color: #f59e0b;
    }

    .alert-badge {
      font-size: 18px;
      width: 18px;
      height: 18px;
      color: #ef4444;
    }

    .metric-label {
      font-size: 12px;
      color: #64748b;
      margin-top: 4px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    /* Row 3: User activity */
    .user-activity-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      align-items: start;
    }

    @media (max-width: 900px) {
      .user-activity-grid {
        grid-template-columns: 1fr;
      }
    }

    .user-activity-cards {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }

    .activity-card {
      text-align: center;
    }

    .activity-card mat-card-content {
      padding: 20px 16px;
    }

    .activity-value {
      font-size: 32px;
      font-weight: 700;
    }

    .activity-today { color: #3b82f6; }
    .activity-7d { color: #8b5cf6; }
    .activity-30d { color: #22c55e; }
    .activity-total { color: #64748b; }

    .activity-label {
      font-size: 12px;
      color: #64748b;
      margin-top: 4px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .top-users-card mat-card-content {
      padding: 20px;
    }

    .top-users-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .top-user-row {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 8px 12px;
      border-radius: 8px;
      background: #f8fafc;
    }

    .top-user-rank {
      font-weight: 700;
      color: #8b5cf6;
      width: 28px;
    }

    .top-user-email {
      flex: 1;
      font-size: 13px;
      color: #1e293b;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .top-user-count {
      font-size: 13px;
      font-weight: 600;
      color: #3b82f6;
      white-space: nowrap;
    }

    /* Row 4: Action cards */
    .actions-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 16px;
    }

    .action-card {
      padding: 24px;
      text-align: center;
      cursor: pointer;
      transition: transform 0.2s, box-shadow 0.2s;
    }

    .action-card:hover {
      transform: translateY(-4px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.12);
    }

    .action-card mat-icon {
      font-size: 36px;
      width: 36px;
      height: 36px;
      color: #3b82f6;
      margin-bottom: 8px;
    }

    .action-card span {
      display: block;
      font-weight: 500;
      color: #1e293b;
    }

    /* Row 5: Status cards */
    .status-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
    }

    .status-card mat-icon {
      font-size: 24px;
      width: 40px;
      height: 40px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .status-card mat-icon.online {
      background: rgba(34, 197, 94, 0.1);
      color: #22c55e;
    }

    .status-card mat-icon.offline {
      background: rgba(239, 68, 68, 0.1);
      color: #ef4444;
    }

    .status-card mat-icon.checking {
      background: rgba(245, 158, 11, 0.1);
      color: #f59e0b;
    }
  `]
})
export class DashboardComponent implements OnInit {
  stats = signal({ chains: 0, llmProviders: 0, mcpConnections: 0, apiKeys: 0, openApiConnections: 0 });
  metrics = signal({
    requests_per_minute: 0, avg_latency_ms: 0, error_rate: 0,
    total_requests: 0, total_errors: 0, total_tokens: 0, total_cost_usd: 0,
    active_alerts: 0, critical_alerts: 0
  });
  userActivity = signal({
    active_users_today: 0, active_users_7d: 0, active_users_30d: 0,
    total_registered_users: 0, top_users: [] as any[], hourly_active_users: [] as any[]
  });
  readiness = signal({ tools_total: 0, tools_openapi: 0, mcp_connected: 0, mcp_connections: 0, database: '', redis: '' });

  apiStatus = signal({ icon: 'sync', message: 'Verificando...', class: 'checking' });
  dbStatus = signal({ icon: 'sync', message: 'Verificando...', class: 'checking' });
  redisStatus = signal({ icon: 'sync', message: 'Verificando...', class: 'checking' });
  mcpStatus = signal({ icon: 'sync', message: 'Verificando...', class: 'checking' });

  constructor(
    private apiService: ApiService,
    private strapiService: StrapiService
  ) {}

  ngOnInit(): void {
    this.loadAllData();
  }

  private loadAllData(): void {
    forkJoin({
      stats: this.strapiService.getSystemStats(),
      metrics: this.strapiService.getDashboardMetrics(),
      activity: this.strapiService.getUserActivity(),
      health: this.apiService.getHealth(),
      readiness: this.apiService.getReadiness()
    }).subscribe({
      next: ({ stats, metrics, activity, health, readiness }) => {
        this.stats.set(stats);
        this.metrics.set(metrics);
        this.userActivity.set(activity);
        this.readiness.set(readiness);

        this.apiStatus.set({
          icon: 'check_circle',
          message: `Online - v${health.version}`,
          class: 'online'
        });

        this.dbStatus.set({
          icon: readiness.database === 'connected' ? 'check_circle' : 'error',
          message: readiness.database === 'connected' ? 'Conectada' : 'No disponible',
          class: readiness.database === 'connected' ? 'online' : 'offline'
        });

        this.redisStatus.set({
          icon: readiness.redis === 'connected' ? 'check_circle' : 'error',
          message: readiness.redis === 'connected' ? 'Conectado' : 'No disponible',
          class: readiness.redis === 'connected' ? 'online' : 'offline'
        });

        const mcpConn = readiness.mcp_connected || 0;
        const mcpTotal = readiness.mcp_connections || 0;
        this.mcpStatus.set({
          icon: mcpConn > 0 ? 'check_circle' : (mcpTotal > 0 ? 'error' : 'remove_circle_outline'),
          message: mcpTotal > 0 ? `${mcpConn}/${mcpTotal} conectados` : 'Sin conexiones',
          class: mcpConn > 0 ? 'online' : (mcpTotal > 0 ? 'offline' : 'checking')
        });
      },
      error: () => {
        this.apiStatus.set({ icon: 'error', message: 'No disponible', class: 'offline' });
        this.dbStatus.set({ icon: 'error', message: 'No disponible', class: 'offline' });
        this.redisStatus.set({ icon: 'error', message: 'No disponible', class: 'offline' });
        this.mcpStatus.set({ icon: 'error', message: 'No disponible', class: 'offline' });
      }
    });
  }

  formatLatency(ms: number): string {
    if (ms < 1) return '0 ms';
    if (ms < 1000) return `${Math.round(ms)} ms`;
    return `${(ms / 1000).toFixed(1)} s`;
  }

  formatTokens(tokens: number): string {
    if (tokens < 1000) return tokens.toString();
    if (tokens < 1_000_000) return `${(tokens / 1000).toFixed(1)} K`;
    return `${(tokens / 1_000_000).toFixed(2)} M`;
  }
}
