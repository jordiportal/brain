import {
  Component, Input, ViewChild, ViewEncapsulation,
  OnInit, OnDestroy, OnChanges, SimpleChanges
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import {
  SpreadsheetModule,
  SpreadsheetComponent
} from '@syncfusion/ej2-angular-spreadsheet';

// Syncfusion CSS - same pattern as fuse-lowcode
import '@syncfusion/ej2-base/styles/material.css';
import '@syncfusion/ej2-inputs/styles/material.css';
import '@syncfusion/ej2-buttons/styles/material.css';
import '@syncfusion/ej2-splitbuttons/styles/material.css';
import '@syncfusion/ej2-lists/styles/material.css';
import '@syncfusion/ej2-navigations/styles/material.css';
import '@syncfusion/ej2-popups/styles/material.css';
import '@syncfusion/ej2-dropdowns/styles/material.css';
import '@syncfusion/ej2-grids/styles/material.css';
import '@syncfusion/ej2-spreadsheet/styles/material.css';

import { environment } from '../../../../environments/environment';

@Component({
  selector: 'app-spreadsheet-viewer',
  standalone: true,
  encapsulation: ViewEncapsulation.None, // Required for Syncfusion styles
  imports: [CommonModule, SpreadsheetModule, MatIconModule],
  template: `
    <div class="sf-scope" *ngIf="!loading && !error">
      <ejs-spreadsheet
        #spreadsheet
        [showRibbon]="true"
        [showFormulaBar]="true"
        [showSheetTabs]="true"
        [allowOpen]="true"
        [allowSave]="false"
        [allowEditing]="true"
        [allowSorting]="true"
        [allowFiltering]="true"
        [allowResizing]="true"
        height="600px"
        width="100%"
        (created)="onSpreadsheetCreated()">
      </ejs-spreadsheet>
    </div>
    
    <div class="loading-state" *ngIf="loading">
      <mat-icon>table_chart</mat-icon>
      <p>Cargando hoja de cálculo...</p>
    </div>

    <div class="error-state" *ngIf="error">
      <mat-icon>error_outline</mat-icon>
      <p>{{ error }}</p>
    </div>
  `,
  styles: [`
    .sf-scope {
      width: 100%;
      height: 600px;
    }

    .loading-state, .error-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 400px;
      color: #666;
      gap: 12px;
    }

    .loading-state mat-icon, .error-state mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
    }

    .error-state {
      color: #d32f2f;
    }
  `]
})
export class SpreadsheetViewerComponent implements OnInit, OnChanges, OnDestroy {
  @Input() artifactId!: string;
  @Input() fileName?: string;

  @ViewChild('spreadsheet', { static: false }) spreadsheetObj?: SpreadsheetComponent;

  loading = true;
  error: string | null = null;

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    if (this.artifactId) {
      this.loadFile();
    }
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['artifactId'] && !changes['artifactId'].firstChange) {
      this.loadFile();
    }
  }

  ngOnDestroy(): void {
    if (this.spreadsheetObj) {
      this.spreadsheetObj.destroy();
    }
  }

  private fileBlob: Blob | null = null;

  private loadFile(): void {
    this.loading = true;
    this.error = null;
    const contentUrl = `${environment.apiUrl}/artifacts/${this.artifactId}/content`;

    this.http.get(contentUrl, { responseType: 'blob' }).subscribe({
      next: (blob) => {
        this.fileBlob = blob;
        this.loading = false;
      },
      error: (err) => {
        console.error('Error loading spreadsheet:', err);
        this.error = 'Error al cargar el archivo Excel';
        this.loading = false;
      }
    });
  }

  onSpreadsheetCreated(): void {
    if (this.spreadsheetObj && this.fileBlob) {
      const file = new File(
        [this.fileBlob],
        this.fileName || 'spreadsheet.xlsx',
        { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }
      );
      this.spreadsheetObj.open({ file });
    }
  }
}
