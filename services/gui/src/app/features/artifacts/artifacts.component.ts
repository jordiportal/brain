import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatSortModule } from '@angular/material/sort';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatMenuModule } from '@angular/material/menu';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDividerModule } from '@angular/material/divider';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { ArtifactService, Artifact, ArtifactListResponse } from '../../core/services/artifact.service';
import { ArtifactViewerComponent } from '../../shared/components/artifact-viewer/artifact-viewer.component';

@Component({
  selector: 'app-artifacts',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    MatInputModule,
    MatFormFieldModule,
    MatSelectModule,
    MatMenuModule,
    MatDialogModule,
    MatTooltipModule,
    MatSnackBarModule,
    MatDividerModule,
    ArtifactViewerComponent
  ],
  template: `
    <div class="artifacts-page">
      <!-- Header -->
      <div class="page-header">
        <div class="header-title">
          <mat-icon>folder_special</mat-icon>
          <div class="title-text">
            <h1>Artefactos</h1>
            <p class="subtitle">Gestión de archivos generados por agentes y herramientas</p>
          </div>
        </div>
        <div class="header-actions">
          <button mat-raised-button color="primary" (click)="refreshArtifacts()" [disabled]="loading">
            <mat-icon *ngIf="!loading">refresh</mat-icon>
            <mat-spinner *ngIf="loading" diameter="20"></mat-spinner>
            Refrescar
          </button>
        </div>
      </div>

      <!-- Filters -->
      <mat-card class="filters-card">
        <mat-card-content>
          <div class="filters-row">
            <mat-form-field appearance="outline" class="filter-field">
              <mat-label>Tipo</mat-label>
              <mat-select [(ngModel)]="selectedType" (selectionChange)="applyFilters()">
                <mat-option value="all">Todos</mat-option>
                <mat-option value="image">Imágenes</mat-option>
                <mat-option value="video">Videos</mat-option>
                <mat-option value="presentation">Presentaciones</mat-option>
                <mat-option value="spreadsheet">Hojas de cálculo</mat-option>
                <mat-option value="document">Documentos</mat-option>
                <mat-option value="code">Código</mat-option>
                <mat-option value="html">HTML</mat-option>
              </mat-select>
            </mat-form-field>

            <mat-form-field appearance="outline" class="filter-field search-field">
              <mat-label>Buscar</mat-label>
              <input matInput [(ngModel)]="searchQuery" placeholder="Nombre o descripción..." (keyup.enter)="applyFilters()">
              <button mat-icon-button matSuffix (click)="applyFilters()">
                <mat-icon>search</mat-icon>
              </button>
            </mat-form-field>

            <div class="stats">
              <span class="stat-item">
                <strong>{{ totalArtifacts }}</strong> artefactos
              </span>
            </div>
          </div>
        </mat-card-content>
      </mat-card>

      <!-- Loading -->
      <div class="loading-container" *ngIf="loading && !artifacts.length">
        <mat-spinner diameter="50"></mat-spinner>
        <p>Cargando artefactos...</p>
      </div>

      <!-- Empty State -->
      <div class="empty-state" *ngIf="!loading && !artifacts.length">
        <mat-icon>folder_open</mat-icon>
        <h2>No hay artefactos</h2>
        <p>Aún no se han generado artefactos. Los archivos creados por los agentes aparecerán aquí.</p>
      </div>

      <!-- Artifacts Table -->
      <mat-card class="table-card" *ngIf="!loading && artifacts.length">
        <table mat-table [dataSource]="artifacts" class="artifacts-table" matSort>
          <!-- Icon Column -->
          <ng-container matColumnDef="icon">
            <th mat-header-cell *matHeaderCellDef></th>
            <td mat-cell *matCellDef="let artifact">
              <div class="artifact-icon" [class]="artifact.type">
                <mat-icon>{{ getIcon(artifact.type) }}</mat-icon>
              </div>
            </td>
          </ng-container>

          <!-- Name Column -->
          <ng-container matColumnDef="name">
            <th mat-header-cell *matHeaderCellDef mat-sort-header>Nombre</th>
            <td mat-cell *matCellDef="let artifact">
              <div class="artifact-name">
                <span class="name-text">{{ artifact.title || artifact.file_name }}</span>
                <span class="type-badge">{{ artifact.type }}</span>
              </div>
              <div class="artifact-description" *ngIf="artifact.description">
                {{ artifact.description }}
              </div>
            </td>
          </ng-container>

          <!-- Type Column -->
          <ng-container matColumnDef="type">
            <th mat-header-cell *matHeaderCellDef mat-sort-header>Tipo</th>
            <td mat-cell *matCellDef="let artifact">
              <mat-chip-listbox>
                <mat-chip-option [class]="artifact.type">{{ artifact.type }}</mat-chip-option>
              </mat-chip-listbox>
            </td>
          </ng-container>

          <!-- Size Column -->
          <ng-container matColumnDef="size">
            <th mat-header-cell *matHeaderCellDef mat-sort-header>Tamaño</th>
            <td mat-cell *matCellDef="let artifact">
              {{ formatSize(artifact.file_size) }}
            </td>
          </ng-container>

          <!-- Created Column -->
          <ng-container matColumnDef="created">
            <th mat-header-cell *matHeaderCellDef mat-sort-header>Fecha</th>
            <td mat-cell *matCellDef="let artifact">
              {{ formatDate(artifact.created_at) }}
            </td>
          </ng-container>

          <!-- Agent Column -->
          <ng-container matColumnDef="agent">
            <th mat-header-cell *matHeaderCellDef>Agente</th>
            <td mat-cell *matCellDef="let artifact">
              <span class="agent-tag" *ngIf="artifact.agent_id">{{ artifact.agent_id }}</span>
              <span class="tool-tag" *ngIf="artifact.tool_id">{{ artifact.tool_id }}</span>
            </td>
          </ng-container>

          <!-- Actions Column -->
          <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef>Acciones</th>
            <td mat-cell *matCellDef="let artifact">
              <button mat-icon-button [matMenuTriggerFor]="menu" matTooltip="Más opciones">
                <mat-icon>more_vert</mat-icon>
              </button>
              <mat-menu #menu="matMenu">
                <button mat-menu-item (click)="previewArtifact(artifact)">
                  <mat-icon>visibility</mat-icon>
                  <span>Ver</span>
                </button>
                <button mat-menu-item (click)="copyArtifactId(artifact)">
                  <mat-icon>content_copy</mat-icon>
                  <span>Copiar ID</span>
                </button>
                <button mat-menu-item (click)="downloadArtifact(artifact)">
                  <mat-icon>download</mat-icon>
                  <span>Descargar</span>
                </button>
                <mat-divider></mat-divider>
                <button mat-menu-item (click)="deleteArtifact(artifact)" class="delete-option">
                  <mat-icon color="warn">delete</mat-icon>
                  <span>Eliminar</span>
                </button>
              </mat-menu>
            </td>
          </ng-container>

          <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
          <tr mat-row *matRowDef="let row; columns: displayedColumns;" (click)="previewArtifact(row)" class="artifact-row"></tr>
        </table>

        <mat-paginator
          [pageSizeOptions]="[10, 25, 50, 100]"
          [pageSize]="pageSize"
          [length]="totalArtifacts"
          (page)="onPageChange($event)">
        </mat-paginator>
      </mat-card>
    </div>

    <!-- Artifact Viewer Modal -->
    <app-artifact-viewer
      *ngIf="selectedArtifact"
      [artifact]="selectedArtifact"
      (closed)="selectedArtifact = undefined"
      (downloadRequested)="onDownload($event)">
    </app-artifact-viewer>
  `,
  styles: [`
    .artifacts-page {
      padding: 24px;
      max-width: 1400px;
      margin: 0 auto;
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 24px;
    }

    .header-title {
      display: flex;
      gap: 16px;
      align-items: flex-start;
    }

    .header-title mat-icon {
      font-size: 40px;
      width: 40px;
      height: 40px;
      color: #2196f3;
    }

    .title-text h1 {
      margin: 0 0 4px 0;
      font-size: 28px;
      font-weight: 600;
      color: #1a1a2e;
    }

    .subtitle {
      color: #666;
      margin: 0;
      font-size: 14px;
    }

    .filters-card {
      margin-bottom: 24px;
    }

    .filters-row {
      display: flex;
      gap: 16px;
      align-items: center;
      flex-wrap: wrap;
    }

    .filter-field {
      min-width: 150px;
    }

    .search-field {
      flex: 1;
      min-width: 200px;
    }

    .stats {
      margin-left: auto;
    }

    .stat-item {
      font-size: 14px;
      color: #666;
    }

    .loading-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 60px;
      color: #666;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 80px 20px;
      text-align: center;
      color: #999;
    }

    .empty-state mat-icon {
      font-size: 80px;
      width: 80px;
      height: 80px;
      margin-bottom: 24px;
      color: #ddd;
    }

    .empty-state h2 {
      margin: 0 0 8px 0;
      color: #666;
    }

    .table-card {
      overflow: hidden;
    }

    .artifacts-table {
      width: 100%;
    }

    .artifact-icon {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 40px;
      height: 40px;
      border-radius: 8px;
      background: #f5f5f5;
    }

    .artifact-icon.image { background: #e3f2fd; color: #1976d2; }
    .artifact-icon.video { background: #fce4ec; color: #c2185b; }
    .artifact-icon.presentation { background: #f3e5f5; color: #7b1fa2; }
    .artifact-icon.document { background: #e8f5e9; color: #388e3c; }
    .artifact-icon.code { background: #fff3e0; color: #f57c00; }
    .artifact-icon.html { background: #e0f2f1; color: #00796b; }

    .artifact-name {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .name-text {
      font-weight: 500;
      color: #333;
    }

    .type-badge {
      font-size: 11px;
      color: #666;
      text-transform: uppercase;
    }

    .artifact-description {
      font-size: 12px;
      color: #888;
      max-width: 300px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .artifact-row {
      cursor: pointer;
      transition: background 0.2s;
    }

    .artifact-row:hover {
      background: #f5f5f5;
    }

    .agent-tag, .tool-tag {
      display: inline-block;
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 4px;
      background: #f0f0f0;
      margin-right: 4px;
    }

    .delete-option {
      color: #d32f2f;
    }
  `]
})
export class ArtifactsComponent implements OnInit, OnDestroy {
  artifacts: Artifact[] = [];
  selectedArtifact?: Artifact;
  loading = false;
  
