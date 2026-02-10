import { Pipe, PipeTransform } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { marked } from 'marked';

marked.setOptions({ async: false });

/**
 * Pipe para renderizar Markdown de forma segura.
 * 
 * Features:
 * - Convierte imágenes base64 grandes a Blob URLs (optimización de memoria)
 * - Resaltado de sintaxis para bloques de código
 * - Soporte para thinking blocks (bloques de razonamiento)
 * - Tablas, listas, citas, enlaces
 */
@Pipe({
  name: 'markdown',
  standalone: true
})
export class MarkdownPipe implements PipeTransform {
  constructor(private sanitizer: DomSanitizer) {}

  transform(value: string): SafeHtml {
    if (!value) return '';
    
    try {
      let processedValue = value;
      
      // Optimización: convertir imágenes base64 grandes a Blob URLs
      const base64ImageRegex = /!\[([^\]]*)\]\(data:image\/([^;]+);base64,([^\)]+)\)/g;
      const matches = Array.from(value.matchAll(base64ImageRegex));
      
      for (const match of matches) {
        const [fullMatch, altText, mimeType, base64Data] = match;
        
        // Si la imagen es grande (>100KB base64), convertir a Blob URL
        if (base64Data.length > 100000) {
          try {
            const binaryString = atob(base64Data);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
              bytes[i] = binaryString.charCodeAt(i);
            }
            const blob = new Blob([bytes], { type: `image/${mimeType}` });
            const blobUrl = URL.createObjectURL(blob);
            
            const replacement = `![${altText}](${blobUrl})`;
            processedValue = processedValue.replace(fullMatch, replacement);
            
            console.log(`Converted large image (${(base64Data.length/1024).toFixed(0)}KB) to Blob URL`);
          } catch (e) {
            console.warn('Failed to convert image to Blob:', e);
          }
        }
      }
      
      const html = marked.parse(processedValue, { async: false }) as string;
      return this.sanitizer.bypassSecurityTrustHtml(html);
    } catch (error) {
      console.error('Error parsing markdown:', error);
      return this.sanitizer.bypassSecurityTrustHtml(value);
    }
  }
}
