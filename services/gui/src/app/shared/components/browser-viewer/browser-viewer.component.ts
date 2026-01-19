import { Component, OnInit, OnDestroy, Input, Output, EventEmitter, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { HttpClient } from '@angular/common/http';
import { catchError, of, interval, Subscription } from 'rxjs';

interface BrowserStatus {
  initialized: boolean;
  headless: boolean;
  active_sessions: number;
  vnc_available: boolean;
  vnc_host: string | null;
}

@Component({
  selector: 'app-browser-viewer',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTooltipModule
  ],
  template: `
    <div class="browser-viewer" [class.expanded]="expanded()" [class.minimized]="!expanded()">
      <!-- Header -->
      <div class="viewer-header" (click)="toggleExpanded()">
        <div class="header-left">
          <mat-icon class="browser-icon" [class.connected]="isConnected()">desktop_windows</mat-icon>
          <span class="title">Vista del Navegador</span>
          @if (isLoading()) {
            <mat-spinner diameter="16"></mat-spinner>
          }
          @if (isConnected()) {
            <span class="status-badge connected">Conectado</span>
          } @else {
            <span class="status-badge disconnected">Desconectado</span>
          }
        </div>
        
        <div class="header-actions">
          @if (expanded()) {
            <button mat-icon-button 
                    matTooltip="Abrir en nueva ventana" 
                    (click)="openInNewWindow($event)">
              <mat-icon>open_in_new</mat-icon>
            </button>
            <button mat-icon-button 
                    matTooltip="Recargar" 
                    (click)="refresh($event)">
              <mat-icon>refresh</mat-icon>
            </button>
          }
          <button mat-icon-button [matTooltip]="expanded() ? 'Minimizar' : 'Expandir'">
            <mat-icon>{{ expanded() ? 'expand_more' : 'expand_less' }}</mat-icon>
          </button>
        </div>
      </div>
      
      <!-- Viewer Content -->
      @if (expanded()) {
        <div class="viewer-content">
          @if (isLoading()) {
            <div class="loading-overlay">
              <mat-spinner diameter="48"></mat-spinner>
              <p>Conectando al navegador...</p>
            </div>
          } @else if (!isConnected()) {
            <div class="not-connected">
              <mat-icon>desktop_access_disabled</mat-icon>
              <p>Navegador no disponible</p>
              <p class="hint">El servicio de navegador visual no está activo.</p>
              <button mat-stroked-button color="primary" (click)="checkConnection()">
                <mat-icon>refresh</mat-icon>
                Reintentar conexión
              </button>
            </div>
          } @else {
            <iframe
              [src]="vncUrl()"
              class="vnc-iframe"
              allow="clipboard-read; clipboard-write"
              (load)="onIframeLoad()"
              (error)="onIframeError()">
            </iframe>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .browser-viewer {
      border: 1px solid var(--mat-divider-color, #e0e0e0);
      border-radius: 12px;
      overflow: hidden;
      background: var(--mat-card-background, #fff);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
      transition: all 0.3s ease;
      
      &.minimized {
        .viewer-header {
          border-bottom: none;
        }
      }
      
      &.expanded {
        .viewer-content {
          height: 500px;
        }
      }
    }
    
    .viewer-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 16px;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      color: white;
      cursor: pointer;
      user-select: none;
      
      &:hover {
        background: linear-gradient(135deg, #1f1f3a 0%, #1b2847 100%);
      }
      
      .header-left {
        display: flex;
        align-items: center;
        gap: 12px;
        
        .browser-icon {
          font-size: 20px;
          width: 20px;
          height: 20px;
          opacity: 0.7;
          
          &.connected {
            opacity: 1;
            color: #4caf50;
          }
        }
        
        .title {
          font-weight: 500;
          font-size: 14px;
        }
        
        mat-spinner {
          opacity: 0.8;
        }
        
        .status-badge {
          font-size: 11px;
          padding: 2px 8px;
          border-radius: 10px;
          font-weight: 500;
          
          &.connected {
            background: rgba(76, 175, 80, 0.2);
            color: #81c784;
          }
          
          &.disconnected {
            background: rgba(244, 67, 54, 0.2);
            color: #e57373;
          }
        }
      }
      
      .header-actions {
        display: flex;
        gap: 4px;
        
        button {
          color: white;
          opacity: 0.8;
          
          &:hover {
            opacity: 1;
          }
        }
      }
    }
    
    .viewer-content {
      position: relative;
      background: #0a0a0f;
      overflow: hidden;
      height: 0;
      transition: height 0.3s ease;
    }
    
    .vnc-iframe {
      width: 100%;
      height: 100%;
      border: none;
      background: #000;
    }
    
    .loading-overlay,
    .not-connected {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      color: rgba(255, 255, 255, 0.7);
      gap: 16px;
      
      mat-icon {
        font-size: 48px;
        width: 48px;
        height: 48px;
        opacity: 0.5;
      }
      
      p {
        margin: 0;
        font-size: 14px;
      }
      
      .hint {
        font-size: 12px;
        opacity: 0.6;
      }
    }
  `]
})
export class BrowserViewerComponent implements OnInit, OnDestroy {
  private sanitizer = inject(DomSanitizer);
  private http = inject(HttpClient);
  
