import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

interface Sandbox {
  user_id: string;
  container_name: string;
  status: string;
  last_accessed_at: string;
  created_at: string;
}

@Component({
  selector: 'app-sandboxes',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatDialogModule,
  ],
  template: `
    <div class="sandboxes-page">
      <h1>Sandboxes de Usuario</h1>
      <p class="subtitle">Contenedores Docker aislados por usuario para ejecución de código y tareas programadas</p>

      <mat-card class="info-card">
        <mat-card-content>
          <div class="info-row">
            <div class="stat">
              <span class="stat-value">{{ sandboxes().length }}</span>
              <span class="stat-label">Sandboxes</span>
            </div>
            <div class="stat">
              <span class="stat-value running">{{ runningCount() }}</span>
              <span class="stat-label">Activos</span>
            </div>
            <div class="stat">
              <span class="stat-value stopped">{{ stoppedCount() }}</span>
              <span class="stat-label">Parados</span>
            </div>
            <div class="actions">
              <button mat-raised-button color="primary" (click)="loadSandboxes()" [disabled]="loading()">
                <mat-icon>refresh</mat-icon>
                Actualizar
              </button>
            </div>
          </div>
        </mat-card-content>
      </mat-card>

      @if (loading()) {
        <div class="loading">
          <mat-spinner diameter="40"></mat-spinner>
          <span>Cargando sandboxes...</span>
        </div>
      }

      @if (!loading() && sandboxes().length === 0) {
        <mat-card class="empty-card">
          <mat-card-content>
            <mat-icon class="empty-icon">dns</mat-icon>
            <h3>Sin sandboxes activos</h3>
            <p>Los sandboxes se crean automáticamente cuando un usuario accede al workspace o ejecuta tareas programadas.</p>
          </mat-card-content>
        </mat-card>
      }

      @if (!loading() && sandboxes().length > 0) {
        <mat-card>
          <table mat-table [dataSource]="sandboxes()" class="sandbox-table">
            <ng-container matColumnDef="user_id">
              <th mat-header-cell *matHeaderCellDef>Usuario</th>
              <td mat-cell *matCellDef="let s">
                <div class="user-cell">
                  <mat-icon>person</mat-icon>
                  <span>{{ s.user_id }}</span>
                </div>
              </td>
            </ng-container>

            <ng-container matColumnDef="container_name">
              <th mat-header-cell *matHeaderCellDef>Contenedor</th>
              <td mat-cell *matCellDef="let s">
                <code>{{ s.container_name }}</code>
              </td>
            </ng-container>

            <ng-container matColumnDef="status">
              <th mat-header-cell *matHeaderCellDef>Estado</th>
              <td mat-cell *matCellDef="let s">
                <span class="status-chip" [class]="s.status">
                  <mat-icon>{{ statusIcon(s.status) }}</mat-icon>
                  {{ s.status }}
                </span>
              </td>
            </ng-container>

            <ng-container matColumnDef="last_accessed_at">
              <th mat-header-cell *matHeaderCellDef>Último acceso</th>
              <td mat-cell *matCellDef="let s">{{ formatDate(s.last_accessed_at) }}</td>
            </ng-container>

            <ng-container matColumnDef="created_at">
              <th mat-header-cell *matHeaderCellDef>Creado</th>
              <td mat-cell *matCellDef="let s">{{ formatDate(s.created_at) }}</td>
            </ng-container>

            <ng-container matColumnDef="actions">
              <th mat-header-cell *matHeaderCellDef>Acciones</th>
              <td mat-cell *matCellDef="let s">
                <button mat-icon-button color="warn" 
                        matTooltip="Eliminar sandbox" 
                        (click)="removeSandbox(s)">
                  <mat-icon>delete</mat-icon>
                </button>
              </td>
            </ng-container>

            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
          </table>
        </mat-card>
      }
    </div>
  `,
  styles: [`
    .sandboxes-page {
      max-width: 1200px;
      margin: 0 auto;
    }

    h1 {
      font-size: 28px;
      font-weight: 700;
      color: #1e293b;
      margin-bottom: 4px;
    }

    .subtitle {
      color: #64748b;
      margin-bottom: 24px;
      font-size: 15px;
    }

    .info-card {
      margin-bottom: 24px;
    }

    .info-row {
      display: flex;
      align-items: center;
      gap: 32px;
    }

    .stat {
      display: flex;
      flex-direction: column;
      align-items: center;
    }

    .stat-value {
      font-size: 28px;
      font-weight: 700;
      color: #1e293b;
    }

    .stat-value.running {
      color: #22c55e;
    }

    .stat-value.stopped {
      color: #94a3b8;
    }

    .stat-label {
      font-size: 13px;
      color: #64748b;
      margin-top: 2px;
    }

    .actions {
      margin-left: auto;
    }

    .loading {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 16px;
      padding: 48px;
      color: #64748b;
    }

    .empty-card {
      text-align: center;
      padding: 48px 24px;
    }

    .empty-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      color: #cbd5e1;
      margin-bottom: 16px;
    }

    .empty-card h3 {
      color: #475569;
      margin-bottom: 8px;
    }

    .empty-card p {
      color: #94a3b8;
      max-width: 500px;
      margin: 0 auto;
    }

    .sandbox-table {
      width: 100%;
    }

    .user-cell {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .user-cell mat-icon {
      font-size: 20px;
      width: 20px;
      height: 20px;
      color: #64748b;
    }

    code {
      background: #f1f5f9;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 13px;
      color: #475569;
    }

    .status-chip {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 4px 12px;
      border-radius: 20px;
      font-size: 13px;
      font-weight: 500;
    }

    .status-chip mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
    }

    .status-chip.running {
      background: rgba(34, 197, 94, 0.1);
      color: #16a34a;
    }

    .status-chip.stopped {
      background: rgba(148, 163, 184, 0.15);
      color: #64748b;
    }

    .status-chip.created {
      background: rgba(59, 130, 246, 0.1);
      color: #2563eb;
    }
  `],
})
export class SandboxesComponent implements OnInit {
  private api = environment.apiUrl;

