export default function ScoreBadge({ score, size = 'md' }) {
  if (score == null) {
    return (
      <span className={`font-mono text-text-muted ${size === 'lg' ? 'text-2xl' : 'text-sm'}`}>
        —
      </span>
    )
  }

  const color =
    score >= 75
      ? 'text-score-high'
      : score >= 50
      ? 'text-score-mid'
      : 'text-score-low'

  const ring =
    score >= 75
      ? 'ring-score-high/30'
      : score >= 50
      ? 'ring-score-mid/30'
      : 'ring-score-low/30'

  if (size === 'lg') {
    return (
      <div className={`inline-flex flex-col items-center justify-center w-16 h-16 rounded-xl ring-2 ${ring} bg-card`}>
        <span className={`font-mono font-medium text-2xl leading-none ${color}`}>{score}</span>
        <span className="text-text-muted text-[10px] mt-0.5">score</span>
      </div>
    )
  }

  return (
    <span className={`font-mono font-medium text-sm ${color}`}>{score}</span>
  )
}
