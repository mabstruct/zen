export function pushTrail(trail: string[], path: string, owners?: Map<string, string>): string[] {
  const last = trail[trail.length - 1]
  if (last === path) return trail
  if (last !== undefined && owners) {
    const o = owners.get(path)
    if (o !== undefined && o === owners.get(last)) return [...trail.slice(0, -1), path]
  }
  return [...trail, path].slice(-30)
}
