import TierBadge from './TierBadge';

export default function ContractorList({ contractors, onSelect }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {contractors.map(c => (
        <div 
          key={c.id} 
          onClick={() => onSelect(c)}
          className="bg-white border border-gray-200 rounded-xl p-5 cursor-pointer hover:shadow-md hover:border-blue-300 transition-all"
        >
          <div className="flex justify-between items-start mb-3">
            <h3 className="font-semibold text-lg">{c.name}</h3>
            <div className="bg-blue-50 text-blue-700 font-bold px-2 py-1 rounded text-sm">
              {c.score}
            </div>
          </div>
          <TierBadge tier={c.tier} />
          <div className="mt-4 text-sm text-gray-600 space-y-1">
            <p><span className="font-medium">Est. Revenue:</span> {c.estRevenue}</p>
            <p><span className="font-medium">Distance:</span> {c.distance}</p>
            <p><span className="font-medium">Reviews:</span> {c.reviews} ({c.rating} ⭐️)</p>
          </div>
        </div>
      ))}
    </div>
  );
}