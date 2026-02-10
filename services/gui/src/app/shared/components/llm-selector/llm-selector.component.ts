import { 
  Component, 
  Input, 
  Output, 
  EventEmitter,
  ChangeDetectionStrategy,
  Signal,
  signal,
  OnInit,
  inject
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';

import { LlmSelectionService } from './llm-selection.service';
import { LlmProvider } from '../../../core/models';

/**
 * Componente unificado de selección LLM
 * 
 * Features:
 * - Selector de proveedor + modelo en un solo componente
 * - Carga automática de modelos según proveedor seleccionado
 * - Caché de modelos para evitar llamadas repetidas
 * - Dos modos de visualización:
 *   - 'standard': Selectores completos con toda la info
 *   - 'compact': Versión minimalista para barras de herramientas
 * - Sincronización bidireccional via ngModel
 * 
 * Usado por:
 * - TestingComponent
 * - ChainsComponent
 * - SubagentsComponent (configuración y ejecución)
 */
@Component({
  selector: 'app-llm-selector',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatFormFieldModule,
    MatSelectModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatChipsModule
  ],
  template: `
    <div class="llm-selector" [class.compact]="mode === 'compact'">
      <!-- Proveedor -->
      <mat-form-field [appearance]="appearance" [class.full-width]="mode === 'standard'">
        <mat-label>{{ providerLabel }}</mat-label>
        <mat-select 
          [(ngModel)]="selectedProviderId" 
          (ngModelChange)="onProviderChange($event)"
          [disabled]="disabled || loadingProviders()">
          @if (allowEmpty) {
            <mat-option [value]="null">
              <em>{{ emptyProviderLabel }}</em>
            </mat-option>
          }
          @for (provider of providers(); track provider.id) {
            <mat-option [value]="provider.id">
              @if (mode === 'standard') {
                <div class="provider-option">
                  <span class="provider-name">{{ provider.name }}</span>
                  <span class="provider-type">{{ provider.type }}</span>
                  @if (showDefaults && provider.isDefault) {
                    <mat-chip class="default-chip" [disableRipple]="true">Por defecto</mat-chip>
                  }
                </div>
              } @else {
                {{ provider.name }}
              }
            </mat-option>
          }
          @if (loadingProviders()) {
            <mat-option disabled>
              <mat-spinner diameter="16"></mat-spinner>
              Cargando...
            </mat-option>
          }
        </mat-select>
        @if (mode === 'standard' && selectedProvider) {
          <mat-hint>
            {{ selectedProvider?.baseUrl }}
            @if (selectedProvider?.defaultModel) {
              · Modelo: {{ selectedProvider?.defaultModel }}
            }
          </mat-hint>
        }
      </mat-form-field>

      <!-- Modelo -->
      <mat-form-field [appearance]="appearance" [class.full-width]="mode === 'standard'">
        <mat-label>{{ modelLabel }}</mat-label>
        <mat-select 
          [(ngModel)]="selectedModel" 
          (ngModelChange)="onModelChange($event)"
          [disabled]="disabled || !selectedProviderId || loadingModels() || availableModels().length === 0">
          @if (allowDefaultModel) {
            <mat-option [value]="''">
              <em>Usar default: {{ selectedProvider?.defaultModel || '(ninguno)' }}</em>
            </mat-option>
          }
          @for (model of availableModels(); track model) {
            <mat-option [value]="model">{{ model }}</mat-option>
          }
          @if (loadingModels()) {
            <mat-option disabled>
              <mat-spinner diameter="16"></mat-spinner>
              Cargando modelos...
            </mat-option>
          }
          @if (!loadingModels() && availableModels().length === 0 && selectedProviderId) {
            <mat-option disabled>
              No hay modelos disponibles
            </mat-option>
          }
        </mat-select>
        @if (mode === 'standard' && availableModels().length > 0) {
          <mat-hint>{{ availableModels().length }} modelos disponibles</mat-hint>
        }
      </mat-form-field>
    </div>
  `,
  styles: [`
    .llm-selector {
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
    }

    .llm-selector.compact {
      gap: 8px;
    }

    .llm-selector.compact mat-form-field {
      width: auto;
      min-width: 150px;
    }

    .full-width {
      flex: 1;
      min-width: 200px;
    }

    .provider-option {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .provider-name {
      font-weight: 500;
    }

    .provider-type {
      font-size: 12px;
      color: #666;
      text-transform: uppercase;
    }

    .default-chip {
      font-size: 10px;
      min-height: 20px;
      background: #e3f2fd !important;
      color: #1976d2 !important;
    }

    mat-hint {
      font-size: 12px;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class LlmSelectorComponent implements OnInit {
  private llmService = inject(LlmSelectionService);

  // Inputs para two-way binding
  @Input() providerId: string | number | null = null;
  @Input() model: string = '';
  
  // Outputs para two-way binding
  @Output() providerIdChange = new EventEmitter<string | number | null>();
  @Output() modelChange = new EventEmitter<string>();
  
  // Otros inputs
  @Input() mode: 'standard' | 'compact' = 'standard';
  @Input() appearance: 'outline' | 'fill' = 'outline';
  @Input() disabled = false;
  @Input() allowEmpty = false;
  @Input() allowDefaultModel = true;
  @Input() showDefaults = true;
  @Input() providerLabel = 'Proveedor LLM';
  @Input() modelLabel = 'Modelo';
  @Input() emptyProviderLabel = 'Seleccionar proveedor...';
  
  // Evento combinado de selección completa
  @Output() selectionChange = new EventEmitter<{
    providerId: string | number | null;
    provider: LlmProvider | null;
    model: string;
  }>();

  // Internal state
  private _providerId: string | number | null = null;
  private _model = '';
  
  providers: Signal<LlmProvider[]> = this.llmService.providers;
  loadingProviders: Signal<boolean> = this.llmService.loadingProviders;
  loadingModels: Signal<boolean> = this.llmService.loadingModels;
  availableModels = signal<string[]>([]);

  // Getter/Setter para two-way binding
  get selectedProviderId(): string | number | null {
    return this._providerId;
  }
  
  set selectedProviderId(value: string | number | null) {
    this._providerId = value;
  }
  
  get selectedModel(): string {
    return this._model;
  }
  
  set selectedModel(value: string) {
    this._model = value;
  }

  ngOnInit(): void {
    // Cargar proveedores
    this.llmService.loadProviders().subscribe();
    
    // Aplicar valores de entrada si existen
    if (this.providerId) {
      this._providerId = this.providerId;
      this.loadModelsForProvider(this.providerId);
    }
    if (this.model) {
      this._model = this.model;
    }
  }

  get selectedProvider(): LlmProvider | null | undefined {
    return this.llmService.getProviderById(this.selectedProviderId);
  }

  onProviderChange(providerId: string | number | null): void {
    this._providerId = providerId;
    this._model = ''; // Reset model when provider changes
    this.availableModels.set([]);
    
    // Emitir evento para two-way binding
    this.providerIdChange.emit(providerId);
    
    const provider = this.llmService.getProviderById(providerId);
    
    if (provider) {
      this.loadModelsForProvider(providerId!);
    } else {
      this.emitSelection();
    }
  }

  private loadModelsForProvider(providerId: string | number): void {
    const provider = this.llmService.getProviderById(providerId);
    if (!provider) return;

    this.llmService.loadModels(provider).subscribe(models => {
      this.availableModels.set(models);
      
      // Si solo hay un modelo, seleccionarlo automáticamente
      if (models.length === 1 && !this.allowDefaultModel) {
        this.selectedModel = models[0];
        this.emitSelection();
      }
    });
  }

  onModelChange(model: string): void {
    this.selectedModel = model;
    this.modelChange.emit(model);
    this.emitSelection();
  }

  private emitSelection(): void {
    const provider = this.selectedProvider || null;
    this.selectionChange.emit({
      providerId: this.selectedProviderId,
      provider,
      model: this.selectedModel
    });
  }

  /**
   * Obtiene la configuración completa para ejecución
   */
  getExecutionConfig(): {
    provider_url: string;
    provider_type: string;
    api_key?: string;
    model: string;
  } | null {
    return this.llmService.buildExecutionConfig(
      this.selectedProviderId,
      this.selectedModel
    );
  }
}
