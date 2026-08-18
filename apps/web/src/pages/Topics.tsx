import { refSrc } from "../api"
import { PlusIcon, WarnIcon } from "../components/Icons"
import { TopicPill } from "../components/Pills"
import { daysAgoISO, formatCount } from "../lib"
import { useStore } from "../store"

export function TopicsPage() {
  const { topics, jobs, loading, busy, toggleTopic, addTopic, syncAllInsights } = useStore()
  const cutoff = daysAgoISO(7)

  function plays7d(slug: string) {
    return jobs
      .filter(
        (job) =>
          job.type === "REEL" &&
          job.status === "PUBLISHED" &&
          job.topic === slug &&
          job.date >= cutoff,
      )
      .reduce((sum, job) => sum + (job.insights?.views ?? job.insights?.reach ?? 0), 0)
  }

  return (
    <div className="page">
      <div className="page-head">
        <h1 className="page-title">Topics</h1>
        <div className="filters">
          <button
            type="button"
            className="btn"
            disabled={busy}
            onClick={() => void syncAllInsights()}
          >
            Refresh insights
          </button>
          <button
            type="button"
            className="btn"
            onClick={() => {
              const name = window.prompt("Topic name")
              if (name) addTopic(name)
            }}
          >
            Add topic
          </button>
        </div>
      </div>
      {!loading && topics.length === 0 ? <p className="page-sub">No topics yet.</p> : null}
      <table className="table">
        <thead>
          <tr>
            <th>Topic</th>
            <th>Last used</th>
            <th>Weight</th>
            <th>7d views</th>
            <th>Audio</th>
            <th>Style refs</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {topics.map((topic) => (
            <tr key={topic.slug}>
              <td>
                <div className="topic-name">
                  <TopicPill topic={topic.slug} />
                </div>
              </td>
              <td>{topic.last_used ?? "Never"}</td>
              <td>
                <div className="weight">
                  <div className="bar">
                    <span style={{ width: `${topic.weight}%`, background: "var(--gold)" }} />
                  </div>
                  {topic.weight}%
                </div>
              </td>
              <td>{formatCount(plays7d(topic.slug))}</td>
              <td>{topic.audio_ids.length} tracks</td>
              <td>
                <div className="refs">
                  {topic.refs.map((src) => (
                    <img key={src} src={refSrc(src)} alt="" />
                  ))}
                </div>
              </td>
              <td>
                <button
                  type="button"
                  className={`toggle ${topic.enabled ? "on" : ""}`}
                  aria-pressed={topic.enabled}
                  onClick={() => toggleTopic(topic.slug)}
                >
                  <i />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {topics
        .filter((topic) => topic.slug === "viral" && topic.audio_ids.length < 5)
        .map((topic) => (
          <div className="warn-bar" key={topic.slug}>
            <WarnIcon />
            Only {topic.audio_ids.length} tracks available. Need 5 tracks before Viral can be
            used for Reels.
          </div>
        ))}
      <button
        type="button"
        className="dashed"
        onClick={() => {
          const name = window.prompt("Topic name")
          if (name) addTopic(name)
        }}
      >
        <PlusIcon />
        Add a new topic pillar
      </button>
    </div>
  )
}
