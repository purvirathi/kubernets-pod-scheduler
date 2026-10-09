import { useState, useEffect, useCallback } from 'react'
import './App.css'

const API = 'http://localhost:5000'

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function pct(v) {
  return `${Math.round(v)}%`
}

function formatTs(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString()
}

/* ------------------------------------------------------------------ */
/*  Main App                                                           */
/* ------------------------------------------------------------------ */

function App() {
  // Navigation
  const [activePage, setActivePage] = useState('Dashboard')
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Data
  const [nodes, setNodes] = useState([])
  const [pods, setPods] = useState([])
  const [stats, setStats] = useState(null)
  const [history, setHistory] = useState([])
  const [algorithms, setAlgorithms] = useState([])
  const [containerProfiles, setContainerProfiles] = useState([])
  const [topology, setTopology] = useState([])

  // Loading / error
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [apiMode, setApiMode] = useState(null)

  // Scheduling form
  const [schedPodName, setSchedPodName] = useState('')
  const [schedCpu, setSchedCpu] = useState('0.5')
  const [schedMem, setSchedMem] = useState('0.5')
  const [selectedAlgorithm, setSelectedAlgorithm] = useState('ai')
  const [selectedProfile, setSelectedProfile] = useState('web-stack')
  const [schedLoading, setSchedLoading] = useState(false)
  const [schedResult, setSchedResult] = useState(null)
  const [schedError, setSchedError] = useState(null)

  // Detail views
  const [selectedNode, setSelectedNode] = useState(null)
  const [selectedPod, setSelectedPod] = useState(null)

  // Modes
  const [demoMode, setDemoMode] = useState(false)
  const [demoStep, setDemoStep] = useState(0)
  const [explainMode, setExplainMode] = useState(false)
  const [presentationMode, setPresentationMode] = useState(false)

  const menuItems = [
    ['▣', 'Dashboard'],
    ['▤', 'Nodes'],
    ['◈', 'Pods'],
    ['✦', 'Scheduler Lab'],
    ['⌁', 'Visualization'],
    ['◷', 'History'],
    ['◎', 'Analytics'],
  ]

  // ----------------------------------------------------------------
  //  Data fetching
  // ----------------------------------------------------------------

  const fetchAll = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [rRoot, rNodes, rPods, rStats, rHist, rAlgorithms, rTopology] = await Promise.all([
        fetch(`${API}/`),
        fetch(`${API}/api/nodes`),
        fetch(`${API}/api/pods`),
        fetch(`${API}/api/cluster-stats`),
        fetch(`${API}/api/history`),
        fetch(`${API}/api/algorithms`),
        fetch(`${API}/api/topology`),
      ])

      const root = await rRoot.json()
      setApiMode(root.mode || 'unknown')

      const nodesData = await rNodes.json()
      if (nodesData.success) setNodes(nodesData.nodes)

      const podsData = await rPods.json()
      if (podsData.success) setPods(podsData.pods)

      const statsData = await rStats.json()
      if (statsData.success) setStats(statsData.stats)

      const histData = await rHist.json()
      if (histData.success) setHistory(histData.history)

      const algorithmData = await rAlgorithms.json()
      if (algorithmData.success) {
        setAlgorithms(algorithmData.algorithms)
        setContainerProfiles(algorithmData.container_profiles)
      }

      const topologyData = await rTopology.json()
      if (topologyData.success) setTopology(topologyData.topology)
    } catch (e) {
      setError(`Cannot reach backend at ${API}. Is the Flask server running?\n${e.message}`)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchAll() }, [fetchAll])

  useEffect(() => {
    const profile = containerProfiles.find((item) => item.id === selectedProfile)
    if (!profile) return
    setSchedCpu(String(profile.cpu_request))
    setSchedMem(String(profile.memory_request_gb))
  }, [containerProfiles, selectedProfile])

  // ----------------------------------------------------------------
  //  Schedule a pod
  // ----------------------------------------------------------------

  async function handleSchedule(e) {
    e.preventDefault()
    setSchedLoading(true)
    setSchedResult(null)
    setSchedError(null)
    try {
      const resp = await fetch(`${API}/api/schedule`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pod_name: schedPodName || `pod-${Date.now()}`,
          cpu_request: parseFloat(schedCpu),
          memory_request_gb: parseFloat(schedMem),
          algorithm: selectedAlgorithm,
          container_profile: selectedProfile,
        }),
      })
      const data = await resp.json()
      if (data.success) {
        setSchedResult(data)
        // Refresh everything to reflect new state
        await fetchAll()
      } else {
        setSchedError(data.error || 'Scheduling failed')
      }
    } catch (e) {
      setSchedError(e.message)
    } finally {
      setSchedLoading(false)
    }
  }

  // ----------------------------------------------------------------
  //  Demo mode steps
  // ----------------------------------------------------------------

  const demoSteps = [
    { page: 'Dashboard', title: 'Welcome!', desc: 'This is the Dashboard — your real-time cluster overview. All numbers come from the live backend.' },
    { page: 'Nodes', title: 'Cluster Nodes', desc: 'Here you see every Kubernetes node, its CPU/memory utilization, and whether it\'s schedulable. Click a node for details.' },
    { page: 'Pods', title: 'Running Pods', desc: 'Every pod running in the cluster. Click one to see its resource requests and which node it\'s on.' },
    { page: 'Scheduler Lab', title: 'Compare Algorithms', desc: 'Choose FCFS, Round Robin, or AI Scheduler, then send a multi-container pod and compare the decision.' },
    { page: 'Visualization', title: 'Visual Assignment', desc: 'See nodes, pods, and containers together so the placement result is easy to explain.' },
    { page: 'History', title: 'Scheduling History', desc: 'Every scheduling decision is recorded with algorithm, selected node, scores, and candidate rankings.' },
    { page: 'Analytics', title: 'Cluster Analytics', desc: 'Visual breakdown of CPU and memory across all nodes. That completes the tour!' },
  ]

  function advanceDemo() {
    if (demoStep < demoSteps.length - 1) {
      const next = demoStep + 1
      setDemoStep(next)
      setActivePage(demoSteps[next].page)
    } else {
      setDemoMode(false)
      setDemoStep(0)
    }
  }

  function startDemo() {
    setDemoMode(true)
    setDemoStep(0)
    setActivePage(demoSteps[0].page)
  }

  // ----------------------------------------------------------------
  //  Render helpers
  // ----------------------------------------------------------------

  function renderExplain(text) {
    if (!explainMode) return null
    return <div className="explain-badge">💡 {text}</div>
  }

  // ----------------------------------------------------------------
  //  RENDER
  // ----------------------------------------------------------------

  if (loading) {
    return (
      <div className="app loading-screen">
        <div className="spinner" />
        <p>Connecting to AI Scheduler backend…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="app loading-screen">
        <div className="error-box">
          <h2>⚠ Connection Error</h2>
          <p>{error}</p>
          <button className="btn-primary" onClick={fetchAll}>Retry</button>
        </div>
      </div>
    )
  }

  return (
    <div className={`app ${presentationMode ? 'presentation' : ''}`}>

      {/* MOBILE HAMBURGER */}
      <button className="hamburger" onClick={() => setSidebarOpen(!sidebarOpen)} aria-label="Toggle menu">
        {sidebarOpen ? '✕' : '☰'}
      </button>

      {/* SIDEBAR */}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>

        <div className="brand">
          <div className="brand-icon">⚡</div>
          <div>
            <h2>AI Scheduler</h2>
            <span>Kubernetes</span>
          </div>
        </div>

        <nav className="nav">
          {menuItems.map(([icon, name]) => (
            <button
              key={name}
              id={`nav-${name.toLowerCase().replace(/\s/g, '-')}`}
              className={`nav-item ${activePage === name ? 'active' : ''}`}
              onClick={() => { setActivePage(name); setSidebarOpen(false) }}
            >
              {icon} {name}
            </button>
          ))}
        </nav>

        <div className="sidebar-actions">
          <button className={`mode-btn ${explainMode ? 'mode-active' : ''}`} onClick={() => setExplainMode(!explainMode)}>
            💡 Explain
          </button>
          <button className={`mode-btn ${presentationMode ? 'mode-active' : ''}`} onClick={() => setPresentationMode(!presentationMode)}>
            📺 Present
          </button>
          <button className="mode-btn" onClick={startDemo}>
            🎯 Demo
          </button>
        </div>

        <div className="cluster-status">
          <p>CLUSTER STATUS</p>
          <div>
            <span className="status-dot" />
            <strong>{apiMode === 'live' ? 'Cluster Online' : 'Simulation Mode'}</strong>
          </div>
          <small>{apiMode === 'live' ? 'Connected to Kubernetes' : 'Using simulated data'}</small>
        </div>

      </aside>


      {/* MAIN CONTENT */}
      <main className="main-content">

        <header className="topbar">
          <div>
            <p className="eyebrow">KUBERNETES CONTROL CENTER</p>
            <h1>{activePage}</h1>
            <p className="subtitle">
              Monitor and manage your intelligent Kubernetes scheduling system.
            </p>
          </div>

          <div className="header-right">
            <button className="refresh-btn" onClick={fetchAll} title="Refresh data">↻</button>
            <span className={`live-badge ${apiMode === 'live' ? '' : 'sim-badge'}`}>
              <span className="live-dot" />
              {apiMode === 'live' ? 'LIVE' : 'SIM'}
            </span>
          </div>
        </header>

        {/* DEMO OVERLAY */}
        {demoMode && (
          <div className="demo-overlay">
            <div className="demo-card">
              <span className="demo-step-num">Step {demoStep + 1} / {demoSteps.length}</span>
              <h3>{demoSteps[demoStep].title}</h3>
              <p>{demoSteps[demoStep].desc}</p>
              <div className="demo-actions">
                <button className="btn-secondary" onClick={() => { setDemoMode(false); setDemoStep(0) }}>Exit Demo</button>
                <button className="btn-primary" onClick={advanceDemo}>
                  {demoStep < demoSteps.length - 1 ? 'Next →' : 'Finish ✓'}
                </button>
              </div>
            </div>
          </div>
        )}


        {/* =========== DASHBOARD =========== */}
        {activePage === 'Dashboard' && stats && (
          <>
            {renderExplain('These stats are fetched from /api/cluster-stats and reflect real-time cluster state.')}

            <section className="stats-grid">
              <div className="stat-card" id="stat-nodes">
                <div className="stat-top">
                  <span>Cluster Nodes</span>
                  <span className="stat-icon">⌘</span>
                </div>
                <h2>{stats.total_nodes}</h2>
                <p><span className="positive">{stats.schedulable_nodes} schedulable</span></p>
              </div>

              <div className="stat-card" id="stat-pods">
                <div className="stat-top">
                  <span>Running Pods</span>
                  <span className="stat-icon">◇</span>
                </div>
                <h2>{stats.running_pods}</h2>
                <p><span className="positive">{stats.total_pods} pods · {stats.total_containers || 0} containers</span></p>
              </div>

              <div className="stat-card" id="stat-cpu">
                <div className="stat-top">
                  <span>Avg CPU Usage</span>
                  <span className="stat-icon">◉</span>
                </div>
                <h2>{pct(stats.avg_cpu_pct)}</h2>
                <div className="progress">
                  <div className="progress-fill cpu" style={{ width: pct(stats.avg_cpu_pct) }} />
                </div>
              </div>

              <div className="stat-card" id="stat-mem">
                <div className="stat-top">
                  <span>Avg Memory Usage</span>
                  <span className="stat-icon">▥</span>
                </div>
                <h2>{pct(stats.avg_mem_pct)}</h2>
                <div className="progress">
                  <div className="progress-fill memory" style={{ width: pct(stats.avg_mem_pct) }} />
                </div>
              </div>
            </section>


            <section className="content-grid">
              {/* LATEST AI RECOMMENDATION */}
              <div className="panel ai-panel">
                <div className="panel-header">
                  <div>
                    <p className="panel-label">INTELLIGENT SCHEDULING</p>
                    <h2>Latest Scheduler Decision</h2>
                  </div>
                  <span className="ai-badge">{history[0]?.algorithm?.short_name || 'READY'}</span>
                </div>

                {history.length > 0 ? (
                  <>
                    <div className="recommendation">
                      <div className="pod-box">
                        <span>Pod</span>
                        <strong>{history[0].pod_name}</strong>
                      </div>
                      <div className="arrow">→</div>
                      <div className={`node-box ${history[0].status === 'FAILED' ? 'node-box-fail' : ''}`}>
                        <span>Selected Node</span>
                        <strong>{history[0].recommended_node || 'None (failed)'}</strong>
                      </div>
                    </div>

                    {history[0].candidates && history[0].candidates.length > 0 && (
                      <div className="score">
                        <div className="score-info">
                          <span>Top Score</span>
                          <strong>{pct((history[0].candidates[0]?.recommendation_probability || 0) * 100)}</strong>
                        </div>
                        <div className="score-bar">
                          <div className="score-bar-fill" style={{ width: pct((history[0].candidates[0]?.recommendation_probability || 0) * 100) }} />
                        </div>
                      </div>
                    )}

                    <p className="reason">
                      {history[0].status === 'SCHEDULED'
                        ? `✓ ${history[0].message} — placed on ${history[0].recommended_node} with highest feasibility score.`
                        : `✗ ${history[0].message}`
                      }
                    </p>
                  </>
                ) : (
                  <p className="reason">No scheduling decisions yet. Go to Scheduler Lab to schedule a pod.</p>
                )}
              </div>


              {/* NODE HEALTH */}
              <div className="panel">
                <div className="panel-header">
                  <div>
                    <p className="panel-label">CLUSTER</p>
                    <h2>Node Health</h2>
                  </div>
                  <span className="healthy">{nodes.filter(n => n.schedulable).length} Online</span>
                </div>

                <div className="node-list">
                  {nodes.slice(0, 4).map((node) => (
                    <div className="node-row clickable" key={node.node_id}
                      onClick={() => { setSelectedNode(node); setActivePage('Nodes') }}>
                      <div className="node-row-left">
                        <span className={`node-status ${node.schedulable ? 'node-online' : 'node-offline'}`} />
                        <div>
                          <strong>{node.node_id}</strong>
                          <small>CPU {pct(node.cpu_utilization_pct)} · RAM {pct(node.memory_utilization_pct)}</small>
                        </div>
                      </div>
                      <span className={node.schedulable ? 'status-online' : 'status-offline'}>
                        {node.schedulable ? 'Online' : 'Cordoned'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </section>


            {/* RECENT SCHEDULING TABLE */}
            <section className="panel table-panel">
              <div className="panel-header">
                <div>
                  <p className="panel-label">RECENT ACTIVITY</p>
                  <h2>Scheduling Decisions</h2>
                </div>
                <button className="view-btn" onClick={() => setActivePage('History')}>View all →</button>
              </div>

              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Pod</th>
                      <th>Selected Node</th>
                      <th>Algorithm</th>
                      <th>Score</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.length === 0 && (
                      <tr><td colSpan={5} className="empty-row">No scheduling decisions yet</td></tr>
                    )}
                    {history.slice(0, 5).map((h) => (
                      <tr key={h.id}>
                        <td><strong>{h.pod_name}</strong></td>
                        <td>{h.recommended_node || '—'}</td>
                        <td>{h.algorithm?.short_name || 'AI'}</td>
                        <td>
                          <span className="confidence">
                            {h.candidates && h.candidates[0]
                              ? pct(h.candidates[0].recommendation_probability * 100)
                              : '—'}
                          </span>
                        </td>
                        <td>
                          <span className={h.status === 'SCHEDULED' ? 'success' : 'failed'}>
                            {h.status === 'SCHEDULED' ? '✓ Scheduled' : '✗ Failed'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}


        {/* =========== NODES PAGE =========== */}
        {activePage === 'Nodes' && (
          <>
            {renderExplain('Node data comes from /api/nodes. In live mode, this reads from the Kubernetes API + metrics server.')}

            {/* Node Detail Modal */}
            {selectedNode && (
              <div className="detail-backdrop" onClick={() => setSelectedNode(null)}>
                <div className="detail-modal" onClick={e => e.stopPropagation()}>
                  <button className="detail-close" onClick={() => setSelectedNode(null)}>✕</button>
                  <h2>{selectedNode.node_id}</h2>
                  <span className={`detail-status ${selectedNode.schedulable ? 'success' : 'failed'}`}>
                    {selectedNode.schedulable ? '● Schedulable' : '● Cordoned'}
                  </span>

                  <div className="detail-grid">
                    <div className="detail-item">
                      <label>CPU Capacity</label>
                      <strong>{selectedNode.cpu_capacity_cores} cores</strong>
                    </div>
                    <div className="detail-item">
                      <label>Memory Capacity</label>
                      <strong>{selectedNode.memory_capacity_gb.toFixed(1)} GB</strong>
                    </div>
                    <div className="detail-item">
                      <label>CPU Utilization</label>
                      <strong>{pct(selectedNode.cpu_utilization_pct)}</strong>
                      <div className="progress"><div className="progress-fill cpu" style={{ width: pct(selectedNode.cpu_utilization_pct) }} /></div>
                    </div>
                    <div className="detail-item">
                      <label>Memory Utilization</label>
                      <strong>{pct(selectedNode.memory_utilization_pct)}</strong>
                      <div className="progress"><div className="progress-fill memory" style={{ width: pct(selectedNode.memory_utilization_pct) }} /></div>
                    </div>
                    <div className="detail-item">
                      <label>Running Pods</label>
                      <strong>{selectedNode.running_pods}</strong>
                    </div>
                    <div className="detail-item">
                      <label>Available CPU</label>
                      <strong>{(selectedNode.cpu_capacity_cores * (1 - selectedNode.cpu_utilization_pct / 100)).toFixed(2)} cores</strong>
                    </div>
                    <div className="detail-item">
                      <label>Available Memory</label>
                      <strong>{(selectedNode.memory_capacity_gb * (1 - selectedNode.memory_utilization_pct / 100)).toFixed(2)} GB</strong>
                    </div>
                  </div>

                  <h3 style={{ marginTop: 16 }}>Pods on this Node</h3>
                  <div className="detail-pods-list">
                    {pods.filter(p => p.node === selectedNode.node_id).length === 0
                      ? <p className="muted">No pods on this node</p>
                      : pods.filter(p => p.node === selectedNode.node_id).map(p => (
                          <div className="detail-pod-row" key={p.name}>
                            <strong>{p.name}</strong>
                            <small>{p.namespace} · {p.status}</small>
                          </div>
                        ))
                    }
                  </div>
                </div>
              </div>
            )}

            <section className="panel table-panel">
              <div className="panel-header">
                <div>
                  <p className="panel-label">KUBERNETES CLUSTER</p>
                  <h2>Cluster Nodes</h2>
                </div>
                <span className="healthy">{nodes.filter(n => n.schedulable).length} Schedulable</span>
              </div>

              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Node</th>
                      <th>CPU Capacity</th>
                      <th>CPU Usage</th>
                      <th>Memory Capacity</th>
                      <th>Memory Usage</th>
                      <th>Pods</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {nodes.map((node) => (
                      <tr key={node.node_id} className="clickable-row"
                        onClick={() => setSelectedNode(node)}>
                        <td><strong>{node.node_id}</strong></td>
                        <td>{node.cpu_capacity_cores} cores</td>
                        <td>
                          <span className={node.cpu_utilization_pct > 80 ? 'warn' : 'confidence'}>
                            {pct(node.cpu_utilization_pct)}
                          </span>
                        </td>
                        <td>{node.memory_capacity_gb.toFixed(1)} GB</td>
                        <td>
                          <span className={node.memory_utilization_pct > 80 ? 'warn' : 'confidence'}>
                            {pct(node.memory_utilization_pct)}
                          </span>
                        </td>
                        <td>{node.running_pods}</td>
                        <td>
                          <span className={node.schedulable ? 'success' : 'failed'}>
                            {node.schedulable ? '● Online' : '● Cordoned'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}


        {/* =========== PODS PAGE =========== */}
        {activePage === 'Pods' && (
          <>
            {renderExplain('Pod data comes from /api/pods. In live mode, this lists real pods from all namespaces.')}

            {/* Pod Detail Modal */}
            {selectedPod && (
              <div className="detail-backdrop" onClick={() => setSelectedPod(null)}>
                <div className="detail-modal" onClick={e => e.stopPropagation()}>
                  <button className="detail-close" onClick={() => setSelectedPod(null)}>✕</button>
                  <h2>{selectedPod.name}</h2>
                  <span className={`detail-status ${selectedPod.status === 'Running' ? 'success' : 'failed'}`}>
                    ● {selectedPod.status}
                  </span>
                  <div className="detail-grid">
                    <div className="detail-item">
                      <label>Namespace</label>
                      <strong>{selectedPod.namespace}</strong>
                    </div>
                    <div className="detail-item">
                      <label>Node</label>
                      <strong>{selectedPod.node}</strong>
                    </div>
                    <div className="detail-item">
                      <label>CPU Request</label>
                      <strong>{selectedPod.cpu_request} cores</strong>
                    </div>
                    <div className="detail-item">
                      <label>Memory Request</label>
                      <strong>{selectedPod.memory_request_gb} GB</strong>
                    </div>
                  </div>
                  <h3>Containers</h3>
                  <div className="container-strip">
                    {(selectedPod.containers || []).map(container => (
                      <div className="container-chip" key={container.name}>
                        <strong>{container.name}</strong>
                        <span>{container.role || 'container'}</span>
                        <small>{container.image}</small>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            <section className="panel table-panel">
              <div className="panel-header">
                <div>
                  <p className="panel-label">WORKLOADS</p>
                  <h2>Running Pods</h2>
                </div>
                <span className="healthy">{pods.filter(p => p.status === 'Running').length} Running</span>
              </div>

              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Pod</th>
                      <th>Namespace</th>
                      <th>Node</th>
                      <th>Containers</th>
                      <th>CPU Request</th>
                      <th>Memory</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pods.map((pod) => (
                      <tr key={pod.name} className="clickable-row"
                        onClick={() => setSelectedPod(pod)}>
                        <td><strong>{pod.name}</strong></td>
                        <td>{pod.namespace}</td>
                        <td>{pod.node}</td>
                        <td>{(pod.containers || []).length}</td>
                        <td>{pod.cpu_request} cores</td>
                        <td>{pod.memory_request_gb} GB</td>
                        <td>
                          <span className={pod.status === 'Running' ? 'success' : 'failed'}>
                            ● {pod.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}


        {/* =========== SCHEDULER LAB PAGE =========== */}
        {activePage === 'Scheduler Lab' && (
          <>
            {renderExplain('This page sends POST /api/schedule with the selected algorithm. FCFS, Round Robin, and AI use the same node state so the comparison is fair.')}

            <section className="panel ai-panel">
              <div className="panel-header">
                <div>
                  <p className="panel-label">SCHEDULING ALGORITHMS</p>
                  <h2>Scheduler Lab</h2>
                </div>
                <span className="ai-badge">{algorithms.find(a => a.id === selectedAlgorithm)?.short_name || 'AI'} ACTIVE</span>
              </div>

              <div className="algorithm-grid">
                {algorithms.map((algorithm) => (
                  <button
                    type="button"
                    key={algorithm.id}
                    className={`algorithm-card ${selectedAlgorithm === algorithm.id ? 'selected' : ''}`}
                    onClick={() => setSelectedAlgorithm(algorithm.id)}
                  >
                    <strong>{algorithm.short_name}</strong>
                    <span>{algorithm.name}</span>
                    <small>{algorithm.description}</small>
                  </button>
                ))}
              </div>

              {/* SCHEDULE FORM */}
              <form className="sched-form" onSubmit={handleSchedule}>
                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="pod-name">Pod Name (optional)</label>
                    <input id="pod-name" type="text" placeholder="e.g. my-web-app"
                      value={schedPodName} onChange={e => setSchedPodName(e.target.value)} />
                  </div>
                  <div className="form-group">
                    <label htmlFor="profile">Container Profile</label>
                    <select id="profile" value={selectedProfile} onChange={e => setSelectedProfile(e.target.value)}>
                      {containerProfiles.map(profile => (
                        <option key={profile.id} value={profile.id}>{profile.name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label htmlFor="cpu-req">CPU Request (cores)</label>
                    <input id="cpu-req" type="number" step="0.1" min="0.1" max="16"
                      value={schedCpu} onChange={e => setSchedCpu(e.target.value)} required />
                  </div>
                  <div className="form-group">
                    <label htmlFor="mem-req">Memory Request (GB)</label>
                    <input id="mem-req" type="number" step="0.1" min="0.1" max="64"
                      value={schedMem} onChange={e => setSchedMem(e.target.value)} required />
                  </div>
                </div>
                <button className="btn-primary" type="submit" disabled={schedLoading}>
                  {schedLoading ? 'Scheduling…' : '✦ Schedule Pod'}
                </button>
              </form>

              {containerProfiles.find(p => p.id === selectedProfile) && (
                <div className="container-strip">
                  {containerProfiles.find(p => p.id === selectedProfile).containers.map(container => (
                    <div className="container-chip" key={container.name}>
                      <strong>{container.name}</strong>
                      <span>{container.role}</span>
                      <small>{container.cpu_request} CPU · {container.memory_request_gb} GB</small>
                    </div>
                  ))}
                </div>
              )}

              {schedError && (
                <div className="sched-error">
                  ⚠ {schedError}
                </div>
              )}

              {/* SCHEDULING RESULT */}
              {schedResult && (
                <div className="sched-result">
                  <div className="recommendation">
                    <div className="pod-box">
                      <span>Pod</span>
                      <strong>{schedResult.pod_name}</strong>
                      <small>CPU: {schedResult.pod.cpu_request} · Mem: {schedResult.pod.memory_request_gb} GB</small>
                    </div>
                    <div className="arrow">→</div>
                    <div className={`node-box ${schedResult.status === 'FAILED' ? 'node-box-fail' : ''}`}>
                      <span>{schedResult.status === 'SCHEDULED' ? `${schedResult.algorithm.short_name} Selected Node` : 'No Suitable Node'}</span>
                      <strong>{schedResult.recommended_node || 'None'}</strong>
                    </div>
                  </div>

                  {/* Explanation */}
                  <p className="reason">
                    {schedResult.status === 'SCHEDULED'
                      ? `✓ ${schedResult.algorithm.name}: ${schedResult.message} It evaluated ${schedResult.candidates.length} candidate nodes and placed "${schedResult.pod_name}" on ${schedResult.recommended_node}.`
                      : `✗ Scheduling failed: ${schedResult.message}. All ${schedResult.candidates.length} nodes were evaluated and none had sufficient resources to satisfy the request.`
                    }
                  </p>

                  {/* CANDIDATE COMPARISON TABLE */}
                  <h3 style={{ color: '#fff', margin: '18px 0 10px' }}>Candidate Node Comparison</h3>
                  <div className="table-wrapper">
                    <table>
                      <thead>
                        <tr>
                          <th>Node</th>
                          <th>Feasible</th>
                          <th>Score</th>
                          <th>Reason</th>
                          <th>Rank</th>
                        </tr>
                      </thead>
                      <tbody>
                        {schedResult.candidates.map((c, i) => (
                          <tr key={c.node_id} className={c.node_id === schedResult.recommended_node ? 'highlight-row' : ''}>
                            <td><strong>{c.node_id}</strong></td>
                            <td>
                              <span className={c.feasible ? 'success' : 'failed'}>
                                {c.feasible ? '✓ Yes' : '✗ No'}
                              </span>
                            </td>
                            <td>
                              <span className="confidence">
                                {(c.recommendation_probability * 100).toFixed(1)}%
                              </span>
                            </td>
                            <td>{c.reason || 'Evaluated'}</td>
                            <td>#{i + 1}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </section>
          </>
        )}


        {/* =========== VISUALIZATION PAGE =========== */}
        {activePage === 'Visualization' && (
          <>
            {renderExplain('This topology view groups pods by assigned node and shows the containers inside each pod. Schedule from Scheduler Lab, then return here to watch the placement change.')}

            <section className="topology-grid">
              {topology.map((item) => (
                <div className="node-column" key={item.node.node_id}>
                  <div className="node-column-header">
                    <div>
                      <p className="panel-label">NODE</p>
                      <h2>{item.node.node_id}</h2>
                    </div>
                    <span className={item.node.schedulable ? 'success' : 'failed'}>
                      {item.node.schedulable ? 'Online' : 'Cordoned'}
                    </span>
                  </div>

                  <div className="node-meter">
                    <span>CPU {pct(item.node.cpu_utilization_pct)}</span>
                    <div className="progress"><div className="progress-fill cpu" style={{ width: pct(item.node.cpu_utilization_pct) }} /></div>
                    <span>Memory {pct(item.node.memory_utilization_pct)}</span>
                    <div className="progress"><div className="progress-fill memory" style={{ width: pct(item.node.memory_utilization_pct) }} /></div>
                  </div>

                  <div className="node-summary">
                    <strong>{item.pod_count}</strong> pods
                    <strong>{item.container_count}</strong> containers
                  </div>

                  <div className="pod-stack">
                    {item.pods.length === 0 && <p className="muted">No pods assigned</p>}
                    {item.pods.map((pod) => (
                      <div className="visual-pod" key={pod.name}>
                        <div className="visual-pod-head">
                          <strong>{pod.name}</strong>
                          <span>{pod.cpu_request} CPU · {pod.memory_request_gb} GB</span>
                        </div>
                        <div className="visual-containers">
                          {(pod.containers || []).map(container => (
                            <span key={container.name} title={container.image}>{container.name}</span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </section>

            <section className="panel table-panel">
              <div className="panel-header">
                <div>
                  <p className="panel-label">EXPLANATION</p>
                  <h2>How to Present This</h2>
                </div>
              </div>
              <div className="explanation-grid">
                <div>
                  <strong>FCFS</strong>
                  <p>Shows the simplest behavior: the pod goes to the first node that has enough free CPU and memory.</p>
                </div>
                <div>
                  <strong>Round Robin</strong>
                  <p>Shows fairness: each new pod starts from the next node in the rotation, then checks capacity.</p>
                </div>
                <div>
                  <strong>AI Scheduler</strong>
                  <p>Shows intelligent ranking: feasible nodes are scored by the trained model before placement.</p>
                </div>
              </div>
            </section>
          </>
        )}


        {/* =========== HISTORY PAGE =========== */}
        {activePage === 'History' && (
          <>
            {renderExplain('Scheduling history is stored in-memory on the backend and fetched from /api/history.')}

            <section className="panel table-panel">
              <div className="panel-header">
                <div>
                  <p className="panel-label">SCHEDULER LOGS</p>
                  <h2>Scheduling History</h2>
                </div>
                <span className="healthy">{history.length} entries</span>
              </div>

              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Pod</th>
                      <th>CPU</th>
                      <th>Memory</th>
                      <th>Algorithm</th>
                      <th>Selected Node</th>
                      <th>Top Score</th>
                      <th>Status</th>
                      <th>Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.length === 0 && (
                      <tr><td colSpan={9} className="empty-row">No scheduling decisions yet. Go to Scheduler Lab to schedule a pod.</td></tr>
                    )}
                    {history.map((h) => (
                      <tr key={h.id}>
                        <td>{h.id}</td>
                        <td><strong>{h.pod_name}</strong></td>
                        <td>{h.cpu_request} cores</td>
                        <td>{h.memory_request_gb} GB</td>
                        <td>{h.algorithm?.short_name || 'AI'}</td>
                        <td>{h.recommended_node || '—'}</td>
                        <td>
                          <span className="confidence">
                            {h.candidates && h.candidates[0]
                              ? pct(h.candidates[0].recommendation_probability * 100)
                              : '—'}
                          </span>
                        </td>
                        <td>
                          <span className={h.status === 'SCHEDULED' ? 'success' : 'failed'}>
                            {h.status === 'SCHEDULED' ? '✓ Success' : '✗ Failed'}
                          </span>
                        </td>
                        <td className="ts-cell">{formatTs(h.timestamp)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}


        {/* =========== ANALYTICS PAGE =========== */}
        {activePage === 'Analytics' && stats && (
          <>
            {renderExplain('Analytics are computed from live node data returned by /api/nodes and /api/cluster-stats.')}

            <section className="analytics-grid">
              {/* Cluster Summary */}
              <div className="panel">
                <div className="panel-header">
                  <div>
                    <p className="panel-label">OVERVIEW</p>
                    <h2>Cluster Summary</h2>
                  </div>
                </div>
                <div className="analytics-summary">
                  <div className="analytics-metric">
                    <span>Total CPU</span>
                    <strong>{stats.total_cpu_cores} cores</strong>
                  </div>
                  <div className="analytics-metric">
                    <span>Total Memory</span>
                    <strong>{stats.total_memory_gb} GB</strong>
                  </div>
                  <div className="analytics-metric">
                    <span>Nodes</span>
                    <strong>{stats.total_nodes}</strong>
                  </div>
                  <div className="analytics-metric">
                    <span>Pods</span>
                    <strong>{stats.total_pods}</strong>
                  </div>
                  <div className="analytics-metric">
                    <span>Containers</span>
                    <strong>{stats.total_containers || 0}</strong>
                  </div>
                  <div className="analytics-metric">
                    <span>Scheduling Events</span>
                    <strong>{history.length}</strong>
                  </div>
                  <div className="analytics-metric">
                    <span>Backend Mode</span>
                    <strong className="mode-label">{apiMode === 'live' ? '🟢 Live' : '🟡 Simulation'}</strong>
                  </div>
                </div>
              </div>

              <div className="panel">
                <div className="panel-header">
                  <div>
                    <p className="panel-label">ALGORITHMS</p>
                    <h2>Scheduling Mix</h2>
                  </div>
                </div>
                <div className="algorithm-bars">
                  {algorithms.map(algorithm => {
                    const count = stats.algorithm_counts?.[algorithm.short_name] || 0
                    const width = history.length ? Math.max(8, (count / history.length) * 100) : 0
                    return (
                      <div className="chart-row" key={algorithm.id}>
                        <span className="chart-label">{algorithm.short_name}</span>
                        <div className="chart-track">
                          <div className="chart-fill chart-cpu" style={{ width: `${width}%` }} />
                        </div>
                        <span className="chart-val">{count}</span>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Per-node breakdown */}
              <div className="panel">
                <div className="panel-header">
                  <div>
                    <p className="panel-label">PER-NODE</p>
                    <h2>Resource Utilization</h2>
                  </div>
                </div>
                <div className="chart-bars">
                  {nodes.map(node => (
                    <div className="chart-node" key={node.node_id}>
                      <strong>{node.node_id}</strong>
                      <div className="chart-row">
                        <span className="chart-label">CPU</span>
                        <div className="chart-track">
                          <div className="chart-fill chart-cpu" style={{ width: pct(node.cpu_utilization_pct) }} />
                        </div>
                        <span className="chart-val">{pct(node.cpu_utilization_pct)}</span>
                      </div>
                      <div className="chart-row">
                        <span className="chart-label">MEM</span>
                        <div className="chart-track">
                          <div className="chart-fill chart-mem" style={{ width: pct(node.memory_utilization_pct) }} />
                        </div>
                        <span className="chart-val">{pct(node.memory_utilization_pct)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          </>
        )}


        <footer>
          AI Kubernetes Pod Scheduler · {apiMode === 'live' ? 'Live Cluster' : 'Simulation Mode'}
        </footer>

      </main>

    </div>
  )
}

export default App
