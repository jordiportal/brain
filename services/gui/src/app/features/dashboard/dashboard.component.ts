import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { StrapiService } from '../../core/services/strapi.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    RouterModule
  ],
  template: `
    <div class="dashboard">
      <h1>Dashboard</h1>
      <p class="subtitle">Resumen del sistema Brain</p>

      <!-- Stats Cards -->
      <div class="stats-grid">
        <mat-card class="stat-card">
          <mat-card-content>
            <div class="stat-icon chains">
              <mat-icon>account_tree</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ stats().chains }}</span>
              <span class="stat-label">Cadenas Activas</span>
            </div>
          </mat-card-content>
        </mat-card>

        <mat-card class="stat-card">
          <mat-card-content>
            <div class="stat-icon providers">
              <mat-icon>smart_toy</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ stats().llmProviders }}</span>
              <span class="stat-label">Proveedores LLM</span>
            </div>
          </mat-card-content>
        </mat-card>

        <mat-card class="stat-card">
          <mat-card-content>
            <div class="stat-icon executions">
              <mat-icon>play_circle</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ stats().executions }}</span>
              <span class="stat-label">Ejecuciones Hoy</span>
            </div>
          </mat-card-content>
        </mat-card>

        <mat-card class="stat-card">
          <mat-card-content>
            <div class="stat-icon mcp">
              <mat-icon>extension</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ stats().mcpConnections }}</span>
              <span class="stat-label">Conexiones MCP</span>
            </div>
          </mat-card-content>
        </mat-card>
      </div>

      <!-- Quick Actions -->
      <div class="section">
        <h2>Acciones Rápidas</h2>
        <div class="actions-grid">
          <mat-card class="action-card" routerLink="/chains">
            <mat-icon>add_circle</mat-icon>
            <span>Nueva Cadena</span>
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

      <!-- System Status -->
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
              <mat-icon mat-card-avatar [class]="apiStatus().class">{{ apiStatus().icon }}</mat-icon>
              <mat-card-title>PostgreSQL</mat-card-title>
              <mat-card-subtitle>{{ dbStatus().message }}</mat-card-subtitle>
            </mat-card-header>
          </mat-card>

          <mat-card class="status-card">
            <mat-card-header>
              <mat-icon mat-card-avatar [class]="dbStatus().class">{{ dbStatus().icon }}</mat-icon>
              <mat-card-title>Base de Datos</mat-card-title>
              <mat-card-subtitle>{{ dbStatus().message }}</mat-card-subtitle>
            </mat-card-header>
          </mat-card>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .dashboard {
      max-width: 1400px;
      margin: 0 auto;
    }

    h1 {
      margin: 0;
      font-size: 28px;
      font-weight: 600;
      color: #1a1a2e;
    }

    .subtitle {
      color: #666;
      margin-top: 4px;
      margin-bottom: 24px;
    }

    h2 {
      font-size: 18px;
      font-weight: 600;
      color: #333;
      margin-bottom: 16px;
    }

    .section {
      margin-top: 32px;
    }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 20px;
    }

    .stat-card {
      border-radius: 12px;
    }

    .stat-card mat-card-content {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 20px;
    }

    .stat-icon {
      width: 56px;
      height: 56px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .stat-icon mat-icon {
      font-size: 28px;
      width: 28px;
      height: 28px;
      color: white;
    }

    .stat-icon.chains { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .stat-icon.providers { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
    .stat-icon.executions { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
    .stat-icon.mcp { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }

    .stat-info {
      display: flex;
      flex-direction: column;
    }

    .stat-value {
      font-size: 32px;
      font-weight: 700;
      color: #1a1a2e;
    }

    .stat-label {
      font-size: 14px;
      color: #666;
    }

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
      border-radius: 12px;
    }

    .action-card:hover {
      transform: translateY(-4px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.12);
    }

    .action-card mat-icon {
      font-size: 36px;
      width: 36px;
      height: 36px;
      color: #667eea;
      margin-bottom: 8px;
    }

    .action-card span {
      display: block;
      font-weight: 500;
      color: #333;
    }

    .status-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
    }

    .status-card {
      border-radius: 12px;
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
      background: rgba(76, 175, 80, 0.1);
      color: #4caf50;
    }

    .status-card mat-icon.offline {
      background: rgba(244, 67, 54, 0.1);
      color: #f44336;
    }

    .status-card mat-icon.checking {
      background: rgba(255, 152, 0, 0.1);
      color: #ff9800;
    }
  `]
})
export class DashboardComponent implements OnInit {
  stats = signal({ chains: 0, llmProviders: 0, executions: 0, mcpConnections: 0 });
  apiStatus = signal({ icon: 'sync', message: 'Verificando...', class: 'checking' });
  dbStatus = signal({ icon: 'sync', message: 'Verificando...', class: 'checking' });

  constructor(
    private apiService: ApiService,
    private strapiService: StrapiService
  ) {}

  ngOnInit(): void {
    this.loadStats();
    this.checkSystemStatus();
  }

  private loadStats(): void {
    // Cargar estadísticas desde la API de Python
    this.strapiService.getSystemStats().subscribe({
      next: (stats) => {
        this.stats.set({
          chains: stats.chains,
          llmProviders: stats.llmProviders,
          mcpConnections: stats.mcpConnections,
          executions: stats.executions
        });
      },
      error: (err) => {
        console.error('Error loading stats:', err);
      }
    });
  }

  private checkSystemStatus(): void {
    // Verificar API Python
    this.apiService.getHealth().subscribe({
      next: (health) => {
        this.apiStatus.set({ 
          icon: 'check_circle', 
          message: `Online - v${health.version}`, 
          class: 'online' 
        });
        this.dbStatus.set({ 
          icon: 'check_circle', 
          message: 'Conectada', 
          class: 'online' 
        });
      },
      error: () => {
        this.apiStatus.set({ 
          icon: 'error', 
          message: 'No disponible', 
          class: 'offline' 
        });
        this.dbStatus.set({ 
          icon: 'error', 
          message: 'No disponible', 
          class: 'offline' 
        });
      }
    });
  }
}