  // Filters
  selectedType = 'all';
  searchQuery = '';
  
  // Pagination
  totalArtifacts = 0;
  pageSize = 25;
  currentPage = 0;
  
  displayedColumns = ['icon', 'name', 'type', 'size', 'created', 'agent', 'actions'];
  
  private destroy$ = new Subject<void>();

  constructor(
    private artifactService: ArtifactService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    console.log('🔍 ArtifactsComponent initialized');
    console.log('🔍 API URL:', this.artifactService['apiUrl']);
    this.loadArtifacts();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadArtifacts(): void {
    this.loading = true;
    
    const artifactType = this.selectedType === 'all' ? undefined : this.selectedType as any;
    
    this.artifactService.listArtifacts(
      undefined,
      artifactType,
      undefined,
      this.pageSize,
      this.currentPage * this.pageSize
    )
    .pipe(takeUntil(this.destroy$))
    .subscribe({
      next: (response: ArtifactListResponse) => {
        console.log('🔍 ArtifactsComponent - Got response:', JSON.stringify(response, null, 2));
        console.log('🔍 ArtifactsComponent - artifacts array:', response.artifacts);
        console.log('🔍 ArtifactsComponent - total:', response.total);
        this.artifacts = response.artifacts;
        this.totalArtifacts = response.total;
        this.loading = false;
      },
      error: (err) => {
        console.error('Error loading artifacts:', err);
        this.snackBar.open('Error cargando artefactos', 'Cerrar', { duration: 3000 });
        this.loading = false;
      }
    });
  }

  applyFilters(): void {
    this.currentPage = 0;
    this.loadArtifacts();
  }

  onPageChange(event: any): void {
    this.currentPage = event.pageIndex;
    this.pageSize = event.pageSize;
    this.loadArtifacts();
  }

  refreshArtifacts(): void {
    this.loadArtifacts();
    this.snackBar.open('Artefactos actualizados', 'Cerrar', { duration: 2000 });
  }

  previewArtifact(artifact: Artifact): void {
    this.selectedArtifact = artifact;
  }

  downloadArtifact(artifact: Artifact): void {
    this.artifactService.downloadArtifact(artifact.artifact_id)
      .pipe(takeUntil(this.destroy$))
      .subscribe(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = artifact.file_name;
        a.click();
        window.URL.revokeObjectURL(url);
        
        this.snackBar.open('Descarga iniciada', 'Cerrar', { duration: 2000 });
      });
  }

