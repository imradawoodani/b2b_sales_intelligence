import TierBadge from './TierBadge';

export default function SidePanel({ contractor, onClose }) {
  if (!contractor) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-[450px] bg-white shadow-2xl border-l border-gray-200 transform transition-transform duration-300 ease-in-out z-50 flex flex-col">
      <div className="p-6 border-b border-gray-100 flex justify-between items-start">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">{contractor.name}</h2>
          <div className="flex items-center gap-3">
            <span className="bg-blue-100 text-blue-800 text-sm font-bold px-2 py-1 rounded">Score: {contractor.score}</span>
            <TierBadge tier={contractor.tier} />
          </div>
        </div>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-700">
          ✕
        </button>
      </div>

      <div className="p-6 flex-1 overflow-y-auto">
        <div className="mb-6">
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">AI Sales Brief</h3>
          <p className="text-gray-700 leading-relaxed bg-blue-50/50 p-4 rounded-lg border border-blue-100">
            {contractor.brief}
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-gray-50 p-3 rounded-lg border border-gray-100">
            <span className="block text-xs text-gray-500 mb-1">Reviews</span>
            <span className="font-semibold">{contractor.reviews} ({contractor.rating} ⭐️)</span>
          </div>
          <div className="bg-gray-50 p-3 rounded-lg border border-gray-100">
            <span className="block text-xs text-gray-500 mb-1">Distance</span>
            <span className="font-semibold">{contractor.distance}</span>
          </div>
          <div className="bg-gray-50 p-3 rounded-lg border border-gray-100 col-span-2">
            <span className="block text-xs text-gray-500 mb-1">Contact</span>
            <span className="font-semibold">{contractor.contact}</span>
          </div>
        </div>

        {/* Layer 4: AI Q&A Mockup */}
        <div className="mt-8 border-t border-gray-100 pt-6">
          <h3 className="text-sm font-semibold mb-3">Ask about this lead</h3>
          <div className="flex gap-2">
            <input 
              type="text" 
              placeholder="e.g., Who is the primary decision maker?" 
              className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button className="bg-gray-900 text-white px-4 py-2 rounded-md text-sm hover:bg-gray-800">
              Ask
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}