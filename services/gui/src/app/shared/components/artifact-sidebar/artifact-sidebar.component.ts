import { Component, OnInit, OnDestroy, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatBadgeModule } from '@angular/material/badge';
import { MatMenuModule } from '@angular/material/menu';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { ArtifactService, Artifact } from '../../../core/services/artifact.service';

@Component({
  selector: 'app-artifact-sidebar',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatSelectModule,
    MatFormFieldModule,
    MatBadgeModule,
    MatMenuModule
  ],
  template: `
    <div class="artifact-sidebar" [class.expanded]="isExpanded">
      <!-- Header -->
      <div class="sidebar-header">
        <div class="header-title">
          <mat-icon>folder_special</mat-icon>
          <span>Artefactos</span>
          <mat-chip *ngIf="artifacts.length > 0" class="count-chip">
            {{ artifacts.length }}
          </mat-chip>
        </div>
        <div class="header-actions">
          <button 
            mat-icon-button 
            (click)="refreshArtifacts()"
            [disabled]="loading"
            matTooltip="Refrescar">
            <mat-icon *ngIf="!loading">refresh</mat-icon>
            <mat-spinner *ngIf="loading" diameter="20"></mat-spinner>
          </button>
          <button 
            mat-icon-button 
            (click)="toggleExpanded()"
            matTooltip="{{ isExpanded ? 'Colapsar' : 'Expandir' }}">
            <mat-icon>{{ isExpanded ? 'chevron_right' : 'chevron_left' }}</mat-icon>
          </button>
        </div>
      </div>

      <!-- Filter -->
      <div class="filter-section" *ngIf="isExpanded">
        <mat-form-field appearance="outline" class="filter-field">
          <mat-label>Tipo</mat-label>
          <mat-select [(ngModel)]="selectedType" (selectionChange)="filterArtifacts()">
            <mat-option value="all">Todos</mat-option>
            <mat-option value="image">Imágenes</mat-option>
            <mat-option value="video">Videos</mat-option>
            <mat-option value="presentation">Presentaciones</mat-option>
            <mat-option value="document">Documentos</mat-option>
            <mat-option value="code">Código</mat-option>
          </mat-select>
        </mat-form-field>
      </div>

      <!-- Content -->
      <div class="sidebar-content" *ngIf="isExpanded">
        <!-- Empty State -->
        <div class="empty-state" *ngIf="filteredArtifacts.length === 0 && !loading">
          <mat-icon>folder_open</mat-icon>
          <p>No hay artefactos</p>
          <span class="hint">Los archivos generados aparecerán aquí</span>
        </div>

        <!-- Loading -->
        <div class="loading-state" *ngIf="loading">
          <mat-spinner diameter="40"></mat-spinner>
          <p>Cargando artefactos...</p>
        </div>

        <!-- Artifacts List -->
        <div class="artifacts-list" *ngIf="filteredArtifacts.length > 0 && !loading">
          <div 
            class="artifact-item"
            *ngFor="let artifact of filteredArtifacts"
            [class.selected]="selectedArtifact?.artifact_id === artifact.artifact_id"
            (click)="selectArtifact(artifact)">
            
            <!-- Icon -->
            <div class="artifact-icon" [class]="artifact.type">
              <mat-icon>{{ getIcon(artifact.type) }}</mat-icon>
            </div>

            <!-- Info -->
            <div class="artifact-info">
              <div class="artifact-title" [title]="artifact.title || artifact.file_name">
                {{ artifact.title || artifact.file_name }}
              </div>
              <div class="artifact-meta">
                <span class="type-badge">{{ artifact.type }}</span>
                <span class="time">{{ formatDate(artifact.created_at) }}</span>
                <span class="size" *ngIf="artifact.file_size">{{ formatSize(artifact.file_size) }}</span>
              </div>
            </div>

            <!-- Actions -->
            <div class="artifact-actions">
              <button 
                mat-icon-button 
                (click)="previewArtifact(artifact, $event)"
                matTooltip="Vista previa">
                <mat-icon>visibility</mat-icon>
              </button>
              <button 
                mat-icon-button 
                [matMenuTriggerFor]="menu"
                matTooltip="Más opciones">
                <mat-icon>more_vert</mat-icon>
              </button>
              <mat-menu #menu="matMenu">
                <button mat-menu-item (click)="downloadArtifact(artifact)">
                  <mat-icon>download</mat-icon>
                  <span>Descargar</span>
                </button>
                <button mat-menu-item (click)="deleteArtifact(artifact)">
                  <mat-icon>delete</mat-icon>
                  <span>Eliminar</span>
                </button>
              </mat-menu>
            </div>
          </div>
        </div>
      </div>

      <!-- Collapsed View -->
      <div class="collapsed-view" *ngIf="!isExpanded">
        <div class="collapsed-icon" matBadge="{{ artifacts.length }}" matBadgeColor="primary">
          <mat-icon>folder_special</mat-icon>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .artifact-sidebar {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: #fafafa;
      border-left: 1px solid #e0e0e0;
      transition: width 0.3s ease;
      width: 60px;
    }

    .artifact-sidebar.expanded {
      width: 320px;
    }

    .sidebar-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 16px;
      border-bottom: 1px solid #e0e0e0;
      background: white;
    }

    .header-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 500;
      color: #333;
    }

    .header-title mat-icon {
      color: #2196f3;
    }

    .count-chip {
      font-size: 11px;
      height: 20px;
      background: #e3f2fd;
      color: #1976d2;
    }

    .header-actions {
      display: flex;
      gap: 4px;
    }

    .filter-section {
      padding: 12px 16px;
      border-bottom: 1px solid #e0e0e0;
    }

    .filter-field {
      width: 100%;
    }

    .sidebar-content {
      flex: 1;
      overflow-y: auto;
      padding: 8px;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 40px 20px;
      text-align: center;
      color: #999;
    }

    .empty-state mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      margin-bottom: 16px;
      color: #ddd;
    }

    .hint {
      font-size: 12px;
      margin-top: 8px;
    }

    .loading-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 40px 20px;
    }

    .artifacts-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .artifact-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px;
      border-radius: 8px;
      cursor: pointer;
      transition: background 0.2s;
      background: white;
      border: 1px solid transparent;
    }

    .artifact-item:hover {
      background: #f5f5f5;
    }

    .artifact-item.selected {
      border-color: #2196f3;
      background: #e3f2fd;
    }

    .artifact-icon {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 40px;
      height: 40px;
      border-radius: 8px;
      background: #f0f0f0;
    }

    .artifact-icon.image { background: #e3f2fd; color: #1976d2; }
    .artifact-icon.video { background: #fce4ec; color: #c2185b; }
    .artifact-icon.presentation { background: #f3e5f5; color: #7b1fa2; }
    .artifact-icon.document { background: #e8f5e9; color: #388e3c; }
    .artifact-icon.code { background: #fff3e0; color: #f57c00; }

    .artifact-info {
      flex: 1;
      min-width: 0;
    }

    .artifact-title {
      font-weight: 500;
      font-size: 13px;
      color: #333;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      margin-bottom: 4px;
    }

    .artifact-meta {
      display: flex;
      gap: 8px;
      align-items: center;
      font-size: 11px;
      color: #666;
    }

    .type-badge {
      text-transform: uppercase;
      font-size: 10px;
      font-weight: 600;
      padding: 2px 6px;
      border-radius: 4px;
      background: #f0f0f0;
    }

    .artifact-actions {
      display: flex;
      opacity: 0;
      transition: opacity 0.2s;
    }

    .artifact-item:hover .artifact-actions {
      opacity: 1;
    }

    .collapsed-view {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 16px 0;
    }

    .collapsed-icon {
      color: #666;
    }
  `]
})
export class ArtifactSidebarComponent implements OnInit, OnDestroy {
  @Input() conversationId?: string;
  @Input() isExpanded = true;
  @Output() artifactSelected = new EventEmitter<Artifact>();
  @Output() previewRequested = new EventEmitter<Artifact>();
  @Output() expandChanged = new EventEmitter<boolean>();

