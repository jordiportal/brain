import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { MatIconModule } from '@angular/material/icon';
import { environment } from '../../../../environments/environment';

/**
 * SpreadsheetViewerComponent - Visualizador de Excel via iframe.
 *
 * Carga el endpoint /api/v1/artifacts/{id}/view del backend que genera
 * un HTML standalone con Syncfusion Spreadsheet via CDN.
 * El iframe asegura aislamiento CSS total respecto a Angular Material.
 */
@Component({
  selector: 'app-spreadsheet-viewer',
  standalone: true,
  imports: [CommonModule, MatIconModule],
  template: `
    <div class="spreadsheet-iframe-wrapper" *ngIf="iframeUrl && !error">
      <iframe
        [src]="iframeUrl"
        frameborder="0"
        allowfullscreen
        title="Excel Viewer">
      </iframe>
    </div>

    <div class="spreadsheet-error" *ngIf="error">
      <mat-icon>error_outline</mat-icon>
      <p>{{ error }}</p>
    </div>
  `,
  styles: [`
    :host {
      display: block;
      width: 100%;
      height: 100%;
    }

    .spreadsheet-iframe-wrapper {
      width: 100%;
      height: 100%;
      min-height: 600px;
    }

    .spreadsheet-iframe-wrapper iframe {
      width: 100%;
      height: 100%;
      min-height: 600px;
      border: none;
    }

    .spreadsheet-error {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 400px;
      color: #d32f2f;
      gap: 12px;
    }

    .spreadsheet-error mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
    }
  `]
})
export class SpreadsheetViewerComponent implements OnChanges {
  @Input() artifactId!: string;
  @Input() fileName?: string;

  iframeUrl: SafeResourceUrl | null = null;
  error: string | null = null;

  constructor(private sanitizer: DomSanitizer) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['artifactId'] && this.artifactId) {
      this.error = null;
      const viewUrl = `${environment.apiUrl}/artifacts/${this.artifactId}/view`;
      this.iframeUrl = this.sanitizer.bypassSecurityTrustResourceUrl(viewUrl);
    }
  }
}
