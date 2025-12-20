import { useState } from 'react'

export default function VerificationReport({ report }) {
  if (!report || !report.result) return null

  const screenshots = report.result.screenshots || []
  const emptyPlaceholder = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="400" height="240"><rect width="100%" height="100%" fill="%23f3f4f6"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="%23999" font-size="14">No preview available</text></svg>'

  const getBase64 = (s) => s?.image_base64 || s?.screenshot_base64 || s?.screenshot || null

  return (
    <div className="mt-6 bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">Verification Report Screenshots</h3>
      {screenshots.length === 0 && (
        <div className="text-sm text-gray-500">No screenshots available in the report.</div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {screenshots.map((s, idx) => {
          const b64 = getBase64(s)
          const src = b64 ? `data:image/png;base64,${b64}` : emptyPlaceholder
          return (
            <div key={idx} className="border rounded overflow-hidden">
              <div className="bg-gray-50 p-2 text-xs text-gray-600">{s.url || 'unknown URL'}</div>
              <img
                src={src}
                alt={`screenshot-${idx}`}
                className="w-full h-48 object-cover"
                onError={(e) => { e.currentTarget.src = emptyPlaceholder }}
              />
              <div className="p-2 text-xs text-gray-500">{new Date((s.timestamp || 0) * 1000).toLocaleString()}</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
