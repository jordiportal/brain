import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatBadgeModule } from '@angular/material/badge';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { ArtifactSidebarComponent } from './artifact-sidebar.component';
import { ArtifactViewerComponent } from '../artifact-viewer/artifact-viewer.component';
import { ArtifactService, Artifact } from '../../../core/services/artifact.service';

/**
 * Botón flotante para acceso rápido al sidebar de artefactos
 * Se puede usar desde cualquier página
 */
@Component({
  selector: 'app-artifact-fab',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatBadgeModule,
    MatTooltipModule,
    ArtifactSidebarComponent,
    ArtifactViewerComponent
  ],
  template: `
    <!-- Floating Action Button -->
    <div class="artifact-fab-container">
      <button 
        mat-fab 
        color="primary"
        (click)="toggleSidebar()"
        [matBadge]="artifactCount"
        matBadgeColor="accent"
        matBadgeSize="medium"
        [matBadgeHidden]="artifactCount === 0"
        matTooltip="Ver artefactos generados"
        matTooltipPosition="left">
        <mat-icon>folder_special</mat-icon>
      </button>
    </div>

    <!-- Artifact Sidebar -->
    <app-artifact-sidebar
      *ngIf="sidebarVisible"
      [isExpanded]="true"
      [conversationId]="conversationId"
      (artifactSelected)="onArtifactSelected($event)"
      (previewRequested)="onPreviewRequested($event)"
      (expandChanged)="sidebarVisible = $event">
    </app-artifact-sidebar>

    <!-- Artifact Viewer Modal -->
    <app-artifact-viewer
      *ngIf="selectedArtifact"
      [artifact]="selectedArtifact"
      (closed)="selectedArtifact = undefined"
      (downloadRequested)="onDownload($event)">
    </app-artifact-viewer>
  `,
  styles: [`
    .artifact-fab-container {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 100;
    }

    ::ng-deep app-artifact-sidebar {
      position: fixed;
      top: 64px; /* Height of toolbar */
      right: 0;
      bottom: 0;
      z-index: 50;
      height: calc(100vh - 64px);
    }

    ::ng-deep app-artifact-sidebar .artifact-sidebar {
      height: 100%;
      box-shadow: -2px 0 8px rgba(0,0,0,0.1);
    }
  `]
})
export class ArtifactFabComponent implements OnInit, OnDestroy {
  sidebarVisible = false;
  artifactCount = 0;
  selectedArtifact?: Artifact;
  conversationId?: string;
  
  private destroy$ = new Subject<void>();

  constructor(private artifactService: ArtifactService) {}

  ngOnInit(): void {
    this.loadArtifactCount();
    
    // Escuchar cambios en la lista de artefactos
    this.artifactService.artifacts$
      .pipe(takeUntil(this.destroy$))
      .subscribe(artifacts => {
        this.artifactCount = artifacts.length;
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadArtifactCount(): void {
    const request = this.conversationId
      ? this.artifactService.getConversationArtifacts(this.conversationId, undefined, 1)
      : this.artifactService.getRecentArtifacts(1);

    request
      .pipe(takeUntil(this.destroy$))
      .subscribe(response => {
        this.artifactCount = response.total;
      });
  }

  toggleSidebar(): void {
    this.sidebarVisible = !this.sidebarVisible;
  }

  onArtifactSelected(artifact: Artifact): void {
    this.selectedArtifact = artifact;
  }

  onPreviewRequested(artifact: Artifact): void {
    this.selectedArtifact = artifact;
  }

  onDownload(artifact: Artifact): void {
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
}
