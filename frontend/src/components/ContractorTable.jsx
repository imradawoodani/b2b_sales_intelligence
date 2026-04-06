import TierBadge from './TierBadge';

export default function ContractorTable({ contractors, onSelect }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="bg-gray-50 border-b border-gray-200 text-sm text-gray-500">
            <th className="p-4 font-medium">Name</th>
            <th className="p-4 font-medium">Score</th>
            <th className="p-4 font-medium">Tier</th>
            <th className="p-4 font-medium">Est. Revenue</th>
            <th className="p-4 font-medium">Distance</th>
          </tr>
        </thead>
        <tbody>
          {contractors.map((c) => (
            <tr 
              key={c.id} 
              onClick={() => onSelect(c)}
              className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors"
            >
              <td className="p-4 font-medium text-gray-900">{c.name}</td>
              <td className="p-4">
                <span className="font-semibold text-blue-600">{c.score}</span>
              </td>
              <td className="p-4"><TierBadge tier={c.tier} /></td>
              <td className="p-4 text-gray-600">{c.estRevenue}</td>
              <td className="p-4 text-gray-600">{c.distance}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}