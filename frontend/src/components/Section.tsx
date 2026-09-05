export default function Section({ title, blurb }: { title: string; blurb: string }) {
  return (
    <div className="page-card">
      <h2>{title}</h2>
      <p>{blurb}</p>
    </div>
  )
}