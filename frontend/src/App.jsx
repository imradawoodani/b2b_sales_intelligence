import { useState, useEffect } from 'react';
import ContractorList from './components/ContractorList';
import ContractorTable from './components/ContractorTable';
import SidePanel from './components/SidePanel';
import PipelineStatus from './components/PipelineStatus';

export default function App() {
  const [viewMode, setViewMode] = useState('list'); // 'list' or 'table'
  const [contractors, setContractors] = useState([]);
  const [selectedContractor, setSelectedContractor] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Mock fetch - in a real app, this calls your FastAPI backend
  useEffect(() => {
    setTimeout(() => {
      setContractors([
        {
          id: 1,
          name: "ABC Roofing",
          score: 92,
          distance: "2.1 miles",
          estRevenue: "USD 48k",
          tier: "Master Elite",
          reviews: 145,
          rating: 4.8,
          brief: "High volume buyer. Recent web signals indicate they are expanding their commercial division. Ideal target for bulk underlayment supplies.",
          contact: "john@abcroofing.com | 555-0192"
        },
        {
          id: 2,
          name: "SkyTop Contractors",
          score: 87,
          distance: "5.0 miles",
          estRevenue: "USD 31k",
          tier: "Certified",
          reviews: 88,
          rating: 4.5,
          brief: "Solid mid-sized operation. They are not locked into GAF warranties, making them a highly flexible buyer for our non-authorized distributor status.",
          contact: "info@skytop.com | 555-8821"
        }
      ]);
      setIsLoading(false);
    }, 1000);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-sans flex">
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold text-gray-800">Instalily Sales Intelligence</h1>
            <p className="text-sm text-gray-500">Territory: ZIP 10013</p>
          </div>
          <div className="flex items-center gap-4">
            <PipelineStatus isLoading={isLoading} />
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
      />
    </div>
  );
}