export default function PipelineStatus({ isLoading }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <div className={`w-2 h-2 rounded-full ${isLoading ? 'bg-yellow-400 animate-pulse' : 'bg-green-500'}`}></div>
      <span className="text-gray-600">
        {isLoading ? 'Pipeline running...' : 'Data enriched & ready'}
      </span>
    </div>
  );
}