  artifacts: Artifact[] = [];
  filteredArtifacts: Artifact[] = [];
  selectedArtifact: Artifact | null = null;
  selectedType = 'all';
  loading = false;
  
  private destroy$ = new Subject<void>();

  constructor(private artifactService: ArtifactService) {}

  ngOnInit(): void {
    this.loadArtifacts();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadArtifacts(): void {
    this.loading = true;
    
    const request = this.conversationId 
      ? this.artifactService.getConversationArtifacts(this.conversationId)
      : this.artifactService.getRecentArtifacts(50);

    request
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          this.artifacts = response.artifacts;
          this.filterArtifacts();
          this.loading = false;
        },
        error: (err) => {
          console.error('Error loading artifacts:', err);
          this.loading = false;
        }
      });
  }

  refreshArtifacts(): void {
    this.loadArtifacts();
  }

  filterArtifacts(): void {
    this.filteredArtifacts = this.selectedType === 'all'
      ? this.artifacts
      : this.artifacts.filter(a => a.type === this.selectedType);
  }

  selectArtifact(artifact: Artifact): void {
    this.selectedArtifact = artifact;
    this.artifactSelected.emit(artifact);
  }

  previewArtifact(artifact: Artifact, event: Event): void {
    event.stopPropagation();
    this.previewRequested.emit(artifact);
  }

  downloadArtifact(artifact: Artifact): void {
    this.artifactService.downloadArtifact(artifact.artifact_id)
      .subscribe(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = artifact.file_name;
        a.click();
        window.URL.revokeObjectURL(url);
      });
  }

  deleteArtifact(artifact: Artifact): void {
    if (confirm(`¿Eliminar "${artifact.title || artifact.file_name}"?`)) {
      this.artifactService.deleteArtifact(artifact.artifact_id)
        .subscribe(() => {
          this.artifacts = this.artifacts.filter(a => a.artifact_id !== artifact.artifact_id);
          this.filterArtifacts();
        });
    }
  }

  toggleExpanded(): void {
    this.isExpanded = !this.isExpanded;
    this.expandChanged.emit(this.isExpanded);
  }

  getIcon(type: string): string {
    return this.artifactService.getIconForType(type as any);
  }

  formatDate(date: string): string {
    return this.artifactService.formatDate(date);
  }

  formatSize(bytes?: number): string {
    return this.artifactService.formatFileSize(bytes);
  }
}
