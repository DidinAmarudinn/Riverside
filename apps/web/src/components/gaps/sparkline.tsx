export function Sparkline({
  data,
  className = "text-primary-container",
}: {
  data: number[];
  className?: string;
}) {
  if (data.length < 2) return null;
  const width = 64;
  const height = 20;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - ((v - min) / range) * (height - 2) - 1;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className={`h-5 w-16 stroke-current fill-none ${className}`}
      style={{ strokeWidth: 2 }}
      aria-hidden
    >
      <polyline points={points} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
