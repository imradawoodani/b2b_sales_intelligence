export default function TierBadge({ tier }) {
  const colors = {
    'Master Elite': 'bg-yellow-100 text-yellow-800 border-yellow-200',
    'Certified Plus': 'bg-blue-100 text-blue-800 border-blue-200',
    'Certified': 'bg-green-100 text-green-800 border-green-200',
    'Uncertified': 'bg-gray-100 text-gray-800 border-gray-200',
  };

  const style = colors[tier] || colors['Uncertified'];

  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${style}`}>
      {tier}
    </span>
  );
}