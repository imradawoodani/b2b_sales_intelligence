export default function PipelineStatus({ status, isLoading, error }) {
  const indicatorClass = isLoading
    ? 'bg-yellow-400 animate-pulse'
    : error
    ? 'bg-red-500'
    : status === 'completed'
    ? 'bg-green-500'
    : 'bg-gray-400';

  const label = error
    ? `Error: ${error}`
    : isLoading
    ? 'Pipeline running...'
    : status === 'never_run'
    ? 'Pipeline not run'
    : `Pipeline: ${status}`;

  return (
    <div className="flex items-center gap-2 text-sm">
      <div className={`w-2 h-2 rounded-full ${indicatorClass}`}></div>
      <span className="text-gray-600">{label}</span>
    </div>
  );
}