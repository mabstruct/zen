export function pushTrail(trail: string[], path: string): string[] {
  if (trail[trail.length - 1] === path) return trail
  return [...trail, path].slice(-30)
}
