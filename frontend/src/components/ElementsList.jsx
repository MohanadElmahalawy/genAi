import { useState, useMemo } from 'react';
import { Search, Filter } from 'lucide-react';

export default function ElementsList({ knowledge }) {
  const [query, setQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');

  const elements = knowledge?.elements || [];

  const types = useMemo(() => {
    const s = new Set(elements.map((e) => e.type || 'unknown'));
    return ['all', ...Array.from(s)];
  }, [elements]);

  const filtered = elements.filter((el) => {
    const matchesType = typeFilter === 'all' ? true : (el.type === typeFilter);
    const text = JSON.stringify(el).toLowerCase();
    const matchesQuery = !query || text.includes(query.toLowerCase());
    return matchesType && matchesQuery;
  });

  return (
    <div className="mt-6 bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Page Elements</h3>
          <p className="text-sm text-gray-600">Extracted interactive elements from the page</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center bg-gray-100 rounded-md px-2 py-1">
            <Search className="w-4 h-4 text-gray-500 mr-2" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search elements..."
              className="bg-transparent text-sm outline-none w-48"
            />
          </div>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-2 py-1 border border-gray-200 rounded-md text-sm"
          >
            {types.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="p-6 space-y-3 max-h-64 overflow-y-auto">
        {filtered.length === 0 && (
          <div className="text-sm text-gray-500">No elements match the filter.</div>
        )}

        {filtered.map((el, idx) => (
          <div key={idx} className="border border-gray-200 rounded-lg p-3">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-xs text-gray-500">{el.type || el.tagName || 'element'}</div>
                <div className="font-medium text-gray-900">{el.name || el.id || el.text || el.tagName || 'Unnamed'}</div>
                {el.description && <div className="text-sm text-gray-600 mt-1">{el.description}</div>}
              </div>
              <div className="text-right text-xs text-gray-500">
                {el.locator && <div>Locator: <span className="font-mono text-xs text-gray-700">{el.locator}</span></div>}
                {el.href && <div className="mt-1">Href: <a className="text-indigo-600" href={el.href} target="_blank" rel="noreferrer">link</a></div>}
              </div>
            </div>
            <div className="mt-3 text-xs text-gray-600">
              <div>ID: <span className="font-mono text-gray-700">{el.id || '-'}</span></div>
              {el.inputType && <div>Input Type: {el.inputType}</div>}
              {el.className && <div>Class: <span className="font-mono">{el.className}</span></div>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
