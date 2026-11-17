'use client';

import { useState } from 'react';
import Link from 'next/link';
import Card, { CardHeader } from '@/components/ui/Card';
import Grid, { GridStack } from '@/components/ui/Grid';
import { cx } from '@/lib/format';

function collectIds(node, predicate, found = []) {
  if (predicate(node)) found.push(node.id);
  (node.children ?? []).forEach((child) => collectIds(child, predicate, found));
  return found;
}

function findSelected(node) {
  const ids = collectIds(node, (item) => item.selected);
  return ids[0] ?? node.id;
}

function flatten(node, list = []) {
  list.push(node);
  (node.children ?? []).forEach((child) => flatten(child, list));
  return list;
}

function TreeNode({ node, expanded, selectedId, onToggle, onSelect }) {
  const isExpandable = Boolean(node.children?.length || node.expandable);
  const isOpen = expanded.has(node.id);
  const listId = `tree-${node.id}`;

  return (
    <li>
      <div className="tree__row">
        {isExpandable && (
          <button
            className="tree__toggle"
            type="button"
            aria-expanded={isOpen}
            aria-controls={listId}
            onClick={() => onToggle(node.id)}
          >
            <span className="sr-only">Toggle {node.name}</span>
          </button>
        )}
        <button
          className="tree__select"
          type="button"
          aria-current={node.id === selectedId ? 'true' : undefined}
          onClick={() => onSelect(node.id)}
        >
          <span className="tree__name">{node.name}</span>
          <span className="tree__meta">
            {node.kind} · {node.outputs} publications
          </span>
        </button>
      </div>
      {isExpandable && (
        <ul id={listId} hidden={!isOpen}>
          {(node.children ?? []).map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              expanded={expanded}
              selectedId={selectedId}
              onToggle={onToggle}
              onSelect={onSelect}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

/**
 * Organisation tree beside a "Selected unit" summary.
 * Both cards share the selection, so they live in one client component.
 *
 * @param {object} tree  Root node (see services/research.js loadOrganisation).
 * @param {node} subtitle Line under the tree heading.
 * @param {node} children Extra cards rendered under the summary in the aside column.
 */
export default function OrganisationExplorer({ tree, subtitle, children }) {
  const nodes = flatten(tree);
  const [expanded, setExpanded] = useState(() => new Set(nodes.filter((node) => node.expanded).map((n) => n.id)));
  const [selectedId, setSelectedId] = useState(() => findSelected(tree));
  const selected = nodes.find((node) => node.id === selectedId);

  const toggle = (id) =>
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const expandable = nodes.filter((node) => node.children?.length || node.expandable).map((node) => node.id);

  return (
    <Grid variant="main-aside" start>
      <Card aria-labelledby="tree-title">
        <CardHeader
          id="tree-title"
          title="Your organisation"
          subtitle={subtitle}
          className="mb-8"
        />
        <div className="tree__actions">
          <button className="link-button" type="button" onClick={() => setExpanded(new Set(expandable))}>
            Expand all
          </button>
          <button className="link-button" type="button" onClick={() => setExpanded(new Set())}>
            Collapse all
          </button>
        </div>
        <ul className="tree" aria-labelledby="tree-title">
          <TreeNode node={tree} expanded={expanded} selectedId={selectedId} onToggle={toggle} onSelect={setSelectedId} />
        </ul>
      </Card>

      <GridStack>
        <Card aria-labelledby="selected-title" aria-live="polite">
          <CardHeader id="selected-title" title="Selected unit" subtitle={selected.name} className="mb-40" />
          <p className={cx('big-figure', 'big-figure--xl')}>{selected.outputs}</p>
          <p className="text-muted mt-16">publications · {selected.childrenLabel}</p>
          {selected.details ? (
            selected.details.map(([label, value]) => (
              <div key={label}>
                <p className="meta-label mt-24">{label}</p>
                <p className="text-md fw-500 mt-8">{value}</p>
              </div>
            ))
          ) : (
            <>
              <p className="meta-label mt-32">Head of unit</p>
              <p className="text-md fw-500 mt-8">Visible to authorised roles</p>
            </>
          )}
          <p className="mt-48 mb-24">
            <Link href="/publications">View publications →</Link>
          </p>
        </Card>
        {children}
      </GridStack>
    </Grid>
  );
}
