import { Component, OnInit, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { ArtifactService, Artifact } from '../../../core/services/artifact.service';

@Component({
  selector: 'app-artifact-viewer',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatChipsModule
  ],
  template: `
    <div class="artifact-viewer-overlay" *ngIf="artifact" (click)="onOverlayClick($event)">
      <div class="viewer-container">
        <!-- Header -->
        <div class="viewer-header">
          <div class="header-info">
            <mat-icon>{{ getIcon() }}</mat-icon>
            <div class="title-section">
              <h3>{{ artifact.title || artifact.file_name }}</h3>
              <div class="meta-info">
                <mat-chip>{{ artifact.type }}</mat-chip>
                <span class="date">{{ formatDate(artifact.created_at) }}</span>
                <span class="size" *ngIf="artifact.file_size">{{ formatSize(artifact.file_size) }}</span>
              </div>
            </div>
          </div>
          <div class="header-actions">
            <button mat-icon-button (click)="download()" matTooltip="Descargar">
              <mat-icon>download</mat-icon>
            </button>
            <button mat-icon-button (click)="close()" matTooltip="Cerrar">
              <mat-icon>close</mat-icon>
            </button>
          </div>
        </div>

        <!-- Content -->
        <div class="viewer-content">
          <!-- Loading -->
          <div class="loading-container" *ngIf="loading">
            <mat-spinner diameter="50"></mat-spinner>
            <p>Cargando...</p>
          </div>

          <!-- Image -->
          <div class="image-container" *ngIf="artifact.type === 'image' && !loading">
            <img [src]="contentUrl" [alt]="artifact.title || artifact.file_name" />
          </div>

          <!-- Video -->
          <div class="video-container" *ngIf="artifact.type === 'video' && !loading">
            <video controls [src]="contentUrl">
              Tu navegador no soporta el formato de video.
            </video>
          </div>

          <!-- HTML/Presentation (Sandboxed) -->
          <div class="html-container" *ngIf="(artifact.type === 'html' || artifact.type === 'presentation') && !loading">
            <iframe 
              [src]="safeViewerUrl"
              sandbox="allow-scripts allow-same-origin"
              frameborder="0"
              title="{{ artifact.title || artifact.file_name }}">
            </iframe>
          </div>

          <!-- Document/Code (Preview) -->
          <div class="document-container" *ngIf="(artifact.type === 'document' || artifact.type === 'code' || artifact.type === 'file') && !loading">
            <div class="preview-not-available">
              <mat-icon>description</mat-icon>
              <p>Vista previa no disponible para este tipo de archivo</p>
              <button mat-raised-button color="primary" (click)="download()">
                <mat-icon>download</mat-icon>
                Descargar archivo
              </button>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="viewer-footer" *ngIf="artifact.metadata && hasMetadata()">
          <div class="metadata-grid">
            <div class="metadata-item" *ngIf="artifact.metadata.width">
              <span class="label">Ancho:</span>
              <span class="value">{{ artifact.metadata.width }}px</span>
            </div>
            <div class="metadata-item" *ngIf="artifact.metadata.height">
              <span class="label">Alto:</span>
              <span class="value">{{ artifact.metadata.height }}px</span>
            </div>
            <div class="metadata-item" *ngIf="artifact.metadata.duration">
              <span class="label">Duración:</span>
              <span class="value">{{ formatDuration(artifact.metadata.duration) }}</span>
            </div>
            <div class="metadata-item" *ngIf="artifact.metadata.provider">
              <span class="label">Proveedor:</span>
              <span class="value">{{ artifact.metadata.provider }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .artifact-viewer-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.85);
      z-index: 1000;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 40px;
    }

    .viewer-container {
      display: flex;
      flex-direction: column;
      width: 100%;
      max-width: 1000px;
      max-height: 90vh;
      background: white;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
    }

    .viewer-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 20px;
      background: #f8f9fa;
      border-bottom: 1px solid #e0e0e0;
    }

    .header-info {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .header-info mat-icon {
      font-size: 32px;
      width: 32px;
      height: 32px;
      color: #2196f3;
    }

    .title-section h3 {
      margin: 0 0 4px 0;
      font-size: 16px;
      font-weight: 500;
      color: #333;
    }

    .meta-info {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: #666;
    }

    .meta-info mat-chip {
      font-size: 11px;
      height: 20px;
      padding: 4px 8px;
    }

    .header-actions {
      display: flex;
      gap: 8px;
    }

    .viewer-content {
      flex: 1;
      overflow: auto;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 400px;
      max-height: 60vh;
      background: #f0f0f0;
    }

    .loading-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
      color: #666;
    }

    .image-container {
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }

    .image-container img {
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }

    .video-container {
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }

    .video-container video {
      max-width: 100%;
      max-height: 100%;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }

    .html-container {
      width: 100%;
      height: 100%;
      min-height: 500px;
    }

    .html-container iframe {
      width: 100%;
      height: 100%;
      min-height: 500px;
      border: none;
    }

    .document-container {
      padding: 40px;
      text-align: center;
    }

    .preview-not-available {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
      color: #666;
    }

    .preview-not-available mat-icon {
      font-size: 64px;
      width: 64px;
      height: 64px;
      color: #ddd;
    }

    .viewer-footer {
      padding: 12px 20px;
      background: #f8f9fa;
      border-top: 1px solid #e0e0e0;
    }

    .metadata-grid {
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
    }

    .metadata-item {
      display: flex;
      gap: 4px;
      font-size: 13px;
    }

    .metadata-item .label {
      color: #666;
    }

    .metadata-item .value {
      color: #333;
      font-weight: 500;
    }
  `]
})
export class ArtifactViewerComponent implements OnInit {
  @Input() artifact?: Artifact;
  @Output() closed = new EventEmitter<void>();
  @Output() downloadRequested = new EventEmitter<Artifact>();

