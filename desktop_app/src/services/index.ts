import { RealLightingService } from './RealLightingService';

// Export types explicitly if needed
export type { ILightingService } from './LightingService';

// Determine which implementation to use. 
// For now, always use real since we built the python sidecar.
export const lightingService = new RealLightingService();
