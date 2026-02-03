import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';
import { FavoriteButton } from './Favorites';

// Route to label mapping
const routeLabels: Record<string, string> = {
  '': 'Dashboard',
  'chat': 'Chat',
  'council': 'Grand Council',
  'terminals': 'Terminals',
  'workflows': 'Workflows',
  'workflow-designer': 'Workflow Designer',
  'tools': 'Tools',
  'memory': 'Memory',
  'memory-explorer': 'Memory Explorer',
  'agents': 'Agents',
  'mcp': 'MCP Servers',
  'apex': 'APEX Dashboard',
  'swarm': 'Swarm Intelligence',
  'god-mode': 'God Mode',
  'files': 'Files',
  'projects': 'Projects',
  'settings': 'Settings',
};

// Parent route relationships
const routeParents: Record<string, string> = {
  'workflow-designer': 'workflows',
  'memory-explorer': 'memory',
};

interface BreadcrumbItem {
  label: string;
  path: string;
  isLast: boolean;
}

export function Breadcrumbs() {
  const location = useLocation();
  const pathSegments = location.pathname.split('/').filter(Boolean);

  // Build breadcrumb items
  const items: BreadcrumbItem[] = [];

  // Always start with home
  items.push({
    label: 'Home',
    path: '/',
    isLast: pathSegments.length === 0
  });

  // Build path progressively
  let currentPath = '';
  pathSegments.forEach((segment, index) => {
    currentPath += `/${segment}`;
    const label = routeLabels[segment] || segment.charAt(0).toUpperCase() + segment.slice(1);

    items.push({
      label,
      path: currentPath,
      isLast: index === pathSegments.length - 1
    });
  });

  // Don't show breadcrumbs on home page
  if (items.length <= 1) {
    return null;
  }

  return (
    <nav className="flex items-center gap-1 text-sm mb-4 px-1">
      {items.map((item, index) => (
        <React.Fragment key={item.path}>
          {index > 0 && (
            <ChevronRight className="w-4 h-4 text-bael-muted" />
          )}
          {item.isLast ? (
            <span className="text-bael-text font-medium flex items-center gap-2">
              {item.label}
              <FavoriteButton path={item.path} title={item.label} />
            </span>
          ) : (
            <Link
              to={item.path}
              className="text-bael-muted hover:text-bael-text transition-colors flex items-center gap-1"
            >
              {index === 0 && <Home className="w-3.5 h-3.5" />}
              {item.label}
            </Link>
          )}
        </React.Fragment>
      ))}
    </nav>
  );
}

export default Breadcrumbs;