  deleteArtifact(artifact: Artifact): void {
    if (confirm(`¿Eliminar "${artifact.title || artifact.file_name}"?`)) {
      this.artifactService.deleteArtifact(artifact.artifact_id)
        .pipe(takeUntil(this.destroy$))
        .subscribe(() => {
          this.artifacts = this.artifacts.filter(a => a.artifact_id !== artifact.artifact_id);
          this.totalArtifacts--;
          this.snackBar.open('Artefacto eliminado', 'Cerrar', { duration: 2000 });
        });
    }
  }

  copyArtifactId(artifact: Artifact): void {
    if (artifact?.artifact_id) {
      navigator.clipboard.writeText(`@${artifact.artifact_id}`)
        .then(() => {
          this.snackBar.open(`ID copiado: @${artifact.artifact_id}`, 'Cerrar', {
            duration: 3000,
            horizontalPosition: 'center',
            verticalPosition: 'bottom'
          });
        })
        .catch(err => {
          console.error('Error al copiar:', err);
          this.snackBar.open('Error al copiar ID', 'Cerrar', { duration: 3000 });
        });
    }
  }

  onDownload(artifact: Artifact): void {
    this.downloadArtifact(artifact);
  }

  getIcon(type: string): string {
    return this.artifactService.getIconForType(type as any);
  }

  formatSize(bytes?: number): string {
    return this.artifactService.formatFileSize(bytes);
  }

  formatDate(date: string): string {
    return this.artifactService.formatDate(date);
  }
}
