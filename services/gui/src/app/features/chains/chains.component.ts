import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { StrapiService } from '../../core/services/strapi.service';
import { BrainChain } from '../../core/models';

@Component({
  selector: 'app-chains',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatMenuModule,
    MatProgressSpinnerModule,
    MatDividerModule,
    MatTooltipModule
  ],
  template: `
    <div class="chains-page">
      <div class="page-header">
        <div>
          <h1>Cadenas de Pensamiento</h1>
          <p class="subtitle">Gestiona y visualiza los flujos de procesamiento</p>
        </div>
        <button mat-raised-button color="primary">
          <mat-icon>add</mat-icon>
          Nueva Cadena
        </button>
      </div>

      @if (loading()) {
        <div class="loading-container">
          <mat-spinner diameter="48"></mat-spinner>
          <p>Cargando cadenas...</p>
        </div>
      } @else {
        <div class="chains-grid">
          @for (chain of chains(); track chain.id) {
            <mat-card class="chain-card">
              <mat-card-header>
                <div class="chain-icon" [class]="chain.type">
                  <mat-icon>{{ getChainIcon(chain.type) }}</mat-icon>
                </div>
                <mat-card-title>{{ chain.name }}</mat-card-title>
                <mat-card-subtitle>{{ chain.type | uppercase }} - v{{ chain.version }}</mat-card-subtitle>
              </mat-card-header>
              
              <mat-card-content>
                <p class="description">{{ chain.description || 'Sin descripción' }}</p>
                
                <div class="chain-stats">
                  @if (chain.nodes?.length) {
                    <span class="stat">
                      <mat-icon>radio_button_checked</mat-icon>
                      {{ chain.nodes.length }} nodos
                    </span>
                  }
                  @if (chain.edges?.length) {
                    <span class="stat">
                      <mat-icon>trending_flat</mat-icon>
                      {{ chain.edges?.length }} conexiones
                    </span>
                  }
                </div>

                <div class="chain-chips">
                  <mat-chip [class]="chain.isActive ? 'active' : 'inactive'">
                    {{ chain.isActive ? 'Activa' : 'Inactiva' }}
                  </mat-chip>
                  @if (chain.llmProvider) {
                    <mat-chip>{{ chain.llmProvider.name }}</mat-chip>
                  }
                </div>
              </mat-card-content>

              <mat-card-actions align="end">
                <button mat-icon-button matTooltip="Ejecutar">
                  <mat-icon>play_arrow</mat-icon>
                </button>
                <button mat-icon-button matTooltip="Visualizar">
                  <mat-icon>visibility</mat-icon>
                </button>
                <button mat-icon-button [matMenuTriggerFor]="chainMenu">
                  <mat-icon>more_vert</mat-icon>
                </button>
                <mat-menu #chainMenu="matMenu">
                  <button mat-menu-item>
                    <mat-icon>edit</mat-icon>
                    <span>Editar</span>
                  </button>
                  <button mat-menu-item>
                    <mat-icon>content_copy</mat-icon>
                    <span>Duplicar</span>
                  </button>
                  <button mat-menu-item>
                    <mat-icon>history</mat-icon>
                    <span>Ver ejecuciones</span>
                  </button>
                  <mat-divider></mat-divider>
                  <button mat-menu-item class="delete-action">
                    <mat-icon>delete</mat-icon>
                    <span>Eliminar</span>
                  </button>
                </mat-menu>
              </mat-card-actions>
            </mat-card>
          } @empty {
            <div class="empty-state">
              <mat-icon>account_tree</mat-icon>
              <h3>No hay cadenas configuradas</h3>
              <p>Crea tu primera cadena de pensamiento para comenzar</p>
              <button mat-raised-button color="primary">
                <mat-icon>add</mat-icon>
                Crear Cadena
              </button>
            </div>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .chains-page {
      max-width: 1400px;
      margin: 0 auto;
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 24px;
    }

    h1 {
      margin: 0;
      font-size: 28px;
      font-weight: 600;
      color: #1a1a2e;
    }

    .subtitle {
      color: #666;
      margin: 4px 0 0;
    }

    .loading-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 64px;
      color: #666;
    }

    .chains-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
      gap: 20px;
    }

    .chain-card {
      border-radius: 12px;
      transition: transform 0.2s, box-shadow 0.2s;
    }

    .chain-card:hover {
      transform: translateY(-4px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.12);
    }

    .chain-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-right: 16px;
    }

    .chain-icon.graph { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .chain-icon.chain { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
    .chain-icon.agent { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
    .chain-icon.rag { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }

    .chain-icon mat-icon {
      color: white;
      font-size: 24px;
    }

    .description {
      color: #666;
      font-size: 14px;
      margin: 16px 0;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .chain-stats {
      display: flex;
      gap: 16px;
      margin-bottom: 12px;
    }

    .stat {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 13px;
      color: #888;
    }

    .stat mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
    }

    .chain-chips {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }

    mat-chip.active {
      background: #e8f5e9 !important;
      color: #388e3c !important;
    }

    mat-chip.inactive {
      background: #fafafa !important;
      color: #9e9e9e !important;
    }

    .delete-action {
      color: #f44336;
    }

    .empty-state {
      grid-column: 1 / -1;
      text-align: center;
      padding: 64px;
      background: white;
      border-radius: 12px;
    }

    .empty-state mat-icon {
      font-size: 72px;
      width: 72px;
      height: 72px;
      color: #ccc;
      margin-bottom: 16px;
    }

    .empty-state h3 {
      margin: 0 0 8px;
      color: #333;
    }

    .empty-state p {
      color: #666;
      margin-bottom: 24px;
    }
  `]
})
export class ChainsComponent implements OnInit {
  chains = signal<BrainChain[]>([]);
  loading = signal(true);

  constructor(private strapiService: StrapiService) {}

  ngOnInit(): void {
    this.loadChains();
  }

  loadChains(): void {
    this.loading.set(true);
    this.strapiService.getBrainChains({ populate: '*' }).subscribe({
      next: (chains) => {
        this.chains.set(chains);
        this.loading.set(false);
      },
      error: () => this.loading.set(false)
    });
  }

  getChainIcon(type: string): string {
    const icons: Record<string, string> = {
      graph: 'account_tree',
      chain: 'link',
      agent: 'smart_toy',
      rag: 'search'
    };
    return icons[type] || 'psychology';
  }
}
