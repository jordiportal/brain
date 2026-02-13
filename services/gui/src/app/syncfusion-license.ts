// Archivo centralizado para registrar la licencia de Syncfusion
// Misma clave que fuse-lowcode
import { registerLicense } from '@syncfusion/ej2-base';

export function registerSyncfusionLicense(): void {
    const licenseKey = (window as unknown as { __SYNCFUSION_LICENSE__?: string }).__SYNCFUSION_LICENSE__ ?? 'Ngo9BigBOggjHTQxAR8/V1JFaF5cXGRCf1FpRmJGdld5fUVHYVZUTXxaS00DNHVRdkdmWXZcc3RWRmJZVEJ2XkRWYEA=';
    try {
        registerLicense(licenseKey);
    } catch {
        // Evitar romper el arranque si la clave no es válida aún
    }
}
