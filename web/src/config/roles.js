/** Roles offered in the top-bar switcher, as [value, label]. */
export const ROLES = [
  ['executive', 'Executive'],
  ['unit-head', 'Unit head'],
  ['analyst', 'Analyst'],
  ['librarian', 'Librarian'],
  ['member', 'Member'],
  ['admin', 'Admin'],
];

export function roleLabel(role) {
  const match = ROLES.find(([value]) => value === role);
  return (match ?? ROLES[0])[1];
}