  sandboxes = signal<Sandbox[]>([]);
  loading = signal(false);
  displayedColumns = ['user_id', 'container_name', 'status', 'last_accessed_at', 'created_at', 'actions'];

  runningCount = signal(0);
  stoppedCount = signal(0);

  constructor(
    private http: HttpClient,
    private snackBar: MatSnackBar,
  ) {}

  ngOnInit(): void {
    this.loadSandboxes();
  }

  loadSandboxes(): void {
    this.loading.set(true);
    this.http.get<{ sandboxes: Sandbox[] }>(`${this.api}/workspace/sandboxes`).subscribe({
      next: (res) => {
        this.sandboxes.set(res.sandboxes);
        this.runningCount.set(res.sandboxes.filter(s => s.status === 'running').length);
        this.stoppedCount.set(res.sandboxes.filter(s => s.status !== 'running').length);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.snackBar.open('Error cargando sandboxes', 'OK', { duration: 3000 });
      },
    });
  }

  removeSandbox(sandbox: Sandbox): void {
    if (!confirm(`¿Eliminar el sandbox de ${sandbox.user_id}? Se perderán los datos del contenedor.`)) return;

    this.http.delete(`${this.api}/workspace/sandboxes/${encodeURIComponent(sandbox.user_id)}`).subscribe({
      next: () => {
        this.snackBar.open(`Sandbox de ${sandbox.user_id} eliminado`, 'OK', { duration: 3000 });
        this.loadSandboxes();
      },
      error: () => {
        this.snackBar.open('Error eliminando sandbox', 'OK', { duration: 3000 });
      },
    });
  }

  statusIcon(status: string): string {
    switch (status) {
      case 'running': return 'play_circle';
      case 'stopped': return 'stop_circle';
      default: return 'circle';
    }
  }

  formatDate(iso: string): string {
    if (!iso) return '-';
    return new Date(iso).toLocaleString('es-ES', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  }
}