  @Input() apiUrl = 'http://localhost:8000/api/v1';
  @Input() browserPort = 6080;
  
  @Output() connectionChange = new EventEmitter<boolean>();
  
  expanded = signal(true);
  isLoading = signal(true);
  isConnected = signal(false);
  vncUrl = signal<SafeResourceUrl>('');
  
  private statusCheckInterval?: Subscription;
  
  ngOnInit(): void {
    this.checkConnection();
    
    // Comprobar estado cada 10 segundos
    this.statusCheckInterval = interval(10000).subscribe(() => {
      if (!this.isLoading()) {
        this.checkConnection(true);
      }
    });
  }
  
  ngOnDestroy(): void {
    this.statusCheckInterval?.unsubscribe();
  }
  
  checkConnection(silent = false): void {
    if (!silent) {
      this.isLoading.set(true);
    }
    
    // Verificar si el servicio VNC está disponible directamente
    const baseUrl = window.location.hostname;
    const vncUrlStr = `http://${baseUrl}:${this.browserPort}/vnc.html?autoconnect=true&resize=scale&reconnect=true`;
    
    // Intentar cargar el endpoint de estado de la API
    this.http.get<BrowserStatus>(`${this.apiUrl}/browser/status`)
      .pipe(catchError(() => of(null)))
      .subscribe(status => {
        this.isLoading.set(false);
        
        if (status?.vnc_available) {
          this.vncUrl.set(this.sanitizer.bypassSecurityTrustResourceUrl(vncUrlStr));
          this.isConnected.set(true);
          this.connectionChange.emit(true);
        } else {
          // Intentar conectar directamente al VNC aunque la API no lo reporte
          this.vncUrl.set(this.sanitizer.bypassSecurityTrustResourceUrl(vncUrlStr));
          this.isConnected.set(true);
          this.connectionChange.emit(true);
        }
      });
  }
  
  toggleExpanded(): void {
    this.expanded.set(!this.expanded());
  }
  
  openInNewWindow(event: Event): void {
    event.stopPropagation();
    const baseUrl = window.location.hostname;
    const vncUrlStr = `http://${baseUrl}:${this.browserPort}/vnc.html?autoconnect=true&resize=scale`;
    window.open(vncUrlStr, '_blank', 'width=1300,height=800');
  }
  
  refresh(event: Event): void {
    event.stopPropagation();
    this.checkConnection();
  }
  
  onIframeLoad(): void {
    console.log('VNC iframe loaded');
  }
  
  onIframeError(): void {
    console.error('Error loading VNC iframe');
    this.isConnected.set(false);
  }
}