  contentUrl: string = '';
  safeViewerUrl?: SafeResourceUrl;
  loading = true;

  constructor(
    private artifactService: ArtifactService,
    private sanitizer: DomSanitizer
  ) {}

  ngOnInit(): void {
    if (this.artifact) {
      this.loadContent();
    }
  }

  loadContent(): void {
    if (!this.artifact) return;

    this.loading = true;

    // Para imágenes y videos, usar URL directa
    if (this.artifact.type === 'image' || this.artifact.type === 'video') {
      this.contentUrl = this.artifactService.getContentUrl(this.artifact.artifact_id);
      this.loading = false;
    }
    // Para HTML/presentaciones, usar viewer sandboxed
    else if (this.artifact.type === 'html' || this.artifact.type === 'presentation') {
      const viewerUrl = this.artifactService.getViewerUrl(this.artifact.artifact_id);
      this.safeViewerUrl = this.sanitizer.bypassSecurityTrustResourceUrl(viewerUrl);
      this.loading = false;
    }
    // Para otros, no hay preview directa
    else {
      this.loading = false;
    }
  }

  close(): void {
    this.closed.emit();
  }

  download(): void {
    if (this.artifact) {
      this.downloadRequested.emit(this.artifact);
    }
  }

  onOverlayClick(event: Event): void {
    // Cerrar si se hace click en el overlay (fuera del contenido)
    if (event.target === event.currentTarget) {
      this.close();
    }
  }

  getIcon(): string {
    if (!this.artifact) return 'insert_drive_file';
    return this.artifactService.getIconForType(this.artifact.type);
  }

  formatDate(date: string): string {
    return this.artifactService.formatDate(date);
  }

  formatSize(bytes?: number): string {
    return this.artifactService.formatFileSize(bytes);
  }

  formatDuration(seconds?: number): string {
    if (!seconds) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  hasMetadata(): boolean {
    if (!this.artifact?.metadata) return false;
    const m = this.artifact.metadata;
    return !!(m.width || m.height || m.duration || m.provider);
  }
}
