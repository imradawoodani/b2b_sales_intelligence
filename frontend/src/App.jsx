import { useState, useEffect } from 'react';
import { fetchContractors, fetchPipelineStatus, triggerPipeline, askQuestion } from './api';
import ContractorList from './components/ContractorList';
import ContractorTable from './components/ContractorTable';
import SidePanel from './components/SidePanel';
import PipelineStatus from './components/PipelineStatus';

export default function App() {
  const [viewMode, setViewMode] = useState('list'); // 'list' or 'table'
  const [contractors, setContractors] = useState([]);
  const [selectedContractor, setSelectedContractor] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [pipelineStatus, setPipelineStatus] = useState('never_run');
  const [pipelineError, setPipelineError] = useState(null);
  const [assumeNonAuthorized, setAssumeNonAuthorized] = useState(true);

  const mapContracts = (items) =>
    items.map((item) => ({
      id: item.id,
      name: item.name,
      distance: item.distance_miles != null ? `${item.distance_miles.toFixed(1)} miles` : 'TBD',
      estRevenue: item.estimated_annual_revenue != null ? `USD ${item.estimated_annual_revenue.toLocaleString()}` : 'TBD',
      tier: item.gaf_tier ? item.gaf_tier.replace('_', ' ') : 'None',
      reviews: item.review_count ?? 0,
      rating: item.avg_rating ?? 0,
      brief: item.brief ?? 'Sales brief not available yet.',
      contact: [item.website, item.phone].filter(Boolean).join(' | '),
      perplexityScore: item.perplexity_score ?? 0,
      perplexityInsights: item.perplexity_insights ?? [],
      score: item.display_score ?? item.priority_score ?? 0,
    }));

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [contractorData, statusData] = await Promise.all([
        fetchContractors(assumeNonAuthorized),
        fetchPipelineStatus(),
      ]);
      setContractors(mapContracts(contractorData.contractors));
      setPipelineStatus(statusData.status || 'never_run');
      setPipelineError(statusData.error || null);
    } catch (error) {
      console.error('Failed to load backend data:', error);
      setPipelineError('Unable to load backend data');
    }
    setIsLoading(false);
  };

  useEffect(() => {
    loadData();
  }, [assumeNonAuthorized]);

  const handleTriggerPipeline = async () => {
    setIsLoading(true);
    try {
      await triggerPipeline();
      await loadData();
    } catch (error) {
      console.error('Pipeline trigger failed:', error);
      setPipelineError('Failed to trigger pipeline');
      setIsLoading(false);
    }
  };

  const handleAsk = async (contractorId, question) => {
    return askQuestion(contractorId, question)
  }

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-sans flex">
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 px-6 py-4 flex flex-col gap-4">
          <div className="flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold text-gray-800">Instalily Sales Intelligence</h1>
            <p className="text-sm text-gray-500">Territory: ZIP 10013</p>
          </div>
          <div className="flex flex-col gap-2 items-end">
            <div className="text-right text-sm text-amber-700 bg-amber-100 px-3 py-2 rounded-lg border border-amber-200">
              ⚠️ Scoring assumes the distributor is NOT a GAF-authorized partner.
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={assumeNonAuthorized}
                onChange={(e) => setAssumeNonAuthorized(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-slate-900 focus:ring-slate-900"
              />
              Use non-authorized distributor scoring
            </label>
          </div>
          <div className="flex items-center gap-4">
            <PipelineStatus status={pipelineStatus} isLoading={isLoading} error={pipelineError} />
            <button
              onClick={handleTriggerPipeline}
              className="bg-slate-900 text-white px-3 py-1 rounded-md text-sm hover:bg-slate-800"
            >
              Refresh Pipeline
            </button>
            <div className="bg-gray-100 p-1 rounded-lg flex gap-1">
              <button 
                onClick={() => setViewMode('list')}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${viewMode === 'list' ? 'bg-white shadow-sm font-medium' : 'text-gray-500 hover:text-gray-700'}`}
              >
                List
              </button>
              <button 
                onClick={() => setViewMode('table')}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${viewMode === 'table' ? 'bg-white shadow-sm font-medium' : 'text-gray-500 hover:text-gray-700'}`}
              >
                Table
              </button>
            </div>
          </div>
        </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-1 overflow-auto p-6">
          {viewMode === 'list' ? (
            <ContractorList contractors={contractors} onSelect={setSelectedContractor} />
          ) : (
            <ContractorTable contractors={contractors} onSelect={setSelectedContractor} />
          )}
        </main>
      </div>

      {/* Side Panel Overlay */}
      <SidePanel 
        contractor={selectedContractor} 
        onClose={() => setSelectedContractor(null)} 
        onAsk={handleAsk}
      />
    </div>
  );
}