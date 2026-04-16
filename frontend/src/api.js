const BASE = '/api'

export async function fetchContractors(assumeNonAuthorized = false) {
  const query = new URLSearchParams({ limit: 50 })
  if (assumeNonAuthorized) query.set('assume_non_authorized', 'true')
  const res = await fetch(`${BASE}/contractors?${query.toString()}`)
  if (!res.ok) throw new Error('Failed to fetch contractors')
  return res.json()
}

export async function fetchContractor(id) {
  const res = await fetch(`${BASE}/contractors/${id}`)
  if (!res.ok) throw new Error('Failed to fetch contractor')
  return res.json()
}

export async function askQuestion(contractorId, question) {
  const res = await fetch(`${BASE}/contractors/${contractorId}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  if (!res.ok) throw new Error('Failed to get answer')
  return res.json()
}

export async function triggerPipeline() {
  const res = await fetch(`${BASE}/pipeline/run`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to trigger pipeline')
  return res.json()
}

export async function fetchPipelineStatus() {
  const res = await fetch(`${BASE}/pipeline/status`)
  if (!res.ok) throw new Error('Failed to fetch pipeline status')
  return res.json()
}
