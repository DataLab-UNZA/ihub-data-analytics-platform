'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import UnitPie from '@/components/features/organisation/UnitPie';
import Card, { CardHeader } from '@/components/ui/Card';
import CountList from '@/components/ui/CountList';
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

/** Lower-case, accent-free text, so case and accents never stop a unit being found. */
const normalise = (text) => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

const isMatch = (node, query) => node.id !== 'unza' && normalise(node.name).includes(query);

/**
 * The part of the tree that matches a search: matching nodes and the nodes above them.
 * Returns null when nothing matches. A node whose own name matches keeps all its children.
 */
function filterTree(node, query) {
  if (isMatch(node, query)) return node;
  const children = (node.children ?? []).map((child) => filterTree(child, query)).filter(Boolean);
  return children.length ? { ...node, children } : null;
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

  const [search, setSearch] = useState('');
  const query = normalise(search.trim());
  const shown = useMemo(() => (query ? filterTree(tree, query) : tree), [tree, query]);
  const matching = useMemo(() => (shown && query ? flatten(shown).filter((node) => isMatch(node, query)) : []), [shown, query]);
  const searchBox = useRef(null);

  // The results list right under the search box; bring the box (and so the results) into view if it is not.
  useEffect(() => {
    if (query) searchBox.current?.scrollIntoView({ block: 'nearest' });
  }, [query]);

  const unitNodes = useMemo(() => (tree.children ?? []).filter((node) => node.inPie !== false), [tree]);
  const pieSlices = unitNodes.filter((node) => node.count > 0);

  const toggle = (id) =>
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const expandable = nodes.filter((node) => node.children?.length || node.expandable).map((node) => node.id);
  // While searching, every unit above a match is open so the matches show without any clicking.
  const open = query
    ? new Set([...expanded, ...flatten(shown ?? tree).filter((node) => node.children?.length).map((node) => node.id)])
    : expanded;

  return (
    <Grid variant="main-aside" start>
      <Card aria-labelledby="tree-title">
        <CardHeader
          id="tree-title"
          title="Your organisation"
          subtitle={subtitle}
          className="mb-8"
        />
        <form
          className="tree__search"
          role="search"
          ref={searchBox}
          onSubmit={(event) => {
            event.preventDefault();
            if (matching[0]) setSelectedId(matching[0].id);
          }}
        >
          <label className="sr-only" htmlFor="unit-search">
            Search units
          </label>
          <input
            className="input"
            id="unit-search"
            type="search"
            placeholder="Search schools and units…"
            autoComplete="off"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          <p className="tree__search-status" role="status">
            {query && (matching.length
              ? `${matching.length} matching unit${matching.length === 1 ? '' : 's'}. Press Enter to select the first.`
              : 'No unit matches your search.')}
          </p>
        </form>
        <div className="tree__actions">
          <button className="link-button" type="button" onClick={() => setExpanded(new Set(expandable))}>
            Expand all
          </button>
          <button className="link-button" type="button" onClick={() => setExpanded(new Set())}>
            Collapse all
          </button>
        </div>
        <ul className="tree" aria-labelledby="tree-title">
          {shown && <TreeNode node={shown} expanded={open} selectedId={selectedId} onToggle={toggle} onSelect={setSelectedId} />}
        </ul>
      </Card>

      <GridStack>
        <Card aria-labelledby="pie-title">
          <CardHeader id="pie-title" title="Publications by unit" subtitle="Share of the period's output" className="mb-16" />
          <UnitPie
            slices={pieSlices}
            emptyUnits={unitNodes.length - pieSlices.length}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </Card>
        <Card aria-labelledby="selected-title" aria-live="polite">
          <CardHeader id="selected-title" title="Selected unit" subtitle={selected.name} className="mb-40" />
          <p className={cx('big-figure', 'big-figure--xl')}>{selected.outputs}</p>
          <p className="text-muted mt-16">publications · {selected.childrenLabel}</p>
          <p className="meta-label mt-24">By source</p>
          {selected.sources ? (
            <CountList items={selected.sources} label={`Publications by source in ${selected.name}`} />
          ) : (
            <p className="text-muted text-xs mt-8">Source figures are given for schools, not for their departments.</p>
          )}
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
            <Link href={selected.unit ? `/publications?unit=${encodeURIComponent(selected.unit)}` : '/publications?unit=all'}>
              {selected.unit && selected.unit !== selected.name ? `View ${selected.unit} publications →` : 'View publications →'}
            </Link>
          </p>
        </Card>
        {children}
      </GridStack>
    </Grid>
  );
}
